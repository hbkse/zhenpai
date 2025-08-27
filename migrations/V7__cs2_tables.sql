CREATE TABLE users (
    discord_id BIGINT PRIMARY KEY,
    discord_username VARCHAR(255) NOT NULL,
    steamid64 BIGINT
);

CREATE TABLE points (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL,
    change_value INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    category VARCHAR(50) NOT NULL,
    reason TEXT,
    event_source VARCHAR(100),
    event_source_id INTEGER,
    FOREIGN KEY (discord_id) REFERENCES users(discord_id)
);

CREATE TABLE cs2_matches (
    matchid INTEGER PRIMARY KEY,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    winner VARCHAR(255) NOT NULL,
    mapname VARCHAR(64) NOT NULL,
    team1_score INTEGER NOT NULL,
    team2_score INTEGER NOT NULL,
    team1_name VARCHAR(255) NOT NULL,
    team2_name VARCHAR(255) NOT NULL
);

CREATE TABLE cs2_player_stats (
    id SERIAL PRIMARY KEY,
    matchid INTEGER NOT NULL,
    steamid64 BIGINT NOT NULL,
    team_name VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    kills INTEGER NOT NULL,
    deaths INTEGER NOT NULL,
    damage INTEGER NOT NULL,
    assists INTEGER NOT NULL,
    enemy5ks INTEGER NOT NULL,
    enemy4ks INTEGER NOT NULL,
    enemy3ks INTEGER NOT NULL,
    enemy2ks INTEGER NOT NULL,
    utility_count INTEGER NOT NULL,
    utility_damage INTEGER NOT NULL,
    utility_successes INTEGER NOT NULL,
    utility_enemies INTEGER NOT NULL,
    flash_count INTEGER NOT NULL,
    flash_successes INTEGER NOT NULL,
    health_points_removed_total INTEGER NOT NULL,
    health_points_dealt_total INTEGER NOT NULL,
    shots_fired_total INTEGER NOT NULL,
    shots_on_target_total INTEGER NOT NULL,
    v1_count INTEGER NOT NULL,
    v1_wins INTEGER NOT NULL,
    v2_count INTEGER NOT NULL,
    v2_wins INTEGER NOT NULL,
    entry_count INTEGER NOT NULL,
    entry_wins INTEGER NOT NULL,
    equipment_value INTEGER NOT NULL,
    money_saved INTEGER NOT NULL,
    kill_reward INTEGER NOT NULL,
    live_time INTEGER NOT NULL,
    head_shot_kills INTEGER NOT NULL,
    cash_earned INTEGER NOT NULL,
    enemies_flashed INTEGER NOT NULL,
    FOREIGN KEY (matchid) REFERENCES cs2_matches(matchid)
);

-- Indexes for efficient querying
CREATE INDEX idx_points_discord_id ON points(discord_id);
CREATE INDEX idx_points_category ON points(category);
CREATE INDEX idx_points_created_at ON points(created_at);
CREATE INDEX idx_cs2_player_stats_matchid ON cs2_player_stats(matchid);
CREATE INDEX idx_cs2_player_stats_steamid64 ON cs2_player_stats(steamid64);
