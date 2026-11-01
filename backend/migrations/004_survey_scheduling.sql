-- Survey scheduling: measurements are filled in after the visit, so they may be empty while a survey is Scheduled.
ALTER TABLE site_surveys ALTER COLUMN roof_area DROP NOT NULL;
ALTER TABLE site_surveys ALTER COLUMN roof_direction DROP NOT NULL;
ALTER TABLE site_surveys ALTER COLUMN roof_tilt DROP NOT NULL;
ALTER TABLE site_surveys ALTER COLUMN shading_level DROP NOT NULL;
ALTER TABLE site_surveys ALTER COLUMN cable_distance DROP NOT NULL;
ALTER TABLE site_surveys ALTER COLUMN grid_suitability DROP NOT NULL;
ALTER TABLE site_surveys ALTER COLUMN recommended_capacity DROP NOT NULL;
ALTER TABLE site_surveys ADD COLUMN IF NOT EXISTS recommended_system_type VARCHAR(50);
ALTER TABLE site_surveys ADD COLUMN IF NOT EXISTS scheduled_date DATE;
-- A quotation whose package differs from the survey's recommendation must say why.
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS override_reason TEXT;
