CREATE TABLE point_balances (
    discord_id BIGINT PRIMARY KEY,
    current_balance INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_transaction_id INTEGER,
    FOREIGN KEY (discord_id) REFERENCES users(discord_id),
    FOREIGN KEY (last_transaction_id) REFERENCES points(id)
);

CREATE TABLE processed_events (
    id SERIAL PRIMARY KEY,
    event_source VARCHAR(100) NOT NULL,
    event_source_id INTEGER NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_source, event_source_id)
);

CREATE INDEX idx_processed_events_source_id ON processed_events(event_source, event_source_id);
CREATE INDEX idx_processed_events_processed_at ON processed_events(processed_at);

CREATE INDEX idx_point_balances_last_updated ON point_balances(last_updated);
CREATE INDEX idx_point_balances_current_balance ON point_balances(current_balance);
