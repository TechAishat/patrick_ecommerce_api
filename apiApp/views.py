import json
import uuid
import hmac
import hashlib
import requests
import logging
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail
from django.utils.encoding import force_str
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from .models import Cart, CartItem, Category, CustomerAddress, Order, OrderItem, Product, Review, Wishlist, Notification, ContactMessage, HelpCenterArticle
from .serializers import CartItemSerializer, CartSerializer, CategoryDetailSerializer, CategoryListSerializer, CustomerAddressSerializer, OrderSerializer, ProductListSerializer, ProductDetailSerializer, ReviewSerializer, SimpleCartSerializer, UserSerializer, WishlistSerializer,NotificationSerializer, ContactMessageSerializer, HelpCenterArticleSerializer
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


logger = logging.getLogger(__name__)

User = get_user_model()

@api_view(['GET', 'POST'])
def product_list(request):
    if request.method == 'POST':
        serializer = ProductDetailSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    products = Product.objects.filter(featured=True) 
    serializer = ProductListSerializer(products, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    serializer = ProductDetailSerializer(product)
    return Response(serializer.data)

@api_view(['GET'])
def category_list(request):
    categories = Category.objects.all()
    serializer = CategoryListSerializer(categories, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    serializer = CategoryDetailSerializer(category)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    try:
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            defaults={'user': request.user}
        )
        
        product = Product.objects.get(id=product_id)
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Product.DoesNotExist:
        return Response(
            {"detail": "Product not found."},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"detail": "Failed to add item to cart: {}".format(str(e))},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT'])
def update_cartitem_quantity(request):
    cartitem_id = request.data.get("item_id")
    quantity = request.data.get("quantity")

    cartitem = get_object_or_404(CartItem, id=cartitem_id)
    cartitem.quantity = int(quantity) 
    cartitem.save()

    serializer = CartItemSerializer(cartitem)
    return Response({"data": serializer.data, "message": "Cart item updated successfully!"})

@api_view(['POST'])
def add_review(request):
    product_id = request.data.get("product_id")
    email = request.data.get("email")
    rating = request.data.get("rating")
    review_text = request.data.get("review")

    product = get_object_or_404(Product, id=product_id)
    user = get_object_or_404(User, email=email)

    if Review.objects.filter(product=product, user=user).exists():
        return Response({"error": "You already dropped a review for this product"}, status=400)

    review = Review.objects.create(product=product, user=user, rating=rating, review=review_text)
    serializer = ReviewSerializer(review)
    return Response(serializer.data)

@api_view(['PUT'])
def update_review(request, pk):
    review = get_object_or_404(Review, id=pk) 
    rating = request.data.get("rating")
    review_text = request.data.get("review")

    review.rating = rating 
    review.review = review_text
    review.save()

    serializer = ReviewSerializer(review)
    return Response(serializer.data)

@api_view(['DELETE'])
def delete_review(request, pk):
    review = get_object_or_404(Review, id=pk) 
    review.delete()

    return Response("Review deleted successfully!", status=204)

@api_view(['DELETE'])
def delete_cartitem(request, pk):
    cartitem = get_object_or_404(CartItem, id=pk) 
    cartitem.delete()

    return Response("Cart item deleted successfully!", status=204)

@api_view(['POST'])
def add_to_wishlist(request):
    email = request.data.get("email")
    product_id = request.data.get("product_id")

    user = get_object_or_404(User, email=email)
    product = get_object_or_404(Product, id=product_id) 

    wishlist = Wishlist.objects.filter(user=user, product=product)
    if wishlist.exists():
        wishlist.delete()
        return Response("Wishlist item deleted successfully!", status=204)

    new_wishlist = Wishlist.objects.create(user=user, product=product)
    serializer = WishlistSerializer(new_wishlist)
    return Response(serializer.data)

@api_view(['GET'])
def product_search(request):
    query = request.query_params.get("query") 
    if not query:
        return Response("No query provided", status=400)
    
    products = Product.objects.filter(Q(name__icontains=query) | 
                                      Q(description__icontains=query) |
                                      Q(category__name__icontains=query))
    serializer = ProductListSerializer(products, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def create_checkout_session(request):
    """Create a Paystack checkout session."""
    cart_code = request.data.get("cart_code")
    email = request.data.get("email")
    
    if not cart_code or not email:
        return Response({'error': 'Both cart_code and email are required.'}, status=400)

    cart = get_object_or_404(Cart, cart_code=cart_code)

    total_amount = sum(int(item.product.price * 100) * item.quantity for item in cart.cartitems.all())  # Amount in Kobo

    payload = {
    'email': email,
    'amount': total_amount,
    'currency': 'NGN',
    'reference': str(uuid.uuid4()),
    'metadata': {'cart_code': cart_code},
    'callback_url': 'https://aishat.pythonanywhere.com/api/webhook/',
    'success_url': 'https://patrick-cavannii.netlify.app/payment/success/',
    'cancel_url': 'https://patrick-cavannii.netlify.app/payment/failed/',}

    response_data = call_paystack_api('transaction/initialize', payload)

    if response_data.get('status'):
        return Response({'authorization_url': response_data['data']['authorization_url']}, status=200)

    logger.error(f"Error from Paystack: {response_data.get('message', 'Unknown error.')}")
    return Response({'error': response_data.get('message', 'Payment initiation failed.')}, status=400)

def call_paystack_api(endpoint, payload):
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}', 
        'Content-Type': 'application/json',
    }

    try:
        response = requests.post(f'https://api.paystack.co/{endpoint}', json=payload, headers=headers)
        logger.debug(f"Response status: {response.status_code}, Response body: {response.text}")

        if response.status_code != 200:
            logger.error(f"Error from Paystack: {response.status_code}, Response: {response.text}")
            return {}

        return response.json()
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return {}

@csrf_exempt
@api_view(['GET', 'POST'])  # Allow both GET and POST
@permission_classes([AllowAny])
def paystack_webhook(request):
    """Handle Paystack webhook events."""
    # For GET requests (redirect from Paystack)
    if request.method == 'GET':
        reference = request.GET.get('reference')
        if reference:
            # Verify the transaction
            verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
            headers = {
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json",
            }
            response = requests.get(verify_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data['status'] and data['data']['status'] == 'success':
                    # Handle successful payment
                    cart_code = data['data']['metadata'].get('cart_code')
                    if cart_code:
                        fulfill_checkout(data['data'], cart_code)
                    return HttpResponse("Payment successful!", status=200)
        return HttpResponse("Invalid request", status=400)

    # For POST requests (webhook from Paystack)
    payload = request.body
    signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE')
    expected_signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode(),
        payload,
        hashlib.sha512
    ).hexdigest()

    if signature != expected_signature:
        return HttpResponse(status=403)  # Forbidden

    try:
        event = json.loads(payload)
        if event['event'] == 'charge.success':
            data = event['data']
            cart_code = data.get("metadata", {}).get("cart_code")
            fulfill_checkout(data, cart_code)
        elif event['event'] == 'charge.failed':
            logger.warning(f"Charge failed for cart code: {data.get('metadata', {}).get('cart_code')}")

        return HttpResponse(status=200)  # Acknowledge receipt

    except json.JSONDecodeError:
        return HttpResponse(status=400)  # Bad Request


def verify_paystack_webhook(payload, signature):
    paystack_secret = settings.PAYSTACK_SECRET_KEY
    hash = hmac.new(
        paystack_secret.encode('utf-8'),
        payload,
        digestmod=hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(hash, signature)

def fulfill_checkout(session, cart_code):
    """Fulfill the order after successful payment."""
    try:
        # Check if order with this reference already exists
        reference = session.get('reference')
        if not reference:
            logger.error("No reference found in session")
            return False

        if Order.objects.filter(paystack_checkout_id=reference).exists():
            logger.info(f"Order with reference {reference} already exists")
            return True

        # Get the cart
        cart = Cart.objects.get(cart_code=cart_code)
        
        # Create order
        order = Order.objects.create(
            paystack_checkout_id=reference,
            amount=float(session.get('amount', 0)) / 100,  # Convert from kobo to Naira
            currency=session.get('currency', 'NGN'),
            customer_email=session.get('customer', {}).get('email', ''),
            status='Paid'
        )
        
        # Add cart items to order
        for item in cart.cartitems.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity
            )
            
        # Clear the cart
        cart.cartitems.all().delete()
        
        logger.info(f"Order {order.id} created successfully for cart {cart_code}")
        return True
        
    except Exception as e:
        logger.error(f"Error fulfilling checkout: {str(e)}", exc_info=True)
        return False

@api_view(['GET'])
@permission_classes([AllowAny])
def verify_payment(request):
    """Handle Paystack payment verification callback."""
    reference = request.query_params.get('reference')
    
    if not reference:
        return Response(
            {"status": "error", "message": "No reference provided"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify the transaction with Paystack
    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.get(verify_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] and data['data']['status'] == 'success':
            # Handle successful payment
            cart_code = data['data']['metadata'].get('cart_code')
            if cart_code:
                fulfill_checkout(data['data'], cart_code)
            
            return Response(
                {
                    "status": "success",
                    "message": "Payment verified successfully",
                    "data": {
                        "reference": reference,
                        "amount": data['data']['amount'] / 100,  # Convert from kobo to Naira
                        "currency": data['data']['currency'],
                        "paid_at": data['data']['paid_at'],
                        "status": data['data']['status']
                    }
                },
                status=status.HTTP_200_OK
            )
        
        return Response(
            {
                "status": "failed",
                "message": data.get('message', 'Payment verification failed'),
                "data": data.get('data')
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    except requests.RequestException as e:
        logger.error(f"Error verifying payment: {str(e)}")
        return Response(
            {"status": "error", "message": "Failed to verify payment"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Newly Added 
@api_view(["POST"])
@permission_classes([AllowAny])
def create_user(request):
    # First, validate the user data
    user_serializer = UserSerializer(data=request.data)
    if not user_serializer.is_valid():
        return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Save the user
    user = user_serializer.save()
    
    # Generate auth token for the user
    from rest_framework.authtoken.models import Token
    token, created = Token.objects.get_or_create(user=user)
    
    # Return the token and next step information
    return Response({
        'token': token.key,
        'user_id': user.id,
        'email': user.email,
        'next_step': 'complete_address',
        'message': 'User created successfully. Please complete your address.'
    }, status=status.HTTP_201_CREATED)

# exiting user
@api_view(["GET"])
@permission_classes ([AllowAny])
def existing_user(request, email):
    try:
        User.objects.get(email=email) 
        return Response({"exists": True}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"exists": False}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes ([AllowAny])
def password_reset_request(request):
    email = request.data.get('email')
    user = get_object_or_404(User, email=email)  # Adjust if using CustomUser
    
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    reset_link = f"https://patrick-cavannii.netlify.app/reset-password/{uid}/{token}/"

    send_mail(
        'Password Reset Request',
        f'Please click the link below to reset your password:\n{reset_link}',
        'no-reply@example.com',
        [user.email],
        fail_silently=False,
    )

    return Response({"message": "Password reset link has been sent."}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes ([AllowAny])
def reset_password(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_object_or_404(User, pk=uid)

        if default_token_generator.check_token(user, token):
            new_password = request.data.get('new_password')
            user.set_password(new_password)
            user.save()
            return Response({"message": "Password has been reset."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response({"error": "User does not exist."}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET']) 
@permission_classes([IsAuthenticated])
def get_orders(request):
    email = request.query_params.get("email")
    orders = Order.objects.filter(customer_email=email)
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_address(request):
    """
    Add or update user's address.
    For authenticated users only - uses the request.user for identification.
    """
    serializer = CustomerAddressSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        # Update or create the address for the current user
        address, created = CustomerAddress.objects.update_or_create(
            customer=request.user,
            defaults=serializer.validated_data
        )
        return Response(CustomerAddressSerializer(address).data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
def get_address(request):
    email = request.query_params.get("email") 
    address = CustomerAddress.objects.filter(customer__email=email)

    if address.exists():
        address = address.last()
        serializer = CustomerAddressSerializer(address)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response({"error": "Address not found"}, status=status.HTTP_404_NOT_FOUND)

@api_view(["GET"])
def my_wishlists(request):
    email = request.query_params.get("email")
    wishlists = Wishlist.objects.filter(user__email=email)
    serializer = WishlistSerializer(wishlists, many=True)
    return Response(serializer.data)

@api_view(["GET"])
def product_in_wishlist(request):
    email = request.query_params.get("email")
    product_id = request.query_params.get("product_id")

    if Wishlist.objects.filter(product__id=product_id, user__email=email).exists():
        return Response({"product_in_wishlist": True})
    
    return Response({"product_in_wishlist": False})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cart(request, cart_code=None):
    try:
        # Get the most recent cart for the user
        cart = Cart.objects.filter(user=request.user).order_by('-created_at').first()
        
        if not cart:
            return Response(
                {"detail": "No cart found. Create one first."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    except Exception as e:
        print(f"Error in get_cart: {str(e)}")  # Debugging
        return Response(
            {"detail": "An error occurred while fetching the cart."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_cart(request):
    try:
        print("Creating cart for user: {}".format(request.user))  # Debugging
        cart = Cart.objects.create(user=request.user)
        print("Cart created: {}".format(cart))  # Debugging
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        print("Error in create_cart: {}".format(str(e)))  # Debugging
        return Response(
            {"detail": "Failed to create cart: {}".format(str(e))},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def get_cart_stat(request):
    cart_code = request.query_params.get("cart_code")
    cart = get_object_or_404(Cart, cart_code=cart_code)

    serializer = SimpleCartSerializer(cart)
    return Response(serializer.data)

@api_view(['GET'])
def product_in_cart(request):
    cart_code = request.query_params.get("cart_code")
    product_id = request.query_params.get("product_id")
    
    cart = get_object_or_404(Cart, cart_code=cart_code)
    product = get_object_or_404(Product, id=product_id)
    
    product_exists_in_cart = CartItem.objects.filter(cart=cart, product=product).exists()

    return Response({'product_in_cart': product_exists_in_cart})

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Simple user registration endpoint"""
    data = request.data.copy()
    
    # Handle the typo in confirmPassword
    if 'comfirmPassword' in data:
        data['confirm_password'] = data.pop('comfirmPassword')
    
    # Handle role mapping
    if data.get('role') == 'cutomer':  # Fix typo
        data['role'] = 'customer'
    
    # Create user directly instead of calling create_user
    user_serializer = UserSerializer(data=data)
    if user_serializer.is_valid():
        user = user_serializer.save()
        
        # Generate auth token for the user
        from rest_framework.authtoken.models import Token
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'user_id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.user_type,        # Add this line for frontend compatibility
            'address': [],
            'message': 'User created successfully.'
        }, status=status.HTTP_201_CREATED)
    
    return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([])  # Disable token authentication
@permission_classes([AllowAny])
def login_user(request):
    """Custom login endpoint that returns only essential user info"""
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response({
            'error': 'Email and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    from django.contrib.auth import authenticate
    user = authenticate(request, username=email, password=password)
    
    if user is not None:
        return Response({
            'email': user.email,
            'full_name': user.full_name or '',
            'role': user.user_type
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)

     
@api_view(['GET'])
def home(request):
    if request.user.is_authenticated:
        # Use full_name in the welcome message
        display_name = request.user.full_name or request.user.email
        return Response({
            'message': f'Welcome, {display_name}!',
            'is_authenticated': True,
            'user': {
                'email': request.user.email,
                'full_name': request.user.full_name or '',
                'user_type': request.user.user_type,
            }
        }, status=status.HTTP_200_OK)
    return Response({
        'message': 'Welcome! Please log in.',
        'is_authenticated': False
    }, status=status.HTTP_200_OK)


# Track Order
@api_view(['GET'])
@permission_classes([AllowAny])
def track_order(request):
    """Track order by email or order ID"""
    email = request.query_params.get('email')
    order_id = request.query_params.get('order_id')
    
    if email:
        orders = Order.objects.filter(customer_email=email).order_by('-created_at')
    elif order_id:
        orders = Order.objects.filter(paystack_checkout_id__icontains=order_id)
    else:
        return Response(
            {"error": "Please provide email or order_id parameter"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not orders.exists():
        return Response(
            {"error": "No orders found"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)

# Notifications
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def notifications(request):
    """Get user notifications or create new notification"""
    if request.method == 'POST':
        # Create notification (admin only)
        if request.user.user_type != 'admin':
            return Response(
                {"error": "Only admins can create notifications"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = NotificationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Get user notifications
    notifications = Notification.objects.filter(user=request.user)
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return Response({"status": "marked as read"})
    except Notification.DoesNotExist:
        return Response(
            {"error": "Notification not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )

# Contact Us
@api_view(['POST'])
@permission_classes([AllowAny])
def contact_us(request):
    """Submit contact form"""
    serializer = ContactMessageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {"message": "Contact form submitted successfully"}, 
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def contact_messages(request):
    """Get all contact messages (admin only)"""
    if request.user.user_type != 'admin':
        return Response(
            {"error": "Only admins can view contact messages"}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    messages = ContactMessage.objects.all()
    serializer = ContactMessageSerializer(messages, many=True)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def resolve_contact_message(request, message_id):
    """Mark contact message as resolved (admin only)"""
    if request.user.user_type != 'admin':
        return Response(
            {"error": "Only admins can resolve contact messages"}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        message = ContactMessage.objects.get(id=message_id)
        message.is_resolved = True
        message.save()
        return Response({"status": "marked as resolved"})
    except ContactMessage.DoesNotExist:
        return Response(
            {"error": "Message not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )

# Help Center
@api_view(['GET'])
@permission_classes([AllowAny])
def help_center_articles(request):
    """Get all help center articles"""
    category = request.query_params.get('category')
    
    if category:
        articles = HelpCenterArticle.objects.filter(
            category=category, 
            is_published=True
        )
    else:
        articles = HelpCenterArticle.objects.filter(is_published=True)
    
    serializer = HelpCenterArticleSerializer(articles, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def help_center_article_detail(request, slug):
    """Get specific help center article"""
    try:
        article = HelpCenterArticle.objects.get(slug=slug, is_published=True)
        serializer = HelpCenterArticleSerializer(article)
        return Response(serializer.data)
    except HelpCenterArticle.DoesNotExist:
        return Response(
            {"error": "Article not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def manage_help_center(request, article_id=None):
    """Manage help center articles (admin only)"""
    if request.user.user_type != 'admin':
        return Response(
            {"error": "Only admins can manage help center articles"}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'POST':
        serializer = HelpCenterArticleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'PUT':
        try:
            article = HelpCenterArticle.objects.get(id=article_id)
            serializer = HelpCenterArticleSerializer(article, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except HelpCenterArticle.DoesNotExist:
            return Response(
                {"error": "Article not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    elif request.method == 'DELETE':
        try:
            article = HelpCenterArticle.objects.get(id=article_id)
            article.delete()
            return Response({"status": "article deleted"})
        except HelpCenterArticle.DoesNotExist:
            return Response(
                {"error": "Article not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )