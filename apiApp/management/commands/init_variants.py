# management/commands/init_variants.py
from django.core.management.base import BaseCommand
from apiApp.models import Product, ProductVariant

class Command(BaseCommand):
    help = 'Initialize variants for existing products'

    def handle(self, *args, **options):
        for product in Product.objects.all():
            # Create a default variant if none exists
            if not product.variants.exists():
                variant = ProductVariant.objects.create(
                    product=product,
                    color='default',
                    size='M',
                    quantity=getattr(product, 'quantity', 0)
                )
                self.stdout.write(self.style.SUCCESS(f'Created variant {variant}'))
            
            # Update product's colors and sizes from variants
            product.update_variant_attributes()
        
        self.stdout.write(self.style.SUCCESS('Successfully initialized variants'))