-- Drafts are generic now: replace draft_type with a free-form display name
ALTER TABLE draft_sessions RENAME COLUMN draft_type TO name;
ALTER TABLE draft_sessions ALTER COLUMN name SET DEFAULT 'Draft';
