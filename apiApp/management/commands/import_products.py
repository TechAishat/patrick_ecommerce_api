# apiApp/management/commands/import_products.py
import json
import os
import requests
from io import BytesIO
from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.core.files import File
from django.core.files.base import ContentFile
from django.utils.text import slugify
from django.conf import settings

from apiApp.models import Product, Category, ProductImage, Inventory, InventoryVariant


class Command(BaseCommand):
    help = 'Import sample products from JSON data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Path to a JSON file containing product data'
        )
        parser.add_argument(
            '--url',
            type=str,
            help='URL to a JSON file containing product data'
        )

    def handle(self, *args, **options):
        product_data = self._get_product_data(options)
        if not product_data:
            self.stderr.write(self.style.ERROR('No product data provided. Use --file or --url option.'))
            return

        self._import_product(product_data)

    def _get_product_data(self, options):
        """Get product data from file, URL, or use sample data."""
        if options['file']:
            return self._load_from_file(options['file'])
        elif options['url']:
            return self._fetch_from_url(options['url'])
        else:
            # Use sample data if no source provided
            return self._get_sample_data()

    def _load_from_file(self, file_path):
        """Load product data from a JSON file."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error reading file: {str(e)}'))
            return None

    def _fetch_from_url(self, url):
        """Fetch product data from a URL."""
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error fetching from URL: {str(e)}'))
            return None

    def _get_sample_data(self):
        """Return sample product data."""
        return {
            "id": "21",
            "name": "Essential Crewneck Tee",
            "slug": "nike-essential-crewneck-tee",
            "isExclusive": False,
            "gender": "unisex",
            "price": 35,
            "oldPrice": 45,
            "discount": 22,
            "images": [
                "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=1000",
                "https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=1000",
                "https://images.unsplash.com/photo-1598033129183-c4f50c736f10?w=1000",
                "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?w=1000"
            ],
            "categories": ["tops", "new-arrival"],
            "colors": ["white", "black", "grey"],
            "sizes": ["S", "M", "L", "XL"],
            "rating": 4.5,
            "reviews": 1240,
            "inventory": {
                "status": "in_stock",
                "skuBase": "NK-TEE-021",
                "variants": [
                    {
                        "color": "white",
                        "size": "M",
                        "quantity": 100,
                        "sku": "NK-TEE-021-WHT-M"
                    }
                ]
            },
            "description": "A soft, everyday staple made from sustainable cotton.",
            "createdAt": "2026-01-02T09:00:00.000Z"
        }

    def _import_product(self, product_data):
        """Import a single product from product data."""
        self.stdout.write(self.style.SUCCESS(f"Starting import of {product_data['name']}..."))

        # Get or create categories
        categories = []
        for cat_name in product_data['categories']:
            category, created = Category.objects.get_or_create(
                name=cat_name.title(),
                defaults={'slug': slugify(cat_name)}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created category: {category.name}"))
            categories.append(category)

        # Create or update product
        product, created = Product.objects.update_or_create(
            slug=product_data['slug'],
            defaults={
                'name': product_data['name'],
                'description': product_data['description'],
                'price': product_data['price'],
                'old_price': product_data.get('oldPrice'),
                'discount': product_data.get('discount', 0),
                'gender': product_data['gender'],
                'colors': product_data['colors'],
                'sizes': product_data['sizes'],
                'rating': product_data['rating'],
                'review_count': product_data['reviews'],
                'is_featured': True,
                'is_exclusive': product_data.get('isExclusive', False),
                'status': 'published'
            }
        )
        
        # Set categories
        product.category.set(categories)
        self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} product: {product.name}"))

        # Create or update inventory
        inventory, _ = Inventory.objects.update_or_create(
            product=product,
            defaults={
                'status': product_data['inventory']['status'],
                'sku_base': product_data['inventory']['skuBase']
            }
        )

        # Create or update inventory variants
        for variant_data in product_data['inventory']['variants']:
            variant, created = InventoryVariant.objects.update_or_create(
                inventory=inventory,
                color=variant_data['color'],
                size=variant_data['size'],
                defaults={
                    'quantity': variant_data['quantity'],
                    # Removed 'sku' field from here
                }
            )
            action = 'Created' if created else 'Updated'
            self.stdout.write(f"  {action} variant: {variant.color} {variant.size}")



        # Download and save images
        for i, image_url in enumerate(product_data['images']):
            try:
                response = requests.get(image_url)
                response.raise_for_status()
                
                # Get the file extension from the URL
                parsed_url = urlparse(image_url)
                file_ext = os.path.splitext(parsed_url.path)[1] or '.jpg'
                image_name = f"{product.slug}-{i}{file_ext}"
                
                # Create a ContentFile from the response content
                image_content = ContentFile(response.content)
                
                # Create the product image
                product_image = ProductImage(
                    product=product,
                    is_primary=(i == 0),
                    alt_text=f"{product.name} - {i+1}"
                )
                
                # Save the image file
                product_image.image.save(
                    image_name,
                    image_content,
                    save=False
                )
                product_image.save()
                
                self.stdout.write(f"  Added image: {image_name}")
                
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error downloading image {image_url}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"Successfully imported {product.name}"))

    def _get_image_extension(self, url):
        """Extract file extension from URL."""
        try:
            return os.path.splitext(urlparse(url).path)[1] or '.jpg'
        except:
            return '.jpg'