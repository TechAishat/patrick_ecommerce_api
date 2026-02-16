from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('apiApp', '0002_remove_sku_column'),
    ]

    operations = [
        # This is an empty migration since the field is already removed
    ]