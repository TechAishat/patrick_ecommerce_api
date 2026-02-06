# apiApp/management/commands/add_featured_categories.py
from django.core.management.base import BaseCommand
from apiApp.models import Category

class Command(BaseCommand):
    help = 'Adds main categories and their subcategories'

    def handle(self, *args, **options):
        # Main categories
        main_categories = [
            {
                'name': 'New Arrival',
                'is_featured': True,
                'display_order': 1
            },
            {
                'name': 'Exclusive',
                'is_featured': True,
                'display_order': 2
            },
            {
                'name': 'Cavanni Wardrobe',
                'is_featured': True,
                'display_order': 3
            },
            {
                'name': 'Haute Couture',
                'is_featured': True,
                'display_order': 4
            }
        ]

        # Subcategories for both Cavanni Wardrobe and Haute Couture
        subcategories = [
            'Pants',
            'Tops',
            'Pant & Tops',
            'JumpSuit',
            'Dress'
        ]

        # Create or get main categories
        for cat_data in main_categories:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                parent=None,  # Ensure it's a main category
                defaults={
                    'is_featured': cat_data['is_featured'],
                    'display_order': cat_data['display_order']
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✅ Created category: {cat_data["name"]}'))
            else:
                self.stdout.write(f'ℹ️  Category exists: {cat_data["name"]}')

            # Add subcategories to Cavanni Wardrobe and Haute Couture
            if category.name in ['Cavanni Wardrobe', 'Haute Couture']:
                for sub_name in subcategories:
                    sub, sub_created = Category.objects.get_or_create(
                        name=sub_name,
                        parent=category,
                        defaults={
                            'is_featured': True,
                            'display_order': subcategories.index(sub_name) + 1
                        }
                    )
                    if sub_created:
                        self.stdout.write(self.style.SUCCESS(f'   └── Created subcategory: {sub_name}'))
                    else:
                        self.stdout.write(f'   ℹ️  Subcategory exists: {sub_name}')

        self.stdout.write(self.style.SUCCESS('\n✅ All categories and subcategories have been processed!'))