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
        fields = ["id", "name", "image", "slug", "is_featured", "subcategories"]
    
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
        # Return the first category's slug or a default
        if obj.category.exists():
            return obj.category.first().slug
        return "uncategorized"

    def get_subCategory(self, obj):
        # Find the first subcategory
        for category in obj.category.all():
            if category.parent:
                return category.slug
        return "uncategorized"  # or None if you prefer

    def get_status(self, obj):
        total_quantity = sum(v.quantity for v in obj.variants.all())
        return "inStock" if total_quantity > 0 else "outOfStock"

    def get_quantity(self, obj):
        return sum(v.quantity for v in obj.variants.all())

    def get_images(self, obj):
        # Get primary images first, then others
        primary_images = obj.images.filter(is_primary=True).order_by('id')
        other_images = obj.images.filter(is_primary=False).order_by('id')
        all_images = list(primary_images) + list(other_images)
        
        request = self.context.get('request')
        if request:
            return [request.build_absolute_uri(img.image.url) for img in all_images if img.image]
        return []

    def get_colors(self, obj):
        # Return unique colors from variants
        return list(set(v.color.lower() for v in obj.variants.all() if v.color))

    def get_sizes(self, obj):
        # Return unique sizes from variants
        return list(set(v.size.upper() for v in obj.variants.all() if v.size))

    def to_representation(self, instance):
        # Convert the response to match the desired format
        data = super().to_representation(instance)
        
        # Convert ID to string if needed
        data['id'] = str(data['id'])
        
        # Ensure rating is a float with one decimal place
        data['rating'] = float(data.get('rating', 0))
        
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
    product = ProductListSerializer(read_only=True)
    sub_total = serializers.SerializerMethodField()
    class Meta:
        model = CartItem 
        fields = ["id", "product", "quantity", "sub_total"]

    
    def get_sub_total(self, cartitem):
        total = cartitem.product.price * cartitem.quantity 
        return total

class CartSerializer(serializers.ModelSerializer):
    cartitems = CartItemSerializer(read_only=True, many=True)
    cart_total = serializers.SerializerMethodField()
    user = UserSerializer(read_only=True)  # Add this line to include user details
    
    class Meta:
        model = Cart 
        fields = ["id", "cart_code", "user", "cartitems", "cart_total", "created_at", "updated_at"]
        read_only_fields = ["user", "cart_code", "created_at", "updated_at"]  # Ensure these are read-only

    def get_cart_total(self, cart):
        items = cart.cartitems.all()
        total = sum([item.quantity * item.product.price for item in items])
        return total
    

class CartStatSerializer(serializers.ModelSerializer): 
    total_quantity = serializers.SerializerMethodField()
    class Meta:
        model = Cart 
        fields = ["id", "cart_code", "total_quantity"]

    def get_total_quantity(self, cart):
        items = cart.cartitems.all()
        total = sum([item.quantity for item in items])
        return total

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