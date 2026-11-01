-- Installation proof: the homeowner's signature. (The photos table is created by create_all.)
ALTER TABLE installations ADD COLUMN IF NOT EXISTS signed_by_name VARCHAR(255);
ALTER TABLE installations ADD COLUMN IF NOT EXISTS signed_at TIMESTAMP;
ALTER TABLE installations ADD COLUMN IF NOT EXISTS signature_path VARCHAR(500);
-- Delivery: the moment the goods reach the customer, which starts the warranty clock.
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMP;
