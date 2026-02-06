# apiApp/management/commands/assign_products_to_subcategories.py
from django.core.management.base import BaseCommand
from apiApp.models import Product, Category

class Command(BaseCommand):
    help = 'Assign products to appropriate subcategories under Cavanni Wardrobe'

    def handle(self, *args, **options):
        # Get the Cavanni Wardrobe category
        try:
            cavanni = Category.objects.get(name='Cavanni Wardrobe')
        except Category.DoesNotExist:
            self.stdout.write(self.style.ERROR('Cavanni Wardrobe category not found!'))
            return

        # Get all subcategories under Cavanni Wardrobe
        subcategories = {
            'pants': Category.objects.filter(parent=cavanni, name__iexact='Pants').first(),
            'tops': Category.objects.filter(parent=cavanni, name__iexact='Tops').first(),
            'pant & tops': Category.objects.filter(parent=cavanni, name__iexact='Pant & Tops').first(),
            'jumpsuit': Category.objects.filter(parent=cavanni, name__iexact='JumpSuit').first(),
            'dress': Category.objects.filter(parent=cavanni, name__iexact='Dress').first(),
        }

        # Get all products that are in Cavanni Wardrobe
        products = Product.objects.filter(category=cavanni)
        self.stdout.write(f"Found {products.count()} products in Cavanni Wardrobe")

        for product in products:
            name_lower = product.name.lower()
            assigned = False

            # Check for subcategory matches
            if any(word in name_lower for word in ['dress', 'gown', 'frock']):
                product.category.add(subcategories['dress'])
                assigned = True
            elif any(word in name_lower for word in ['jumpsuit', 'jump suit', 'romper']):
                product.category.add(subcategories['jumpsuit'])
                assigned = True
            elif 'pant' in name_lower and 'top' in name_lower:
                product.category.add(subcategories['pant & tops'])
                assigned = True
            elif any(word in name_lower for word in ['pant', 'trouser', 'jean']):
                product.category.add(subcategories['pants'])
                assigned = True
            elif any(word in name_lower for word in ['top', 'tee', 'shirt', 'blouse', 't-shirt', 't shirt']):
                product.category.add(subcategories['tops'])
                assigned = True

            if assigned:
                self.stdout.write(self.style.SUCCESS(f"Assigned '{product.name}' to a subcategory"))
            else:
                self.stdout.write(self.style.WARNING(f"Could not assign '{product.name}' to a subcategory - assigning to Tops by default"))
                product.category.add(subcategories['tops'])

        self.stdout.write(self.style.SUCCESS('Finished assigning products to subcategories!'))
        