CREATE TABLE cs2_match_bets (
    id SERIAL PRIMARY KEY,
    cs_match_id INTEGER NOT NULL,
    user_id BIGINT NOT NULL,
    amount INTEGER NOT NULL,
    team_name VARCHAR(255) NOT NULL,
    odds DECIMAL(10, 4) NOT NULL,
    payout INTEGER,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cs_match_id) REFERENCES cs2_matches(matchid),
    FOREIGN KEY (user_id) REFERENCES users(discord_id)
);

-- Indexes for efficient querying
CREATE INDEX idx_cs2_match_bets_match_id ON cs2_match_bets(cs_match_id);
CREATE INDEX idx_cs2_match_bets_user_id ON cs2_match_bets(user_id);
CREATE INDEX idx_cs2_match_bets_active ON cs2_match_bets(active);
