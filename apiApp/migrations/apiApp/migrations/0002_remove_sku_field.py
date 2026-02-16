from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('apiApp', '0001_initial'),  # This should match your first migration
    ]

    operations = [
        migrations.RunSQL(
            """
            PRAGMA foreign_keys=off;
            BEGIN TRANSACTION;
            
            -- Create a temporary table without the sku column
            CREATE TABLE apiApp_productvariant_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL REFERENCES "apiApp_product" ("id") DEFERRABLE INITIALLY DEFERRED,
                color VARCHAR(50) NOT NULL,
                size VARCHAR(20) NOT NULL,
                quantity INTEGER UNSIGNED NOT NULL,
                price_override DECIMAL(10, 2) NULL,
                FOREIGN KEY (product_id) REFERENCES "apiApp_product" ("id") DEFERRABLE INITIALLY DEFERRED
            );
            
            -- Copy data from old table to new table
            INSERT INTO apiApp_productvariant_new
            (id, product_id, color, size, quantity, price_override)
            SELECT id, product_id, color, size, quantity, price_override
            FROM apiApp_productvariant;
            
            -- Drop old table
            DROP TABLE apiApp_productvariant;
            
            -- Rename new table to old table name
            ALTER TABLE apiApp_productvariant_new RENAME TO apiApp_productvariant;
            
            -- Recreate indexes
            CREATE INDEX "apiApp_productvariant_product_id_1234abcd" ON "apiApp_productvariant" ("product_id");
            
            COMMIT;
            PRAGMA foreign_keys=on;
            """
        ),
    ]