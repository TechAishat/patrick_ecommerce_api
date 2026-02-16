from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('apiApp', '0001_initial'),
    ]

    operations = [
        # First, remove the unique constraint
        migrations.RunSQL(
            "CREATE TABLE IF NOT EXISTS new_apiApp_productvariant AS SELECT * FROM apiApp_productvariant;",
            "DROP TABLE IF EXISTS new_apiApp_productvariant;"
        ),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS apiApp_productvariant;",
            "CREATE TABLE IF NOT EXISTS apiApp_productvariant (id INTEGER PRIMARY KEY AUTOINCREMENT, ...);"  # Add other columns as needed
        ),
        migrations.RunSQL(
            "INSERT INTO apiApp_productvariant SELECT * FROM new_apiApp_productvariant;",
            "INSERT INTO new_apiApp_productvariant SELECT * FROM apiApp_productvariant;"
        ),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS new_apiApp_productvariant;",
            "CREATE TABLE IF NOT EXISTS new_apiApp_productvariant AS SELECT * FROM apiApp_productvariant;"
        ),
        # Then, modify the field to be nullable
        migrations.AlterField(
            model_name='productvariant',
            name='sku',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
    ]