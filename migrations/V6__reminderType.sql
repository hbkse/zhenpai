-- Change is_private boolean to reminder_type text to support more reminder types
ALTER TABLE remindme 
ADD COLUMN reminder_type VARCHAR(20) DEFAULT 'private';

-- Migrate existing data
UPDATE remindme 
SET reminder_type = CASE 
    WHEN is_private = true THEN 'private'
    WHEN is_private = false THEN 'public'
    ELSE 'private'
END;

-- Make reminder_type NOT NULL after migration
ALTER TABLE remindme 
ALTER COLUMN reminder_type SET NOT NULL;

-- Drop the old is_private column
ALTER TABLE remindme 
DROP COLUMN is_private;


