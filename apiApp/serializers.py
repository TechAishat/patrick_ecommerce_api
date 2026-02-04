from rest_framework import serializers 
from django.contrib.auth import get_user_model
from .models import (
    Cart, CartItem, CustomerAddress, Order, OrderItem, 
    Product, Category, ProductRating, Review, Wishlist, 
    Notification, ContactMessage, HelpCenterArticle, ProductImage
)
from django.contrib.auth import get_user_model
from rest_framework import serializers
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
    class Meta:
        model = Review 
        fields = ["id", "user", "rating", "review", "created", "updated"]


class ProductRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRating 
        fields =[ "id", "average_rating", "total_reviews"]

class ProductListSerializer(serializers.ModelSerializer):
    discount = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "primary_image", "price", 
            "old_price", "discount", "is_featured", "is_exclusive",
            "rating"
        ]
    
    def get_primary_image(self, obj):
        image = obj.images.filter(is_primary=True).first() or obj.images.first()
        if image and hasattr(image.image, 'url'):
            return self.context['request'].build_absolute_uri(image.image.url)
        return None
    
    def get_discount(self, obj):
        if obj.old_price and obj.old_price > obj.price:
            discount = ((obj.old_price - obj.price) / obj.old_price) * 100
            return round(discount)
        return 0

class CategoryListSerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ["id", "name", "image", "slug", "is_featured", "subcategories"]
    
    def get_subcategories(self, obj):
        children = obj.get_children()
        return CategoryListSerializer(children, many=True).data

class CategoryDetailSerializer(serializers.ModelSerializer):
    products = ProductListSerializer(many=True, read_only=True)
    subcategories = CategoryListSerializer(many=True, read_only=True, source='get_children')
    
    class Meta:
        model = Category
        fields = ["id", "name", "image", "products", "subcategories", "description"]


class ProductDetailSerializer(serializers.ModelSerializer):
    categories = CategoryListSerializer(many=True, read_only=True, source='category')
    category_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Category.objects.all(),
        write_only=True,
        source='category'
    )
    
    # Keep all the SerializerMethodField definitions
    images = serializers.SerializerMethodField()
    reviews = ReviewSerializer(read_only=True, many=True)
    rating = ProductRatingSerializer(read_only=True)
    poor_review = serializers.SerializerMethodField()
    fair_review = serializers.SerializerMethodField()
    good_review = serializers.SerializerMethodField()
    very_good_review = serializers.SerializerMethodField()
    excellent_review = serializers.SerializerMethodField()
    similar_products = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()
    sizes = serializers.SerializerMethodField()
    is_in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "description", "slug", "price", "old_price", "discount",
            "categories", "category_ids", "images", "reviews", "rating",
            "poor_review", "fair_review", "good_review", "very_good_review",
            "excellent_review", "similar_products", "colors", "sizes", "is_in_stock",
            "gender", "is_featured", "is_exclusive", "created_at", "status"
        ]
        read_only_fields = ["slug", "created_at", "categories", "status"]

    def get_images(self, obj):
        # Return empty list for now, you can implement this later
        return []

    def get_poor_review(self, obj):
        return None  # Implement this if needed

    def get_fair_review(self, obj):
        return None  # Implement this if needed

    def get_good_review(self, obj):
        return None  # Implement this if needed

    def get_very_good_review(self, obj):
        return None  # Implement this if needed

    def get_excellent_review(self, obj):
        return None  # Implement this if needed

    def get_similar_products(self, obj):
        # Return empty list for now, you can implement this later
        return []

    def get_colors(self, obj):
        return getattr(obj, 'colors', [])

    def get_sizes(self, obj):
        return getattr(obj, 'sizes', [])

    def create(self, validated_data):
        # Set default values
        validated_data.setdefault('colors', [])
        validated_data.setdefault('sizes', [])
        validated_data.setdefault('status', 'draft')
        validated_data.setdefault('is_featured', False)
        validated_data.setdefault('is_exclusive', False)
        validated_data.setdefault('review_count', 0)
        validated_data.setdefault('rating_field', 0.0)
        
        # Extract categories
        categories = validated_data.pop('category', [])
        
        # Create the product
        product = Product.objects.create(**validated_data)
        
        # Add categories
        if categories:
            product.category.set(categories)
        
        return product
        

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_primary', 'alt_text']
        read_only_fields = ['product']


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