import random
from django.core.management.base import BaseCommand
from apiApp.models import Product, ProductVariant, ProductImage

class Command(BaseCommand):
    help = 'Seed product variants for testing'

    def handle(self, *args, **options):
        colors = ['Red', 'Blue', 'Black', 'White', 'Green', 'Yellow']
        sizes = ['S', 'M', 'L', 'XL', 'XXL']
        
        # Get all products
        products = Product.objects.all()
        
        for product in products:
            self.stdout.write(f"Processing product: {product.name}")
            
            # Skip if product already has variants
            if product.variants.exists():
                self.stdout.write(f"  - Product already has variants, skipping...")
                continue
            
            # Get up to 3 random colors for this product
            product_colors = random.sample(colors, k=min(3, len(colors)))
            product.colors = product_colors
            product.sizes = sizes[:3]  # Use first 3 sizes
            product.save()
            
            # Create variants
            for color in product_colors:
                for size in product.sizes:
                    # Create variant
                    sku = f"{product.sku_base or 'SKU'}-{color[:3].upper()}-{size}"
                    variant = ProductVariant.objects.create(
                        product=product,
                        sku=sku,
                        color=color,
                        size=size,
                        quantity=random.randint(5, 100),
                    )
                    
                    # Add sample images (2 per variant)
                    for i in range(1, 3):
                        ProductImage.objects.create(
                            product=product,
                            variant=variant,
                            image=f"product_images/sample-{i}.jpg",
                            alt_text=f"{product.name} - {color} - {size} - Image {i}",
                            is_primary=(i == 1)
                        )
                    
                    self.stdout.write(f"  - Created variant: {color} / {size} (Qty: {variant.quantity})")
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded product variants!'))