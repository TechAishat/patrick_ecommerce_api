from django.contrib import admin
from .models import (
    Cart, CartItem, Category, CustomUser, Order, OrderItem, Product, 
    ProductRating, Review, Wishlist, CustomerAddress, Notification,
    ContactMessage, HelpCenterArticle, ProductImage, ProductVariant
)
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils.http import urlencode


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

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    max_num = 3
    fields = ('image', 'is_primary', 'preview_image')
    readonly_fields = ('preview_image',)
 
    def preview_image(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return mark_safe(f'<img src="{obj.image.url}" width="100" height="auto" />')
        return "No Image"
    preview_image.short_description = 'Preview'


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('color', 'size', 'quantity', 'price_override', 'is_in_stock_display')  # Changed is_in_stock to is_in_stock_display
    readonly_fields = ('is_in_stock_display',)  # Make sure this is in readonly_fields
    show_change_link = True
    classes = ('collapse',)
    
    def is_in_stock_display(self, obj):
        if obj.quantity > 0:
            return mark_safe('<span style="color: #2ecc71; font-weight: bold;">In Stock</span>')
        return mark_safe('<span style="color: #e74c3c; font-weight: bold;">Out of Stock</span>')
    is_in_stock_display.short_description = 'Stock Status'
    
    def has_add_permission(self, request, obj=None):
        return True
        
    def has_change_permission(self, request, obj=None):
        return True


class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        'display_thumbnail',
        'product_link',
        'color_display',
        'size_display',
        'quantity',
        'price_display',
        'stock_status',
    )
    
    list_filter = (
        'color', 
        'size',
        'product__category'
    )
    
    search_fields = (
        'product__name',
        'color',
        'size',
    )
    
    readonly_fields = (
        'stock_status',
        'display_thumbnail',
        'price_display'
    )
    
    fieldsets = (
        (None, {
            'fields': ('product', 'display_thumbnail')
        }),
        ('Variant Details', {
            'fields': (
                'color',
                'size',
                'quantity',
                'price_override',
                'price_display',
                'stock_status'
            )
        }),
    )

    def price_display(self, obj):
        return f"${obj.price:.2f}"
    price_display.short_description = 'Price'


    def display_thumbnail(self, obj):
        if obj.images.exists():
            img = obj.images.first()
            if hasattr(img.image, 'url'):
                return mark_safe(
                    f'<img src="{img.image.url}" width="50" height="50" '
                    'style="object-fit: cover; border-radius: 4px;" />'
                )
        return "No Image"
    display_thumbnail.short_description = 'Thumbnail'

    def product_link(self, obj):
        url = reverse('admin:apiApp_product_change', args=[obj.product.id])
        return mark_safe(f'<a href="{url}">{obj.product.name}</a>')
    product_link.short_description = 'Product'

    def sku_link(self, obj):
        url = reverse('admin:apiApp_productvariant_change', args=[obj.id])
        return mark_safe(f'<a href="{url}">{obj.sku or "-"}</a>')
    sku_link.short_description = 'SKU'

    def color_display(self, obj):
        return obj.color.title() if obj.color else "-"
    color_display.short_description = 'Color'

    def size_display(self, obj):
        return obj.size.upper() if obj.size else "-"
    size_display.short_description = 'Size'

    def stock_status(self, obj):
        if obj.quantity > 10:
            return mark_safe('<span style="color: #2ecc71;">In Stock</span>')
        elif obj.quantity > 0:
            return mark_safe('<span style="color: #f39c12;">Low Stock</span>')
        return mark_safe('<span style="color: #e74c3c;">Out of Stock</span>')
    stock_status.short_description = 'Status'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')

    class Media:
        css = {
            'all': ('admin/css/variants.css',)
        }



class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'price_display', 
        'stock_status',
        'quantity_in_stock',
        'available_variants',
        'is_featured_display',
        'is_exclusive_display',
        'status_display',
        'category_list'
    ]
    
    list_filter = (
        'status', 
        'is_featured', 
        'is_exclusive', 
        'gender', 
        'category',
        'created_at'
    )
    
    search_fields = (
        'name', 
        'description',
        'variants__color',
        'variants__size'
    )
    
    readonly_fields = (
        'created_at', 
        'updated_at', 
        'slug',
        'stock_status',
        'available_colors_display',
        'available_sizes_display'
    )
    
    filter_horizontal = ('category',)
    inlines = [ProductImageInline, ProductVariantInline]
    list_select_related = ()
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'category')
        }),
        ('Pricing', {
            'fields': ('price', 'old_price', 'discount')
        }),
        ('Inventory', {
            'fields': ('stock_status', 'available_colors_display', 'available_sizes_display')
        }),
        ('Details', {
            'fields': ('gender', 'review_count')
        }),
        ('Status', {
            'fields': ('is_featured', 'is_exclusive', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def available_variants(self, obj):
        return obj.variants.count()
    available_variants.short_description = 'Variants'

    def available_colors_display(self, obj):
        colors = obj.colors or []
        if not colors:
            return "No colors"
        return ", ".join(colors)
    available_colors_display.short_description = 'Available Colors'

    def available_sizes_display(self, obj):
        sizes = obj.sizes or []
        if not sizes:
            return "No sizes"
        return ", ".join(sizes)
    available_sizes_display.short_description = 'Available Sizes'

    def stock_status(self, obj):
        variants = obj.variants.all()
        if not variants.exists():
            return mark_safe('<span style="color: #95a5a6;">No Variants</span>')
            
        in_stock = any(v.quantity > 0 for v in variants)
        if in_stock:
            return mark_safe('<span style="color: #2ecc71;">In Stock</span>')
        return mark_safe('<span style="color: #e74c3c;">Out of Stock</span>')
    stock_status.short_description = 'Status'

    def quantity_in_stock(self, obj):
        total = sum(v.quantity for v in obj.variants.all())
        if total > 10:
            style = 'color: #2ecc71; font-weight: bold;'
        elif total > 0:
            style = 'color: #f39c12; font-weight: bold;'
        else:
            style = 'color: #e74c3c; font-weight: bold;'
        return mark_safe(f'<span style="{style}">{total}</span>')
    quantity_in_stock.short_description = 'Qty'


    def price_display(self, obj):
        if obj.old_price and obj.old_price > obj.price:
            return mark_safe(
                f'<span style="text-decoration: line-through; color: #999;">${obj.old_price}</span> '
                f'<span style="color: #e74c3c; font-weight: bold;">${obj.price}</span>'
            )
        return f"${obj.price}"
    price_display.short_description = 'Price'
    
    def status_display(self, obj):
        status_style = {
            'published': ('#2ecc71', 'Published'),
            'draft': ('#f39c12', 'Draft'),
            'archived': ('#e74c3c', 'Archived')
        }
        color, text = status_style.get(obj.status, ('#7f8c8d', obj.status))
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{text}</span>')
    status_display.short_description = 'Status'
    
    def stock_status(self, obj):
        total = sum(variant.quantity for variant in obj.variants.all())
        if total > 10:
            return mark_safe('<span style="color: #2ecc71;">In Stock</span>')
        elif total > 0:
            return mark_safe('<span style="color: #f39c12;">Low Stock</span>')
        return mark_safe('<span style="color: #e74c3c;">Out of Stock</span>')
    stock_status.short_description = 'In Stock'
    
    def quantity_in_stock(self, obj):
        total = sum(variant.quantity for variant in obj.variants.all())
        if total > 10:
            style = 'color: #2ecc71; font-weight: bold;'
        elif total > 0:
            style = 'color: #f39c12; font-weight: bold;'
        else:
            style = 'color: #e74c3c; font-weight: bold;'
        return mark_safe(f'<span style="{style}">{total}</span>')
    quantity_in_stock.short_description = 'Qty'
    
    def is_featured_display(self, obj):
        return obj.is_featured
    is_featured_display.short_description = 'Featured'
    is_featured_display.boolean = True
    
    def is_exclusive_display(self, obj):
        return obj.is_exclusive
    is_exclusive_display.short_description = 'Exclusive'
    is_exclusive_display.boolean = True
    
    def category_list(self, obj):
        return ", ".join([c.name for c in obj.category.all()])
    category_list.short_description = 'Categories'
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('variants', 'category')

    class Media:
        css = {
            'all': ('admin/css/products.css',)
        }



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
    list_display = ('id', 'customer', 'address_line1', 'city', 'state', 'country', 'is_default')
    list_filter = ('city', 'state', 'country', 'is_default')
    search_fields = ('customer__email', 'address_line1', 'city', 'postal_code')
    list_select_related = ('customer',)

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
admin.site.register(CustomUser, CustomUserAdmin)
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
admin.site.register(ProductVariant, ProductVariantAdmin)