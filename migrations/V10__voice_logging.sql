-- Simple voice logging channel configuration
CREATE TABLE voice_log_config (
    guild_id BIGINT PRIMARY KEY,
    log_channel_id BIGINT NOT NULL,
    enabled BOOLEAN DEFAULT true,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);