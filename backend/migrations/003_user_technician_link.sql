-- Links a staff user with the technician role to a technician record.
ALTER TABLE users ADD COLUMN IF NOT EXISTS technician_id INTEGER REFERENCES technicians(id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_technician_id ON users (technician_id);
