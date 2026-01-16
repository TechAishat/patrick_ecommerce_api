from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from django.views.decorators.csrf import csrf_exempt

# Create a router and register our viewsets with it (if using DRF)
# router = DefaultRouter()
# router.register(r'products', views.ProductViewSet)

urlpatterns = [
    # Products
    path("products/", views.product_list, name="product-list"),
    path("products/<slug:slug>/", views.product_detail, name="product-detail"),
     
    # Categories
    path("categories/", views.category_list, name="category-list"),
    path("categories/<slug:slug>/", views.category_detail, name="category-detail"),
    
    # Cart
    path("cart/", include([
        path("", views.get_cart, name="cart-detail"),
        path("add/", views.add_to_cart, name="add-to-cart"),
        path("items/<int:pk>/update/", views.update_cartitem_quantity, name="update-cart-item"),
        path("items/<int:pk>/delete/", views.delete_cartitem, name="delete-cart-item"),
    ])),
    
    # Reviews
    path("reviews/", include([
        path("add/", views.add_review, name="add-review"),
        path("<int:pk>/update/", views.update_review, name="update-review"),
        path("<int:pk>/delete/", views.delete_review, name="delete-review"),
    ])), 
    
    # Checkout & Orders
    path("checkout/", views.create_checkout_session, name="create-checkout"),
    path("webhook/", csrf_exempt(views.paystack_webhook), name="webhook"),
    path("orders/", views.get_orders, name="order-list"),
    
    # User Management
    path("users/", include([
        path("create/", views.create_user, name="create-user"),
        path("check/<str:email>/", views.existing_user, name="check-user"),
        path("address/", include([
            path("", views.get_address, name="user-address"),
            path("add/", views.add_address, name="add-address"),
        ])),
        path("wishlist/", include([
            path("", views.my_wishlists, name="wishlist"),
            path("check/", views.product_in_wishlist, name="check-wishlist"),
            path("add/", views.add_to_wishlist, name="add-to-wishlist"),
        ])),
    ])),
    
    # Search
    path("search/", views.product_search, name="search"),

    path('', views.home, name='home'),
    
    # Google Authentication (Using Allauth)
    path("accounts/", include("allauth.urls")),  # Include allauth routes for login, logout, etc.

    # Password Reset URLs
    path("password-reset/", views.password_reset_request, name="password-reset-request"),
    path("password-reset-confirm/<uidb64>/<token>/", views.reset_password, name="password-reset-confirm"),
]


# from django.urls import path
# from . import views

# urlpatterns = [
#     path("product_list/", views.product_list, name="product_list"),  # Added trailing slash for consistency
#     path("products/<slug:slug>/", views.product_detail, name="product_detail"),  # Added trailing slash
#     path("category_list/", views.category_list, name="category_list"),  # Added trailing slash
#     path("categories/<slug:slug>/", views.category_detail, name="category_detail"),  # Added trailing slash
#     path("add_to_cart/", views.add_to_cart, name="add_to_cart"),
#     path("update_cartitem_quantity/", views.update_cartitem_quantity, name="update_cartitem_quantity"),
#     path("add_review/", views.add_review, name="add_review"),
#     path("update_review/<int:pk>/", views.update_review, name="update_review"),
#     path("delete_review/<int:pk>/", views.delete_review, name="delete_review"),
#     path("delete_cartitem/<int:pk>/", views.delete_cartitem, name="delete_cartitem"),
#     path("add_to_wishlist/", views.add_to_wishlist, name="add_to_wishlist"),
#     path("search/", views.product_search, name="search"),  # Added trailing slash

#     path("create_checkout_session/", views.create_checkout_session, name="create_checkout_session"),
#     path("webhook/", views.paystack_webhook, name="webhook"),  # Standardized function name

#     # Newly Added
#     path("get_orders/", views.get_orders, name="get_orders"),  # Added trailing slash
#     path("create_user/", views.create_user, name="create_user"),
#     path("existing_user/<str:email>/", views.existing_user, name="existing_user"),  # Added trailing slash
#     path("add_address/", views.add_address, name="add_address"),
#     path("get_address/", views.get_address, name="get_address"),  # Added trailing slash
#     path("my_wishlists/", views.my_wishlists, name="my_wishlists"),  # Added trailing slash
#     path("product_in_wishlist/", views.product_in_wishlist, name="product_in_wishlist"),  # Added trailing slash
#     path("get_cart/<str:cart_code>/", views.get_cart, name="get_cart"),  # Added trailing slash
#     path("get_cart_stat/", views.get_cart_stat, name="get_cart_stat"),  # Added trailing slash
#     path("product_in_cart/", views.product_in_cart, name="product_in_cart"),  # Added trailing slash
# ]