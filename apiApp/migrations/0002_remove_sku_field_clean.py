from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('apiApp', '0001_initial'),  # Adjust this to your last working migration
    ]

    operations = [
        migrations.AlterField(
            model_name='productvariant',
            name='sku',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.RunSQL(
            "ALTER TABLE apiApp_productvariant ALTER COLUMN sku DROP NOT NULL;",
            reverse_sql="ALTER TABLE apiApp_productvariant ALTER COLUMN sku SET NOT NULL;"
        )
    ]