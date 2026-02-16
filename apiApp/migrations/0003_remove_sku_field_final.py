from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('apiApp', '0001_initial'),  # Adjust this to your last working migration
    ]

    operations = [
        migrations.RunSQL(
            """
            -- Create a new table without the sku column
            CREATE TABLE apiApp_productvariant_new (
                "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, 
                "color" varchar(50) NOT NULL, 
                "size" varchar(20) NOT NULL, 
                "quantity" integer unsigned NOT NULL CHECK ("quantity" >= 0), 
                "price_override" decimal NULL, 
                "product_id" bigint NOT NULL REFERENCES "apiApp_product" ("id") DEFERRABLE INITIALLY DEFERRED
            );
            
            -- Copy data from old table to new table
            INSERT INTO apiApp_productvariant_new 
            ("id", "color", "size", "quantity", "price_override", "product_id")
            SELECT 
                "id", "color", "size", "quantity", "price_override", "product_id"
            FROM apiApp_productvariant;
            
            -- Drop the old table
            DROP TABLE apiApp_productvariant;
            
            -- Rename the new table
            ALTER TABLE apiApp_productvariant_new RENAME TO apiApp_productvariant;
            
            -- Recreate indexes
            CREATE INDEX "apiApp_productvariant_product_id_1234abcd" ON "apiApp_productvariant" ("product_id");
            """
        )
    ]