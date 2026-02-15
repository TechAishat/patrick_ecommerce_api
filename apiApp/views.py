from rest_framework.views import exception_handler
from rest_framework.exceptions import PermissionDenied
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework import status
from django.utils import timezone
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
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from django.db.models import Avg, Count
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import Http404
from .paystack import Paystack  # Add this import at the top with other imports
from .models import Cart, CartItem, Category, CustomerAddress, Order, OrderItem, Product, Review, Wishlist, Notification, ContactMessage, HelpCenterArticle, ProductVariant
from .serializers import CartItemSerializer, CartSerializer, CategoryDetailSerializer, CategoryListSerializer, CustomerAddressSerializer, OrderSerializer, ProductListSerializer, ProductDetailSerializer, ReviewSerializer, SimpleCartSerializer, UserSerializer, WishlistSerializer,NotificationSerializer, ContactMessageSerializer, HelpCenterArticleSerializer, CartStatSerializer
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.urls import reverse
import time



def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that adds special handling for PermissionDenied
    exceptions related to exclusive products.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    # Handle PermissionDenied for exclusive products
    if isinstance(exc, PermissionDenied) and hasattr(exc, 'detail') and isinstance(exc.detail, dict):
        if exc.detail.get('code') == 'authentication_required':
            return Response({
                'error': 'Authentication required',
                'requires_login': True,
                'detail': exc.detail.get('detail', 'Authentication required')
            }, status=status.HTTP_403_FORBIDDEN)
    
    return response


logger = logging.getLogger(__name__)

User = get_user_model()

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])  # Changed from IsAuthenticated to AllowAny for testing
def product_list(request):
    if request.method == 'POST':
        if not request.user.is_staff:
            return Response(
                {"error": "You don't have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = ProductDetailSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            product = serializer.save()
            return Response(
                ProductDetailSerializer(product, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
    # GET request handling
    try:
        # Start with base queryset
        products = Product.objects.prefetch_related(
            'variants',
            'images',
            'category',
            'variants__images'
        ).filter(status='published')
        
        # Apply filters
        if category_slug := request.query_params.get('category'):
            products = products.filter(category__slug=category_slug)
        if featured := request.query_params.get('featured'):
            products = products.filter(is_featured=featured.lower() == 'true')
        if exclusive := request.query_params.get('exclusive'):
            products = products.filter(is_exclusive=exclusive.lower() == 'true')
        if gender := request.query_params.get('gender'):
            products = products.filter(gender__iexact=gender)
 
        # Ordering
        products = products.order_by('-is_featured', '-created_at')
        
        # Remove pagination and return all results
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)
 
    except Exception as e:
        logger.error(f"Error in product_list: {str(e)}")
        return Response(
            {"error": "An error occurred while processing your request."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
               
    
    # Get query parameters
    category_slug = request.query_params.get('category')
    featured = request.query_params.get('featured')
    is_exclusive = request.query_params.get('exclusive')
    gender = request.query_params.get('gender')
    
    # Start with base queryset
    products = Product.objects.filter(status='published')
    
    # Apply filters
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    if featured and featured.lower() == 'true':
        products = products.filter(is_featured=True)
        
    if is_exclusive and is_exclusive.lower() == 'true':
        products = products.filter(is_exclusive=True)
        
    if gender and gender.lower() in dict(Product.GENDER_CHOICES):
        products = products.filter(gender__iexact=gender.lower())
    
    # Order by featured and created date
    products = products.order_by('-is_featured', '-created_at')
    
    # Pagination
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 20)
    paginator = Paginator(products, page_size)
    
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)
    
    serializer = ProductListSerializer(products_page, many=True, context={'request': request})
    
    return Response({
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': products_page.number,
        'results': serializer.data
    })
    

class ProductDetailView(generics.RetrieveAPIView):
    """
    GET: Get product details
    - Public access for non-exclusive products
    - Requires authentication for exclusive products
    """
    permission_classes = [AllowAny]
    serializer_class = ProductDetailSerializer
    lookup_field = 'slug'
    queryset = Product.objects.prefetch_related(
        'variants',
        'images',
        'variants__images',
        'reviews'
    ).all()
 
    def get_serializer_context(self):
        return {'request': self.request}
 
    def get_object(self):
        slug = self.kwargs.get('slug')
        try:
            product = get_object_or_404(
                self.get_queryset(),
                slug=slug,
                status='published'
            )
            
            # Check if product is exclusive and user is not authenticated
            if product.is_exclusive and not self.request.user.is_authenticated:
                raise PermissionDenied({
                    "detail": "Authentication required to view this product",
                    "code": "authentication_required",
                    "requires_login": True
                })
                
            return product
            
        except Product.DoesNotExist:
            logger.error(f"Product not found: {slug}")
            raise Http404("Product not found")
        except Exception as e:
            logger.error(f"Error retrieving product {slug}: {str(e)}")
            raise


@api_view(['GET'])
@permission_classes([AllowAny])
def category_list(request):
    # Get only parent categories (categories without a parent)
    categories = Category.objects.filter(parent__isnull=True).order_by('display_order', 'name')
    serializer = CategoryListSerializer(categories, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def category_detail(request, slug):
    category = get_object_or_404(
        Category.objects.prefetch_related('children', 'products'),
        slug=slug
    )
    
    # Get all descendant category IDs including the current category
    def get_descendant_ids(category):
        ids = [category.id]
        for child in category.children.all():
            ids.extend(get_descendant_ids(child))
        return ids
    
    category_ids = get_descendant_ids(category)
    
    # Get products from this category and all subcategories
    products = Product.objects.filter(
        category__id__in=category_ids,
        status='published'
    ).order_by('-is_featured', '-created_at')
    
    # Pagination
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 20)
    paginator = Paginator(products, page_size)
    
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)
    
    category_serializer = CategoryDetailSerializer(category, context={'request': request})
    product_serializer = ProductListSerializer(products_page, many=True, context={'request': request})
    
    return Response({
        'category': category_serializer.data,
        'products': {
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': products_page.number,
            'results': product_serializer.data
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def add_to_cart(request):
    try:
        # Get or create a cart code in session
        if 'cart_code' not in request.session:
            request.session['cart_code'] = str(uuid.uuid4())
        cart_code = request.session['cart_code']

        # Get request data
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        color = request.data.get('color')
        size = request.data.get('size')
        
        # Debug: Log the incoming request data
        logger.info(f"Add to cart request - Product ID: {product_id}, Quantity: {quantity}, Color: {color}, Size: {size}")

        # Get or create cart using cart_code
        cart, created = Cart.objects.get_or_create(
            cart_code=cart_code,
            defaults={'cart_code': cart_code}
        )
        
        # Get the product with categories prefetched
        try:
            product = Product.objects.prefetch_related('category').get(
                id=product_id,
                status='published'
            )
            logger.info(f"Product found: {product.name}")
        except Product.DoesNotExist:
            logger.error(f"Product not found or not published: {product_id}")
            return Response(
                {"success": False, "message": "Product not found or not published."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Find the variant
        variant = None
        if color or size:
            variant_query = ProductVariant.objects.filter(product=product)
            if color:
                variant_query = variant_query.filter(color=color)
            if size:
                variant_query = variant_query.filter(size=size)
            
            variant = variant_query.first()
            if not variant:
                logger.error(f"Variant not found for product {product_id} with color={color}, size={size}")
                return Response(
                    {"success": False, "message": "Variant not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
            logger.info(f"Variant found: {variant.id}")

        # Create or update cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=variant,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()
            logger.info(f"Updated cart item quantity to {cart_item.quantity}")

        # Debug: Log cart items after update
        cart_items = CartItem.objects.filter(cart=cart).select_related('product', 'variant').prefetch_related('product__category')
        logger.info(f"Cart items after update: {cart_items.count()} items")
        for item in cart_items:
            logger.info(f"Cart item: {item.product.name}, Qty: {item.quantity}, Variant: {item.variant}")

        # Prepare response
        items = []
        total_quantity = 0
        
        for item in cart_items:
            variant_color = item.variant.color if item.variant else None
            variant_size = item.variant.size if item.variant else None
            
            # Get category and subcategory
            category_name = None
            subcategory_name = ""
            
            if hasattr(item.product, 'category') and item.product.category.exists():
                categories = item.product.category.all().order_by('name')
                if categories:
                    main_category = categories[0]
                    category_name = main_category.name
                    if len(categories) > 1:
                        subcategory_name = categories[1].name
                    elif hasattr(main_category, 'parent') and main_category.parent:
                        category_name = main_category.parent.name
                        subcategory_name = main_category.name
            
            items.append({
                "product_name": item.product.name,
                "category": category_name,
                "subcategory": subcategory_name,
                "quantity": item.quantity,
                "price": str(item.product.price),
                "total": float(item.product.price * item.quantity),
                "color": variant_color,
                "size": variant_size
            })
            total_quantity += item.quantity

        cart_data = {
            "id": cart.id,
            "item_count": cart_items.count(),
            "total_quantity": total_quantity,
            "items": items
        }
        
        return Response({
            "success": True,
            "message": "Item added to cart successfully",
            "cart": cart_data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error in add_to_cart: {str(e)}", exc_info=True)
        return Response(
            {"success": False, "message": f"An error occurred: {str(e)}"},
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
@permission_classes([IsAuthenticated])  # Require authentication
def add_review(request):
    try:
        product_id = request.data.get("product_id")
        rating = request.data.get("rating")
        review_text = request.data.get("review")

        # Validate required fields
        if not all([product_id, rating, review_text]):
            return Response(
                {"error": "product_id, rating, and review are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the product
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if review already exists for this user and product
        if Review.objects.filter(product=product, user=request.user).exists():
            return Response(
                {"error": "You have already reviewed this product"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create the review
        review = Review.objects.create(
            product=product,
            user=request.user,  # Use the authenticated user
            rating=rating,
            review=review_text
        )
        
        # Serialize and return the response
        serializer = ReviewSerializer(review)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

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
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    """Create a Paystack checkout session using the authenticated user's cart."""
    try:
        # Get the user's most recent cart
        try:
            cart = Cart.objects.filter(user=request.user).latest('created_at')
            
            # Check if this cart is already associated with an order
            cart_product_ids = cart.cartitems.values_list('product_id', flat=True)
            if OrderItem.objects.filter(product_id__in=cart_product_ids).exists():
                return Response(
                    {"error": "This cart has already been processed. Please add items to a new cart."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Cart.DoesNotExist:
            return Response(
                {"error": "No active cart found. Please add items to your cart first."},
                status=status.HTTP_400_BAD_REQUEST
            )
 
        if cart.cartitems.count() == 0:
            return Response(
                {"error": "Your cart is empty. Please add items before checking out."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate total amount in kobo
        total_amount = int(sum(
            item.quantity * float(item.product.price) * 100  # Convert to kobo
            for item in cart.cartitems.all()
        ))

        # Prepare Paystack payload
        payload = {
            'email': request.user.email,
            'amount': total_amount,
            'reference': f"order_{cart.id}_{int(time.time())}",
            'callback_url': f"{settings.FRONTEND_URL}/payment/verify/",  # Your frontend callback URL
            'metadata': {
                'cart_id': str(cart.id),
                'user_id': str(request.user.id),
                'cart_code': str(cart.cart_code)  # Add cart_code to metadata
            }
        }

        # Initialize Paystack payment
        paystack = Paystack()
        response = paystack.initialize_transaction(**payload)

        if not response.get('status'):
            logger.error(f"Paystack error: {response.get('message', 'Unknown error')}")
            return Response(
                {"error": "Failed to initialize payment. Please try again."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Return the authorization URL to the frontend
        return Response({
            "authorization_url": response['data']['authorization_url'],
            "reference": payload['reference'],
            "amount": total_amount,
            "email": request.user.email
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Checkout error: {str(e)}", exc_info=True)
        return Response(
            {"error": "An error occurred while processing your payment. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        
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

def fulfill_checkout(session_data, cart_code):
    """Fulfill the order after successful payment."""
    try:
        # Check if order with this reference already exists
        reference = session_data.get('reference')
        if not reference:
            logger.error("No reference found in session")
            return False

        if Order.objects.filter(paystack_checkout_id=reference).exists():
            logger.info(f"Order with reference {reference} already exists")
            return True

        # Get the cart
        try:
            cart = Cart.objects.get(cart_code=cart_code)
        except Cart.DoesNotExist:
            logger.error(f"Cart with code {cart_code} not found")
            return False

        # Get customer email from session data
        customer_email = session_data.get('customer', {}).get('email', '') or session_data.get('customer_email', '')
        
        # Create order
        order = Order.objects.create(
            paystack_checkout_id=reference,
            amount=float(session_data.get('amount', 0)) / 100,  # Convert from kobo to Naira
            currency=session_data.get('currency', 'NGN'),
            customer_email=customer_email,
            status='Paid'
        )
        
        # Add cart items to order
        for item in cart.cartitems.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price  # Store the price at time of purchase
            )
            
        # Clear the cart
        cart.cartitems.all().delete()
        
        logger.info(f"Order {order.id} created successfully for cart {cart_code}")
        return True
        
    except Exception as e:
        logger.error(f"Error fulfilling checkout: {str(e)}", exc_info=True)
        return False


@api_view(['GET'])
@permission_classes([AllowAny])  # Add this back if you want to allow unauthenticated access
def verify_payment(request):
    reference = request.query_params.get('reference')
    if not reference:
        return Response({'error': 'Reference is required'}, status=400)
    
    paystack = Paystack()
    response = paystack.verify_transaction(reference)
    
    if response.get('status') is False:
        return Response(response, status=400)
    
    data = response.get('data', {})
    status = data.get('status')
    metadata = data.get('metadata', {})
    cart_code = metadata.get('cart_code')
    
    if status == 'success':
        # Handle successful payment
        if cart_code and fulfill_checkout(data, cart_code):
            return Response({
                'status': 'success',
                'message': 'Payment verified and order created successfully',
                'data': {
                    'reference': reference,
                    'amount': data.get('amount', 0) / 100,  # Convert from kobo to Naira
                    'currency': data.get('currency', 'NGN'),
                    'paid_at': data.get('paid_at'),
                    'status': status
                }
            })
        else:
            return Response({
                'status': 'error',
                'message': 'Payment verified but failed to create order',
                'data': data
            }, status=400)
            
    elif status == 'abandoned':
        return Response({
            'status': 'pending',
            'message': 'Payment was not completed. Please try again.',
            'data': data
        }, status=200)
    else:
        return Response({
            'status': 'failed',
            'message': data.get('gateway_response', 'Payment verification failed'),
            'data': data
        }, status=400)


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
    """User registration with email verification"""
    data = request.data.copy()
    
    # Handle the typo in confirmPassword
    if 'comfirmPassword' in data:
        data['confirm_password'] = data.pop('comfirmPassword')
    
    # Handle role mapping
    if data.get('role') == 'cutomer':  # Fix typo
        data['role'] = 'customer'
    
    # Create user but keep them inactive until email is verified
    user_serializer = UserSerializer(data=data)
    if user_serializer.is_valid():
        user = user_serializer.save(
            is_active=False,  # User is inactive until verified
            email_verified=False
        )
        
        # Generate verification token
        user.verification_token = str(uuid.uuid4())
        user.verification_token_created_at = timezone.now()
        user.save()
        
        # Build frontend verification URL with token
        frontend_url = f"http://localhost:5173/verify-email?token={user.verification_token}"
        
        # Send verification email with frontend URL
        send_mail(
            'Verify Your Email - Patrick Cavanni',
            f'Please click the following link to verify your email:\n\n{frontend_url}\n\n'
            'This link will expire in 24 hours.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
            html_message=(
                f'<p>Please click the button below to verify your email:</p>'
                f'<a href="{frontend_url}" style="background-color: #4CAF50; border: none; color: white; '
                f'padding: 15px 32px; text-align: center; text-decoration: none; display: inline-block; '
                f'font-size: 16px; margin: 4px 2px; cursor: pointer; border-radius: 4px;">'
                f'Verify Email</a>'
                f'<p>Or copy and paste this link in your browser:<br>{frontend_url}</p>'
                f'<p>This link will expire in 24 hours.</p>'
            )
        )
        
        return Response({
            'message': 'Registration successful! Please check your email to verify your account.',
            'email': user.email,
            'requires_verification': True
        }, status=status.HTTP_201_CREATED)
    
    return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

 
@api_view(['GET'])
@permission_classes([AllowAny])
def test_email(request):
    send_mail(
        'Test Email from Patrick Cavanni',
        'This is a test email from Django backend.',
        settings.DEFAULT_FROM_EMAIL,  # Use the email from settings
        ['curvemetric122@gmail.com'],  # Your email address
        fail_silently=False,
    )
    return Response({"message": "Test email sent to curvemetric122@gmail.com"})


@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """Custom login endpoint that checks email verification"""
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response({
            'error': 'Email and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    from django.contrib.auth import authenticate
    user = authenticate(request, username=email, password=password)
    
    if user is not None:
        # Check if email is verified
        if not user.email_verified:
            return Response({
                'error': 'Please verify your email before logging in. Check your email for the verification link.',
                'requires_verification': True,
                'email': user.email,
                'can_resend': True
            }, status=status.HTTP_403_FORBIDDEN)
            
        # Check if account is active
        if not user.is_active:
            return Response({
                'error': 'Your account is inactive. Please contact support.',
                'is_active': False
            }, status=status.HTTP_403_FORBIDDEN)
            
        # Generate token and return user data
        from rest_framework.authtoken.models import Token
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'isAuthenticated': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name or '',
                'role': user.user_type
            }
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'error': 'Invalid credentials',
            'isAuthenticated': False
        }, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification_email(request):
    """Resend verification email"""
    email = request.data.get('email')
    if not email:
        return Response(
            {'error': 'Email is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(email=email)
        
        if user.email_verified:
            return Response(
                {'message': 'Email is already verified'}, 
                status=status.HTTP_200_OK
            )
            
        # Generate new token
        user.verification_token = str(uuid.uuid4())
        user.verification_token_created_at = timezone.now()
        user.save()
        
        # Send verification email
        verification_url = request.build_absolute_uri(
            reverse('verify-email', args=[user.verification_token])
        )
        
        send_mail(
            'Verify Your Email - Patrick Cavanni',
            f'Please click the following link to verify your email:\n\n{verification_url}\n\n'
            'This link will expire in 24 hours.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        return Response(
            {'message': 'Verification email sent successfully'}, 
            status=status.HTTP_200_OK
        )
        
    except User.DoesNotExist:
        # Don't reveal if email exists for security reasons
        return Response(
            {'message': 'If an account exists with this email, a verification link has been sent'}, 
            status=status.HTTP_200_OK
        )

 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    try:
        # Get the token from the request
        token = request.auth
        if token:
            # Delete the token
            token.delete()
            return Response(
                {"message": "Successfully logged out."}, 
                status=status.HTTP_200_OK
            )
        return Response(
            {"error": "No authentication token found."},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    user = request.user
    return Response({
        'id': user.id,
        'email': user.email,
        'full_name': user.full_name,
        'role': user.user_type,
        'is_active': user.is_active,
        'date_joined': user.date_joined,
        #'address': user.address,
        #'phone_number': user.phone_number
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def check_user(request, email):
    """Check if a user with the given email exists."""
    User = get_user_model()
    exists = User.objects.filter(email=email).exists()
    return Response({'exists': exists}, status=status.HTTP_200_OK)
     
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

class RatingListCreateView(generics.ListCreateAPIView):
    """
    List all ratings or create a new rating.
    """
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
 
    def get_queryset(self):
        # Return only the current user's ratings
        return Review.objects.filter(user=self.request.user).select_related('product')
 
    def perform_create(self, serializer):
        product_id = self.request.data.get('product')
        variant_id = self.request.data.get('variant')
        
        # Check if user already reviewed this product-variant combination
        existing_review = Review.objects.filter(
            user=self.request.user,
            product_id=product_id,
            variant_id=variant_id if variant_id else None
        ).exists()
        
        if existing_review:
            raise ValidationError("You have already reviewed this product.")
            
        serializer.save(user=self.request.user)
 
class RatingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a rating.
    """
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
 
    def get_queryset(self):
        # Users can only access their own ratings
        return Review.objects.filter(user=self.request.user)
 
@api_view(['GET'])
@permission_classes([AllowAny])
def product_ratings(request, product_id):
    """
    Get all ratings for a specific product.
    """
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response(
            {"error": "Product not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get all published reviews for the product
    reviews = Review.objects.filter(
        product=product,
        is_published=True
    ).select_related('user')
    
    # Calculate rating summary
    rating_summary = reviews.aggregate(
        average_rating=Avg('rating'),
        total_ratings=Count('id'),
        rating_1=Count('id', filter=Q(rating=1)),
        rating_2=Count('id', filter=Q(rating=2)),
        rating_3=Count('id', filter=Q(rating=3)),
        rating_4=Count('id', filter=Q(rating=4)),
        rating_5=Count('id', filter=Q(rating=5))
    )
    
    # Serialize the reviews
    serializer = ReviewSerializer(reviews, many=True)
    
    return Response({
        'product_id': product_id,
        'product_name': product.name,
        'rating_summary': rating_summary,
        'reviews': serializer.data
    })


class VerifyEmailView(APIView):
    """
    Verify user's email using the verification token.
    """
    permission_classes = [AllowAny]
    
    def get(self, request, token):
        try:
            user = User.objects.get(verification_token=token)
            
            # Check if token is expired (24 hours)
            token_age = timezone.now() - user.verification_token_created_at
            if token_age > timezone.timedelta(hours=24):
                return Response(
                    {"error": _("Verification link has expired. Please request a new one.")},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Mark email as verified and activate the account
            user.email_verified = True
            user.is_active = True
            user.verification_token = None
            user.verification_token_created_at = None
            user.save()
            
            return Response(
                {"message": _("Email verified successfully! You can now log in.")},
                status=status.HTTP_200_OK
            )
            
        except User.DoesNotExist:
            return Response(
                {"error": _("Invalid verification link.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error verifying email: {str(e)}")
            return Response(
                {"error": _("An error occurred while verifying your email.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response(
                {"error": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            # Don't reveal if user doesn't exist for security
            return Response(
                {"message": "If an account exists with this email, a password reset link has been sent."},
                status=status.HTTP_200_OK
            )
            
        # Generate password reset token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build reset URL
        # In views.py, update the reset_url in PasswordResetRequestView
        reset_url = request.build_absolute_uri(
            reverse('api:password-reset-confirm', kwargs={
                'uidb64': uid,
                'token': token
            })
        ).replace('/api/password-reset-confirm/', '/api/users/password-reset/confirm/')
        
        # Send email
        subject = "Password Reset Request"
        message = f"""
        You're receiving this email because you requested a password reset for your account.
        
        Please go to the following page and choose a new password:
        {reset_url}
        
        If you didn't request this, please ignore this email.
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        return Response(
            {"message": "Password reset email has been sent if the email exists in our system."},
            status=status.HTTP_200_OK
        )
 
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, uidb64, token):
        # This handles the GET request when user clicks the reset link
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            
            if not default_token_generator.check_token(user, token):
                return Response(
                    {"error": "Invalid or expired reset link"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            return Response({
                "uid": uidb64,
                "token": token,
                "email": user.email
            })
            
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"error": "Invalid reset link"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def post(self, request, uidb64, token):
        # This handles the password reset form submission
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            
            if not default_token_generator.check_token(user, token):
                return Response(
                    {"error": "Invalid or expired reset link"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate password
            password = request.data.get('password')
            if not password:
                return Response(
                    {"error": "Password is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Set new password
            user.set_password(password)
            user.save()
            
            return Response({
                "message": "Password has been reset successfully"
            }, status=status.HTTP_200_OK)
            
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"error": "Invalid reset link"},
                status=status.HTTP_400_BAD_REQUEST
            )

class GoogleAuthURL(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, *args, **kwargs):
        from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
        from allauth.socialaccount.providers.oauth2.client import OAuth2Client
        from urllib.parse import urlencode
        from django.conf import settings

        # Get the client ID and secret from settings
        client_id = settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id']
        client_secret = settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['secret']
        
        # Build the authorization URL
        params = {
            'client_id': client_id,
            'redirect_uri': f"{settings.FRONTEND_URL}/google/callback",
            'scope': 'openid profile email',
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'select_account',
        }
        
        url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        return Response({'authorization_url': url}, status=200)

class GoogleLogin(SocialLoginView):
    permission_classes = [AllowAny]
    adapter_class = GoogleOAuth2Adapter
    callback_url = 'postmessage'
    client_class = OAuth2Client