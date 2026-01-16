from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Category, Tag, Post, Comment

User = get_user_model()

# Register models with the default admin site too
admin.site.register(Category)
admin.site.register(Tag)
admin.site.register(Post)
admin.site.register(Comment)

class BlogAdminSite(admin.AdminSite):
    site_header = 'Blog Administration'
    site_title = 'Blog Admin'
    index_title = 'Blog Administration'
    login_template = 'admin/login.html'

# Create the admin site instance
blog_admin_site = BlogAdminSite(name='blog_admin')

@admin.register(Category, site=blog_admin_site)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    list_filter = ['created_at']
    date_hierarchy = 'created_at'

@admin.register(Tag, site=blog_admin_site)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']
    list_filter = ['created_at']
    date_hierarchy = 'created_at'

@admin.register(Post, site=blog_admin_site)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'author', 'publish_date', 'view_count']
    list_filter = ['status', 'publish_date', 'author', 'categories', 'tags']
    search_fields = ['title', 'content', 'excerpt']
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ['author']
    date_hierarchy = 'publish_date'
    filter_horizontal = ['categories', 'tags']
    readonly_fields = ['view_count', 'created_at', 'updated_at']

@admin.register(Comment, site=blog_admin_site)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['post', 'author', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'created_at', 'updated_at']
    search_fields = ['content', 'author__username', 'post__title']
    raw_id_fields = ['post', 'author']
    actions = ['approve_comments', 'reject_comments']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_approved']

    def approve_comments(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} comment(s) approved successfully.")
    approve_comments.short_description = "Approve selected comments"

    def reject_comments(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f"{updated} comment(s) rejected.")
    reject_comments.short_description = "Reject selected comments"