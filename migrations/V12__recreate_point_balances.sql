-- Recreate point_balances table that was wrongly dropped in V11
CREATE TABLE point_balances (
    discord_id BIGINT PRIMARY KEY,
    current_balance INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_transaction_id INTEGER,
    FOREIGN KEY (discord_id) REFERENCES users(discord_id),
    FOREIGN KEY (last_transaction_id) REFERENCES points(id)
);

CREATE INDEX idx_point_balances_last_updated ON point_balances(last_updated);
CREATE INDEX idx_point_balances_current_balance ON point_balances(current_balance);