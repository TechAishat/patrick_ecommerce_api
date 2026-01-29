from django.contrib import admin
from .models import Cart, CartItem, Category, CustomUser, Order, OrderItem, Product, ProductRating, Review, Wishlist, CustomerAddress
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

# Register your models here.

class CustomUserAdmin(UserAdmin):
    list_display = ("email", "full_name", "user_type", "is_staff")
    list_filter = ("user_type", "is_staff", "is_active")
    search_fields = ("email", "full_name")
    
    # Update fieldsets to remove username references
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('full_name', 'profile_picture_url', 'user_type')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    # Update add_fieldsets for creating users
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    
    # Update ordering to use email instead of username
    ordering = ('email',)

# Register CustomUser after the class is defined
admin.site.register(CustomUser, CustomUserAdmin)


class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "featured", "display_image"]

    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "No Image"
    display_image.short_description = 'Image Preview'

admin.site.register(Product, ProductAdmin)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]

admin.site.register(Category, CategoryAdmin)


class ReviewAdmin(admin.ModelAdmin):
    list_display = ["product", "rating", "review", 'created', "updated"]
admin.site.register(Review, ReviewAdmin)


class CartAdmin(admin.ModelAdmin):
    list_display = ("cart_code",)
admin.site.register(Cart, CartAdmin)


class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "product", "quantity")
admin.site.register(CartItem, CartItemAdmin)


class ProductRatingAdmin(admin.ModelAdmin):
    list_display = ("product", "average_rating", "total_reviews")
admin.site.register(ProductRating, ProductRatingAdmin)


class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user", "product")
admin.site.register(Wishlist, WishlistAdmin)


admin.site.register([Order, OrderItem, CustomerAddress])