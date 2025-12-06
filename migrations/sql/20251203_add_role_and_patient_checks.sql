-- Migration: add users.role for class table inheritance and strengthen patient numeric checks

-- 1) Add role column to users and populate based on existing role tables
ALTER TABLE users ADD COLUMN IF NOT EXISTS role userrole;

-- Populate roles from existing tables (doctor/admin override patient when overlapping)
UPDATE users SET role = 'patient'
WHERE role IS NULL AND EXISTS (SELECT 1 FROM patients p WHERE p.email = users.email);

UPDATE users SET role = 'doctor'
WHERE EXISTS (SELECT 1 FROM doctors d WHERE d.email = users.email);

UPDATE users SET role = 'admin'
WHERE EXISTS (SELECT 1 FROM admins a WHERE a.email = users.email);

-- Set NOT NULL constraint now that data is populated
ALTER TABLE users ALTER COLUMN role SET NOT NULL;

-- Ensure enum remains constrained by database type (already enforced by userrole enum)

-- 2) Patient numeric checks (age, height, weight)
DO $$
BEGIN
    -- Age between 0 and 120
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_patient_age_range'
    ) THEN
        ALTER TABLE patients ADD CONSTRAINT ck_patient_age_range CHECK (age >= 0 AND age <= 120);
    END IF;

    -- Height between 0 and 250 cm
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_patient_height_range'
    ) THEN
        ALTER TABLE patients ADD CONSTRAINT ck_patient_height_range CHECK (height_cm > 0 AND height_cm <= 250);
    END IF;

    -- Weight between 0 and 600 kg
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_patient_weight_range'
    ) THEN
        ALTER TABLE patients ADD CONSTRAINT ck_patient_weight_range CHECK (weight_kg > 0 AND weight_kg <= 600);
    END IF;
END$$;
