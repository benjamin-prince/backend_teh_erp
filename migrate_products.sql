-- TEHTEK — Products table migration
-- Run on VPS 1:
-- docker compose exec db psql -U tehtek_user -d tehtek_erp -f /tmp/migrate_products.sql
-- (copy this file to /tmp/ first)

-- New columns for modern product catalog
ALTER TABLE products
  ADD COLUMN IF NOT EXISTS name_fr        VARCHAR(300),
  ADD COLUMN IF NOT EXISTS subcategory    VARCHAR(100),
  ADD COLUMN IF NOT EXISTS barcode        VARCHAR(100),
  ADD COLUMN IF NOT EXISTS model_number   VARCHAR(100),
  ADD COLUMN IF NOT EXISTS weight_kg      NUMERIC(8, 3),
  ADD COLUMN IF NOT EXISTS reorder_level  INTEGER DEFAULT 5,
  ADD COLUMN IF NOT EXISTS tax_rate       NUMERIC(5, 2) DEFAULT 19.25,
  ADD COLUMN IF NOT EXISTS warranty_months INTEGER,
  ADD COLUMN IF NOT EXISTS min_order_qty  INTEGER DEFAULT 1,
  ADD COLUMN IF NOT EXISTS tags           TEXT;

-- Backfill reorder_level from StockItem.min_quantity for existing products
UPDATE products p
SET reorder_level = si.min_quantity
FROM stock_items si
WHERE si.product_id = p.id
  AND p.reorder_level = 5;

-- Unique barcode per company (sparse — allows NULLs)
CREATE UNIQUE INDEX IF NOT EXISTS ix_product_barcode_company
  ON products (company_id, barcode)
  WHERE barcode IS NOT NULL AND deleted_at IS NULL;

-- Index for subcategory filtering
CREATE INDEX IF NOT EXISTS ix_product_subcategory
  ON products (company_id, category, subcategory)
  WHERE deleted_at IS NULL;

SELECT 'Migration complete. New columns added to products.' AS result;
