from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg, Count
from django.contrib.auth import get_user_model
from apiApp.models import ProductRating, Review, Product

User = get_user_model()

@receiver(post_save, sender=User)
def update_user_profile(sender, instance, created, **kwargs):
    if created:
        # Any additional logic when a user is created
        pass

def update_product_rating_stats(product):
    """
    Helper function to update rating stats for a product
    """
    reviews = product.reviews.all()
    total_reviews = reviews.count()
    
    # Calculate average rating
    rating_avg = reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0.0
    
    # Calculate rating breakdown
    breakdown = reviews.values('rating').annotate(count=Count('id'))
    breakdown_dict = {str(rating): 0 for rating in range(1, 6)}
    for item in breakdown:
        breakdown_dict[str(item['rating'])] = item['count']
    
    # Update or create ProductRating
    product_rating, created = ProductRating.objects.update_or_create(
        product=product,
        defaults={
            'average_rating': round(rating_avg, 1),
            'total_reviews': total_reviews,
            'rating_breakdown': breakdown_dict
        }
    )
    
    # Update the product's rating fields
    product.rating_field = rating_avg
    product.review_count = total_reviews
    product.save(update_fields=['rating_field', 'review_count'])
    
    return product_rating

@receiver([post_save, post_delete], sender=Review)
def handle_review_update(sender, instance, **kwargs):
    """
    Handle both save and delete operations for reviews
    """
    product = instance.product
    update_product_rating_stats(product)

@receiver(post_save, sender=Product)
def create_product_rating(sender, instance, created, **kwargs):
    """
    Create a ProductRating entry when a new product is created
    """
    if created:
        ProductRating.objects.create(
            product=instance,
            average_rating=0.0,
            total_reviews=0,
            rating_breakdown={'1': 0, '2': 0, '3': 0, '4': 0, '5': 0}
        )