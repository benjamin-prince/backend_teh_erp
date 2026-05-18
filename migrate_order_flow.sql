-- TEHTEK — Order Flow Migration
-- Run: docker compose cp migrate_order_flow.sql db:/tmp/
--      docker compose exec db psql -U tehtek_user -d tehtek_erp -f /tmp/migrate_order_flow.sql

-- ── Customer flag ─────────────────────────────────────────────────────────────
ALTER TABLE customers
  ADD COLUMN IF NOT EXISTS can_invoice_without_br BOOLEAN DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS invoice_flag_reason     TEXT,
  ADD COLUMN IF NOT EXISTS invoice_flag_set_by     INTEGER,
  ADD COLUMN IF NOT EXISTS invoice_flag_set_at     TIMESTAMP;

-- ── Order flags ───────────────────────────────────────────────────────────────
ALTER TABLE orders
  ADD COLUMN IF NOT EXISTS skip_br              BOOLEAN DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS skip_br_reason       TEXT,
  ADD COLUMN IF NOT EXISTS skip_br_approved_by  INTEGER,
  ADD COLUMN IF NOT EXISTS skip_br_approved_at  TIMESTAMP,
  ADD COLUMN IF NOT EXISTS proforma_sent_at     TIMESTAMP,
  ADD COLUMN IF NOT EXISTS bl_sent_at           TIMESTAMP,
  ADD COLUMN IF NOT EXISTS br_received_at       TIMESTAMP,
  ADD COLUMN IF NOT EXISTS invoiced_at          TIMESTAMP,
  ADD COLUMN IF NOT EXISTS delivered_at         TIMESTAMP;

-- ── Migrate existing statuses to new flow ────────────────────────────────────
-- processing → bl_sent (closest equivalent)
UPDATE orders SET status = 'bl_sent'    WHERE status = 'processing';
-- ready → br_received (items ready = customer confirmed receipt)
UPDATE orders SET status = 'br_received' WHERE status = 'ready';

SELECT 'Migration complete.' AS result;
SELECT status, COUNT(*) FROM orders GROUP BY status;
