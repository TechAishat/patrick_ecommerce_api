from django.contrib import admin
from .models import (
    Cart, CartItem, Category, CustomUser, Order, OrderItem, Product, 
    ProductRating, Review, Wishlist, CustomerAddress, Notification,
    ContactMessage, HelpCenterArticle, ProductImage
)
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils.http import urlencode

# Register your models here.

class CustomUserAdmin(UserAdmin):
    list_display = ("email", "full_name", "user_type", "is_staff")
    list_filter = ("user_type", "is_staff", "is_active")
    search_fields = ("email", "full_name")
    readonly_fields = ('date_joined', 'last_login')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('full_name', 'profile_picture_url', 'user_type')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    
    ordering = ('email',)

admin.site.register(CustomUser, CustomUserAdmin)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ['preview_image']

    def preview_image(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="100" height="auto" />')
        return "No Image"
    preview_image.short_description = 'Preview'

class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "is_featured", "is_exclusive", "status", "display_primary_image"]
    list_filter = ("status", "is_featured", "is_exclusive", "gender", "category")
    search_fields = ("name", "description", "sku_base")
    readonly_fields = ('created_at', 'updated_at', 'slug')
    filter_horizontal = ('category',)
    inlines = [ProductImageInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'category')
        }),
        ('Pricing', {
            'fields': ('price', 'old_price', 'discount')
        }),
        ('Details', {
            'fields': ('sku_base', 'gender', 'colors', 'sizes', 'review_count')
        }),
        ('Status', {
            'fields': ('is_featured', 'is_exclusive', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def display_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return mark_safe(f'<img src="{primary_image.image.url}" width="50" height="50" style="object-fit: cover;" />')
        return "No Image"
    display_primary_image.short_description = 'Image'
    display_primary_image.allow_tags = True


class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "parent", "is_featured", "display_order"]
    list_filter = ("is_featured", "parent")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ('preview_image',)

    def preview_image(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="200" height="auto" />')
        return "No Image"
    preview_image.short_description = 'Image Preview'

class ReviewAdmin(admin.ModelAdmin):
    list_display = ["user", "product", "rating", "created", "updated"]
    list_filter = ("rating", "created")
    search_fields = ("user__email", "product__name", "review")
    readonly_fields = ('created', 'updated')

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1

class CartAdmin(admin.ModelAdmin):
    list_display = ("cart_code", "user", "created_at", "updated_at", "item_count", "cart_total")
    inlines = [CartItemInline]
    readonly_fields = ('created_at', 'updated_at')
    
    def item_count(self, obj):
        return obj.cartitems.count()
    item_count.short_description = 'Items'
    
    def cart_total(self, obj):
        return sum(item.product.price * item.quantity for item in obj.cartitems.all())
    cart_total.short_description = 'Total'

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    readonly_fields = ('product', 'quantity')

class OrderAdmin(admin.ModelAdmin):
    list_display = ("paystack_checkout_id", "customer_email", "amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("paystack_checkout_id", "customer_email")
    inlines = [OrderItemInline]
    readonly_fields = ('created_at',)

class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = ("customer", "street", "city", "state", "phone")
    search_fields = ("customer__email", "street", "city", "state")
    list_filter = ("state", "city")

class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__email", "title", "message")
    readonly_fields = ('created_at',)

class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "is_resolved", "created_at")
    list_filter = ("is_resolved", "created_at")
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ('created_at',)

class HelpCenterArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_published", "created_at")
    list_filter = ("category", "is_published")
    search_fields = ("title", "content")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ('created_at', 'updated_at')

# Register all models with their admin classes
admin.site.register(Product, ProductAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(CartItem)
admin.site.register(ProductRating)
admin.site.register(Wishlist)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(CustomerAddress, CustomerAddressAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(ContactMessage, ContactMessageAdmin)
admin.site.register(HelpCenterArticle, HelpCenterArticleAdmin)
admin.site.register(ProductImage)