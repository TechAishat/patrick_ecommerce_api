from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('apiApp', '0001_initial'),  # Adjust this to your last migration
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- First, create a new table without the sku column
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

            -- Drop the old table
            DROP TABLE apiApp_productvariant;

            -- Rename the new table
            ALTER TABLE apiApp_productvariant_new RENAME TO apiApp_productvariant;

            -- Recreate the index
            CREATE INDEX "apiApp_productvariant_product_id_1234abcd" ON "apiApp_productvariant" ("product_id");
            """,
            reverse_sql="""
            -- This is the reverse migration in case you need to rollback
            CREATE TABLE apiApp_productvariant_old (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                sku VARCHAR(100) NOT NULL,
                color VARCHAR(50) NOT NULL,
                size VARCHAR(20) NOT NULL,
                quantity INTEGER UNSIGNED NOT NULL,
                price_override DECIMAL(10, 2) NULL,
                FOREIGN KEY (product_id) REFERENCES "apiApp_product" ("id") DEFERRABLE INITIALLY DEFERRED
            );

            INSERT INTO apiApp_productvariant_old
            (id, product_id, color, size, quantity, price_override, sku)
            SELECT id, product_id, color, size, quantity, price_override, 
                   'DEFAULT_SKU' as sku  -- Provide a default value for sku
            FROM apiApp_productvariant;

            DROP TABLE apiApp_productvariant;
            ALTER TABLE apiApp_productvariant_old RENAME TO apiApp_productvariant;
            CREATE INDEX "apiApp_productvariant_product_id_1234abcd" ON "apiApp_productvariant" ("product_id");
            """
        ),
    ]