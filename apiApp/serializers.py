from rest_framework import serializers 
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Cart, CartItem, CustomerAddress, Order, OrderItem, Product, Category, ProductRating, Review, Wishlist, Notification, EmailNotificationPreference

User = get_user_model()

# Product Serializers
class ProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "slug", "image", "price"]

class ProductRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRating 
        fields = ["id", "average_rating", "total_reviews"]

# User Serializer (must come before ReviewSerializer)
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
 
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "profile_picture_url", "password"]
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise ValidationError("This email is already in use.")
        return value
 
    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(validated_data.pop('password'))
        user.save()
        return user

# Review Serializer (now UserSerializer is defined)
class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Review 
        fields = ["id", "user", "rating", "review", "created", "updated"]

# Product Detail Serializer
class ProductDetailSerializer(serializers.ModelSerializer):
    reviews = ReviewSerializer(read_only=True, many=True)
    rating = ProductRatingSerializer(read_only=True)
    poor_review = serializers.SerializerMethodField()
    fair_review = serializers.SerializerMethodField()
    good_review = serializers.SerializerMethodField()
    very_good_review = serializers.SerializerMethodField()
    excellent_review = serializers.SerializerMethodField()
    similar_products = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "description", "slug", "image", "price", "reviews", "rating", 
                  "similar_products", "poor_review", "fair_review", "good_review",
                  "very_good_review", "excellent_review"]
        
    def get_similar_products(self, product):
        products = Product.objects.filter(category=product.category).exclude(id=product.id)
        serializer = ProductListSerializer(products, many=True)
        return serializer.data
    
    def get_poor_review(self, product):
        return product.reviews.filter(rating=1).count()
    
    def get_fair_review(self, product):
        return product.reviews.filter(rating=2).count()
    
    def get_good_review(self, product):
        return product.reviews.filter(rating=3).count()
    
    def get_very_good_review(self, product):
        return product.reviews.filter(rating=4).count()
    
    def get_excellent_review(self, product):
        return product.reviews.filter(rating=5).count()

# Category Serializers
class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "image", "slug"]

class CategoryDetailSerializer(serializers.ModelSerializer):
    products = ProductListSerializer(many=True, read_only=True)
    class Meta:
        model = Category
        fields = ["id", "name", "image", "products"]

# Cart Serializers
class CartItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    sub_total = serializers.SerializerMethodField()
    class Meta:
        model = CartItem 
        fields = ["id", "product", "quantity", "sub_total"]

    def get_sub_total(self, cartitem):
        return cartitem.product.price * cartitem.quantity

class CartSerializer(serializers.ModelSerializer):
    cartitems = CartItemSerializer(read_only=True, many=True)
    cart_total = serializers.SerializerMethodField()
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Cart 
        fields = ["id", "cart_code", "user", "cartitems", "cart_total", "created_at", "updated_at"]
        read_only_fields = ["user", "cart_code", "created_at", "updated_at"]

    def get_cart_total(self, cart):
        return sum([item.quantity * item.product.price for item in cart.cartitems.all()])

class SimpleCartSerializer(serializers.ModelSerializer):
    num_of_items = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart 
        fields = ["id", "cart_code", "num_of_items"]

    def get_num_of_items(self, cart):
        return sum([item.quantity for item in cart.cartitems.all()])

# Address Serializer (keep only one)
class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddress
        fields = ['id', 'street', 'city', 'state', 'phone']
        read_only_fields = ['customer']

    def create(self, validated_data):
        user = self.context['request'].user
        return CustomerAddress.objects.create(customer=user, **validated_data)

# Order Serializers
class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    class Meta:
        model = OrderItem
        fields = ["id", "quantity", "product"]

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(read_only=True, many=True)
    class Meta:
        model = Order 
        fields = ["id", "paystack_checkout_id", "amount", "items", "status", "created_at"]

# Wishlist Serializer
class WishlistSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    product = ProductListSerializer(read_only=True)
    class Meta:
        model = Wishlist 
        fields = ["id", "user", "product", "created"]

# Registration Serializers
class CustomerAddressRegistrationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    
    class Meta:
        model = CustomerAddress
        fields = ['id', 'fullName', 'phone', 'altPhone', 'street', 'landmark', 
                  'country', 'state', 'city', 'isDefault']
    
    def validate(self, data):
        if not data.get('isDefault', False):
            pass
        return data

class UserRegistrationSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    addresses = CustomerAddressRegistrationSerializer(many=True, required=False)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'confirm_password', 
                 'profile_picture_url', 'addresses']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def validate(self, data):
        # Handle typo in frontend: "comfirmPassword" instead of "confirm_password"
        if 'comfirmPassword' in self.initial_data:
            if data['password'] != self.initial_data['comfirmPassword']:
                raise serializers.ValidationError("Passwords don't match")
        elif 'confirm_password' in data:
            if data['password'] != data['confirm_password']:
                raise serializers.ValidationError("Passwords don't match")
        return data


    
    def create(self, validated_data):
            # Handle both 'address' and 'addresses' from frontend
            addresses_data = []
            if 'address' in self.initial_data:
                addresses_data = self.initial_data['address']
            elif 'addresses' in self.initial_data:
                addresses_data = self.initial_data['addresses']
            
            # Create user - get name from frontend data
            name = self.initial_data.get('name', '')  # Get 'name' from frontend
            profile_pic = self.initial_data.get('profilePic', '')  # Get 'profilePic' from frontend
            
            # Create user directly instead of using create_user
            user = User(
                email=validated_data['email'],
                full_name=name,
                profile_picture_url=profile_pic
            )
            user.set_password(validated_data['password'])  # Hash the password
            user.save()
            
            # Create addresses
            for address_data in addresses_data:
                CustomerAddress.objects.create(
                    customer=user,
                    full_name=address_data.get('fullName', ''),
                    phone=address_data.get('phone', ''),
                    alt_phone=address_data.get('altPhone', ''),
                    street=address_data.get('street', ''),
                    landmark=address_data.get('landmark', ''),
                    country=address_data.get('country', ''),
                    city=address_data.get('city', ''),
                    state=address_data.get('state', ''),
                    is_default=address_data.get('isDefault', False)
                )
            return user

# In apiApp/serializers.py (add at the end)
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'is_read', 'created_at', 'email_sent']
        read_only_fields = ['user']

class EmailNotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailNotificationPreference
        fields = ['product_updates', 'order_status', 'promotions', 'new_arrivals']