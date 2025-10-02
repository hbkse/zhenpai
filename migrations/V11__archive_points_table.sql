-- Drop the precomputed balances table (will be recreated as needed)
DROP TABLE IF EXISTS point_balances;

-- Archive the existing points table with current date
ALTER TABLE points
RENAME TO points_2025_10_02;

-- Create new points table with original structure
CREATE TABLE points (LIKE points_2025_10_02 INCLUDING ALL);