from django import forms
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import BaseUserManager

# Create your models here.

from django.contrib.auth.models import BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        if password is None:
            raise ValueError('The Password field must be set')  
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None  # CRITICAL: Disable username field
    USER_TYPE_CHOICES = (
        ('customer', 'Customer'),
        ('blog_editor', 'Blog Editor'),
        ('admin', 'Admin'),
    )
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    profile_picture_url = models.URLField(blank=True, null=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='customer')

    USERNAME_FIELD = 'email'  # Use email for authentication
    REQUIRED_FIELDS = []  # No additional fields required for superuser

    def __str__(self):
        return self.full_name or self.email

    
    # Add this property for backward compatibility with your existing code
    @property
    def is_blog_editor(self):
        return self.user_type == 'blog_editor' or self.is_staff

    def __str__(self):
        return self.full_name or self.email
    

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    image = models.FileField(upload_to="category_img", blank=True, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):

        if not self.slug:
            self.slug = slugify(self.name)
            unique_slug = self.slug
            counter = 1
            if Product.objects.filter(slug=unique_slug).exists():
                unique_slug = f'{self.slug}-{counter}'
                counter += 1
            self.slug = unique_slug
        
        super().save(*args, **kwargs)
  

class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    slug = models.SlugField(unique=True, blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)

    featured = models.BooleanField(default=False)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, related_name="products",  blank=True, null=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):

        if not self.slug:
            self.slug = slugify(self.name)
            unique_slug = self.slug
            counter = 1
            if Product.objects.filter(slug=unique_slug).exists():
                unique_slug = f'{self.slug}-{counter}'
                counter += 1
            self.slug = unique_slug
        
        super().save(*args, **kwargs)


import uuid

class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carts",
        null=True,  # Allow NULL in the database
        blank=True  # Allow blank in forms
    )
    cart_code = models.CharField(max_length=11, unique=True, default=uuid.uuid4().hex[:11])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Cart {} - {}".format(self.cart_code, self.user.email if self.user else "No User")


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="cartitems")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="item")
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in cart {self.cart.cart_code}"
    


class Review(models.Model):

    RATING_CHOICES = [
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent'),
    ]


    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveIntegerField(choices=RATING_CHOICES)
    review = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.user.email}'s review on {self.product.name}"
    
    class Meta:
        unique_together = ["user", "product"]
        ordering = ["-created"]



class ProductRating(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='rating')
    average_rating = models.FloatField(default=0.0)
    total_reviews = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.average_rating} ({self.total_reviews} reviews)"




class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlists")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlist")
    created = models.DateTimeField(auto_now_add=True) 

    class Meta:
        unique_together = ["user", "product"]

    def __str__(self):
        return f"{self.user.email} - {self.product.name}"
    



class Order(models.Model):
    paystack_checkout_id = models.CharField(max_length=255, unique=True, default=uuid.uuid4)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='NGN')
    customer_email = models.EmailField()
    status = models.CharField(max_length=20, choices=[("Pending", "Pending"), ("Paid", "Paid")], default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.paystack_checkout_id} - {self.status}"
    

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"Order {self.product.name} - {self.order.paystack_checkout_id}"
    

# In apiApp/models.py - update CustomerAddress model
# In apiApp/models.py - update CustomerAddress model
class CustomerAddress(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)  # Make nullable
    alt_phone = models.CharField(max_length=20, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)  # Make nullable
    landmark = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)  # Make nullable
    state = models.CharField(max_length=100, blank=True, null=True)  # Make nullable
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.customer.email} - {self.full_name or 'No Name'} - {self.city or 'No City'}"


# Notification Models
class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # For email notifications
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.title}"

class EmailNotificationPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product_updates = models.BooleanField(default=True)
    order_status = models.BooleanField(default=True)
    promotions = models.BooleanField(default=False)
    new_arrivals = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.email} - Preferences"

# Contact Message Model
class ContactMessage(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.name} - {self.subject}"

# Help Center Models
class HelpCenterArticle(models.Model):
    CATEGORY_CHOICES = [
        ('general', 'General'),
        ('orders', 'Orders'),
        ('payments', 'Payments'),
        ('shipping', 'Shipping'),
        ('account', 'Account'),
    ]
    
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    content = models.TextField()
    faq = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order', 'title']
    
    def __str__(self):
        return self.title
