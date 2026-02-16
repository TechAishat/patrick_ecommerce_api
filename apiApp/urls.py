from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from . import views
from .views import (
    get_cart, add_to_cart, create_cart, product_list, 
    ProductDetailView, category_list, category_detail, 
    verify_payment, product_ratings, resend_verification_email, 
    VerifyEmailView, GoogleAuthURL, GoogleLogin, ProductVariantView,
)

app_name = 'api'  # Add this for namespacing

urlpatterns = [
    # JWT Authentication
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Products
    path('products/', product_list, name='product-list'),
    path('products/<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/<slug:product_slug>/variants/', ProductVariantView.as_view(), name='product-variants'),
    
    
    # Categories
    path("categories/", category_list, name="category-list"),
    path("categories/<slug:slug>/", category_detail, name="category-detail"),
    
    # Cart
    path("cart/", include([
        path("", get_cart, name="cart-detail"),
        path("add/", add_to_cart, name="add-to-cart"),
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
    path('verify-payment/', views.verify_payment, name='verify-payment'),
    
    # User Management
    path("users/", include([
        path("register/", views.register, name="register"),
        path("login/", views.login_user, name="login"),
        path("logout/", views.logout_user, name="logout"),
        path("me/", views.user_profile, name="user-profile"),
        path("verify-email/<str:token>/", VerifyEmailView.as_view(), name="verify-email"),
        path("resend-verification/", resend_verification_email, name="resend-verification"),
        path('check/<str:email>/', views.check_user, name='check-user'),
        path("address/", include([
            path("", views.get_address, name="user-address"),
            path("add/", views.add_address, name="add-address"),
        ])),

        # Password Reset
        path("password-reset/", include([
            path("", views.PasswordResetRequestView.as_view(), name="password-reset-request"),
            path("confirm/<uidb64>/<token>/", views.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
        ])),

        path('google/', GoogleAuthURL.as_view(), name='google_auth'),
        path('google/callback/', GoogleLogin.as_view(), name='google_callback'),
        
        path("wishlist/", include([
            path("", views.my_wishlists, name="wishlist"),
            path("check/", views.product_in_wishlist, name="check-wishlist"),
            path("add/", views.add_to_wishlist, name="add-to-wishlist"),
        ])),
    ])),

    path('test-email/', views.test_email, name='test-email'),    
    
    # Ratings
    path("products/<int:product_id>/ratings/", product_ratings, name="product-ratings"),
    path("ratings/", views.RatingListCreateView.as_view(), name="rating-list"),
    path("ratings/<int:pk>/", views.RatingDetailView.as_view(), name="rating-detail"),

    # Track Order
    path("track-order/", views.track_order, name="track-order"),
    
    # Notifications
    path("notifications/", include([
        path("", views.notifications, name="notifications"),
        path("<int:notification_id>/read/", views.mark_notification_read, 
             name="mark-notification-read"),
    ])),
    
    # Contact Us
    path("contact/", include([
        path("", views.contact_us, name="contact-us"),
        path("messages/", views.contact_messages, name="contact-messages"),
        path("messages/<int:message_id>/resolve/", 
            views.resolve_contact_message, 
            name="resolve-contact-message"),
    ])),
    
    # Help Center
    path("help-center/", include([
        path("", views.help_center_articles, name="help-center-articles"),
        path("<slug:slug>/", views.help_center_article_detail, 
             name="help-center-article-detail"),
        path("admin/", include([
            path("", views.manage_help_center, name="manage-help-center"),
            path("<int:article_id>/", views.manage_help_center, 
                 name="manage-help-center-detail"),
        ])),
    ])),
    
    # Search
    path("search/", views.product_search, name="search"),

    # Home
    path("", views.home, name="home"),
    
    # Authentication
    path("accounts/", include("allauth.urls")),  # Allauth routes
    
    # Password Reset
    path("password-reset/", views.password_reset_request, name="password-reset-request"),
    path("password-reset-confirm/<uidb64>/<token>/", 
        views.reset_password, 
        name="password-reset-confirm"
    ),
]