from rest_framework import serializers 
from django.contrib.auth import get_user_model
from .models import (
    Cart, CartItem, CustomerAddress, Order, OrderItem, 
    Product, Category, ProductRating, Review, Wishlist, 
    Notification, ContactMessage, HelpCenterArticle, ProductImage, ProductVariant
)
from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.db.models import Avg, Count
from django.core.exceptions import ValidationError
from django.db.models import Sum

User = get_user_model()



class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddress
        fields = ['id', 'street', 'city', 'state', 'phone']
        read_only_fields = ['customer']

    def create(self, validated_data):
        # Get the user from the request context
        user = self.context['request'].user
        return CustomerAddress.objects.create(customer=user, **validated_data)

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
 
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "profile_picture_url", "password"]  # Remove username, first_name, last_name
        ref_name = 'apiApp_User'
        

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise ValidationError("This email is already in use.")
        return value
 
    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(validated_data.pop('password'))  # Securely set password
        user.save()
        return user    

class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)  # For writing
    product = serializers.PrimaryKeyRelatedField(read_only=True)  # For reading
    
    class Meta:
        model = Review
        fields = ["id", "user", "product", "product_id", "rating", "review", "created", "updated"]
    
    def create(self, validated_data):
        # Get the user from the request context
        user = self.context['request'].user
        # Remove product_id from validated_data and get its value
        product_id = validated_data.pop('product_id')
        # Get the product instance
        product = Product.objects.get(id=product_id)
        # Create and return the review with the user
        return Review.objects.create(
            product=product,
            user=user,
            **validated_data
        )

class CategoryListSerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "is_featured", "subcategories"]
    
    def get_subcategories(self, obj):
        children = obj.get_children()
        return CategoryListSerializer(children, many=True).data



class ProductListSerializer(serializers.ModelSerializer):
    isExclusive = serializers.BooleanField(source='is_exclusive')
    oldPrice = serializers.DecimalField(source='old_price', max_digits=10, decimal_places=2, coerce_to_string=False, allow_null=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=False)
    category = serializers.SerializerMethodField()
    subCategory = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    quantity = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()
    sizes = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source='created_at', format='%Y-%m-%dT%H:%M:%S.000Z')

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'isExclusive', 'gender', 'price', 'oldPrice',
            'discount', 'category', 'subCategory', 'rating', 'status', 'quantity',
            'images', 'colors', 'sizes', 'description', 'createdAt'
        ]

    def get_category(self, obj):
        if obj.category.exists():
            return obj.category.first().slug
        return "uncategorized"

    def get_subCategory(self, obj):
        for category in obj.category.all():
            if category.parent:
                return category.slug
        return "uncategorized"

    def get_status(self, obj):
        total_quantity = sum(v.quantity for v in obj.variants.all())
        return "inStock" if total_quantity > 0 else "outOfStock"

    def get_quantity(self, obj):
        return sum(v.quantity for v in obj.variants.all())

    def get_images(self, obj):
        request = self.context.get('request')
        if obj.is_exclusive and (not request or not request.user.is_authenticated):
            # Return only the first image or a placeholder for exclusive products
            first_image = obj.images.filter(is_primary=True).first() or obj.images.first()
            if first_image and first_image.image:
                return [request.build_absolute_uri(first_image.image.url)] if request else [first_image.image.url]
            return []
            
        primary_images = obj.images.filter(is_primary=True).order_by('id')
        other_images = obj.images.filter(is_primary=False).order_by('id')
        all_images = list(primary_images) + list(other_images)
        
        if request:
            return [request.build_absolute_uri(img.image.url) for img in all_images if img and img.image]
        return [img.image.url for img in all_images if img and img.image]

    def get_colors(self, obj):
        if obj.is_exclusive and not self.context.get('request', None) or not self.context['request'].user.is_authenticated:
            return []
        return list(set(v.color.lower() for v in obj.variants.all() if v.color))

    def get_sizes(self, obj):
        if obj.is_exclusive and not self.context.get('request', None) or not self.context['request'].user.is_authenticated:
            return []
        return list(set(v.size.upper() for v in obj.variants.all() if v.size))

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        
        # For unauthenticated users viewing exclusive products
        if instance.is_exclusive and (not request or not request.user.is_authenticated):
            return {
                'id': str(instance.id),
                'name': instance.name,
                'isExclusive': True,
                'slug': instance.slug,
                'images': self.get_images(instance),  # Limited images
                'message': 'Login to view this exclusive product',
                'requires_auth': True
            }
            
        # For all other cases, ensure proper data formatting
        data['id'] = str(data['id'])
        data['rating'] = float(data.get('rating', 0))
        
        # Ensure price and oldPrice are properly formatted
        if 'price' in data and data['price'] is not None:
            data['price'] = str(round(float(data['price']), 2))
        if 'oldPrice' in data and data['oldPrice'] is not None:
            data['oldPrice'] = str(round(float(data['oldPrice']), 2))
            
        return data
 

class CategoryDetailSerializer(serializers.ModelSerializer):
    products = ProductListSerializer(many=True, read_only=True)
    subcategories = CategoryListSerializer(many=True, read_only=True, source='children')
    
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "image", "products", "subcategories"]
        read_only_fields = ['slug']

class ProductRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRating 
        fields =[ "id", "average_rating", "total_reviews"]


class ProductDetailSerializer(ProductListSerializer):
    variants = serializers.SerializerMethodField()
    reviewStats = serializers.SerializerMethodField()
    
    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ['variants', 'reviewStats']
    
    def get_variants(self, obj):
        variants = obj.variants.all()
        return [{
            'id': variant.id,
            'color': variant.color,
            'size': variant.size,
            'quantity': variant.quantity,
            'price': float(variant.price),  # Convert Decimal to float for JSON
            'images': [
                self.context['request'].build_absolute_uri(img.image.url)
                for img in variant.images.all()
                if img.image and hasattr(img.image, 'url')
            ]
        } for variant in variants]
 
    def get_reviewStats(self, obj):
        reviews = Review.objects.filter(product=obj)
        rating_avg = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        rating_count = reviews.count()
        
        # Calculate rating breakdown
        breakdown = {str(i): 0 for i in range(1, 6)}
        for i in range(1, 6):
            breakdown[str(i)] = reviews.filter(rating=i).count()
        
        return {
            'rating': round(float(rating_avg), 1),
            'totalReviews': rating_count,
            'breakdown': breakdown
        }
        

class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
 
    class Meta:
        model = ProductImage
        fields = ['url']
    
    def get_url(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return self.context['request'].build_absolute_uri(obj.image.url)
        return ""


class CartItemSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField()
    sub_total = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem 
        fields = ["id", "product", "quantity", "sub_total"]
    
    def get_product(self, obj):
        # Return only essential product fields
        return {
            "id": obj.product.id,
            "name": obj.product.name,
            "price": str(obj.product.price),
            "image": self.context['request'].build_absolute_uri(obj.product.images.first().image.url) if obj.product.images.exists() else None
        }
    
    def get_sub_total(self, obj):
        return float(obj.product.price) * obj.quantity


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(source='cartitems', many=True, read_only=True)
    total = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart 
        fields = ["id", "items", "total"]
    
    def get_total(self, obj):
        return float(sum(
            item.quantity * item.product.price 
            for item in obj.cartitems.all()
        ))
    

class CartStatSerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()
    total_quantity = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ['id', 'item_count', 'total_quantity', 'items']

    def get_item_count(self, cart):
        return cart.cartitems.count()

    def get_total_quantity(self, cart):
        return cart.cartitems.aggregate(total=Sum('quantity'))['total'] or 0
        
    def get_items(self, cart):
        items = []
        for item in cart.cartitems.all():
            items.append({
                'product_name': item.product.name,
                'category': item.product.category.name if item.product.category else "",
                'subcategory': item.product.subcategory.name if hasattr(item.product, 'subcategory') and item.product.subcategory else "",
                'quantity': item.quantity,
                'price': str(item.product.price),
                'total': float(item.quantity * item.product.price),
                'color': item.variant.color if item.variant and hasattr(item.variant, 'color') else None,
                'size': item.variant.size if item.variant and hasattr(item.variant, 'size') else None
            })
        return items


class WishlistSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    product = ProductListSerializer(read_only=True)
    class Meta:
        model = Wishlist 
        fields = ["id", "user", "product", "created"]


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    class Meta:
        model = OrderItem
        fields = ["id", "quantity", "product"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(read_only=True, many=True)
    class Meta:
        model = Order 
        fields = ["id", "stripe_checkout_id", "amount", "items", "status", "created_at"]



class CustomerAddressSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)
    
    class Meta:
        model = CustomerAddress
        fields = ['id', 'customer', 'street', 'city', 'state', 'phone']

class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddress
        fields = ['id', 'street', 'city', 'state', 'phone']
        read_only_fields = ['customer']  # We'll set this in the view

    def create(self, validated_data):
        # The customer will be set to the current user in the view
        return CustomerAddress.objects.create(**validated_data)

class SimpleCartSerializer(serializers.ModelSerializer):
    num_of_items = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart 
        fields = ["id", "cart_code", "num_of_items"]

    def get_num_of_items(self, cart):
        num_of_items = sum([item.quantity for item in cart.cartitems.all()])
        return num_of_items  # <-- Added return statement


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'is_read', 'created_at']
        read_only_fields = ['user']

class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'subject', 'message', 'created_at', 'is_resolved']
        read_only_fields = ['created_at', 'is_resolved']

class HelpCenterArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpCenterArticle
        fields = ['id', 'title', 'slug', 'content', 'category', 'is_published', 'created_at', 'updated_at']
        read_only_fields = ['slug', 'created_at', 'updated_at']