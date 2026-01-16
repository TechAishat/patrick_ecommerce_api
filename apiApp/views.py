import json
import uuid
import hmac
import hashlib
import requests
import logging
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from .models import Cart, CartItem, Category, CustomerAddress, Order, OrderItem, Product, Review, Wishlist
from .serializers import CartItemSerializer, CartSerializer, CategoryDetailSerializer, CategoryListSerializer, CustomerAddressSerializer, OrderSerializer, ProductListSerializer, ProductDetailSerializer, ReviewSerializer, SimpleCartSerializer, UserSerializer, WishlistSerializer
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
def add_to_cart(request):
    cart_code = request.data.get("cart_code")
    product_id = request.data.get("product_id")

    cart, created = Cart.objects.get_or_create(cart_code=cart_code)
    product = get_object_or_404(Product, id=product_id)

    cartitem, created = CartItem.objects.get_or_create(product=product, cart=cart)
    cartitem.quantity = 1 
    cartitem.save() 

    serializer = CartSerializer(cart)
    return Response(serializer.data)

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
    'callback_url': 'https://electrochemical-thoughtlessly-bruce.ngrok-free.dev/api/webhook/',
    'success_url': 'https://electrochemical-thoughtlessly-bruce.ngrok-free.dev/payment/success/',
    'cancel_url': 'https://electrochemical-thoughtlessly-bruce.ngrok-free.dev/payment/failed/',
}

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

    reset_link = f"https://electrochemical-thoughtlessly-bruce.ngrok-free.dev//{uid}/{token}/"

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
def get_cart(request, cart_code):
    cart = get_object_or_404(Cart, cart_code=cart_code)
    
    serializer = CartSerializer(cart)
    return Response(serializer.data, status=status.HTTP_200_OK)

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

     
from rest_framework import status
@api_view(['GET'])
def home(request):
    if request.user.is_authenticated:
        return Response({
            'message': f'Welcome, {request.user.email}!',
            'is_authenticated': True,
            'user': {
                'email': request.user.email,
                'first_name': getattr(request.user, 'first_name', ''),
                'last_name': getattr(request.user, 'last_name', ''),
            }
        }, status=status.HTTP_200_OK)
    return Response({
        'message': 'Welcome! Please log in.',
        'is_authenticated': False
    }, status=status.HTTP_200_OK)