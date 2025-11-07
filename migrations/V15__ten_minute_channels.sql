-- Ten minute message deletion channels
CREATE TABLE ten_minute_channels (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    delete_after_minutes INTEGER NOT NULL DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, channel_id)
);

-- Index for efficient lookups
CREATE INDEX idx_ten_minute_channels_guild ON ten_minute_channels(guild_id);
