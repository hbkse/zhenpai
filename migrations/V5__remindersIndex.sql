CREATE INDEX idx_remind_time ON remindme (remind_time);

ALTER TABLE remindme
ADD COLUMN created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN is_private BOOLEAN,
ADD COLUMN sent_on TIMESTAMP,
ADD COLUMN deleted_on TIMESTAMP;