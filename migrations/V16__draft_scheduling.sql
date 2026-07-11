-- MTG draft scheduling
CREATE TABLE draft_sessions (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    announcement_message_id BIGINT,
    organizer_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    draft_type TEXT NOT NULL DEFAULT 'in_person',      -- 'in_person' | 'online'
    candidate_days TEXT NOT NULL,                      -- comma-separated ISO dates, e.g. '2026-07-17,2026-07-18'
    hour_start INTEGER NOT NULL,                       -- earliest selectable start hour (local, 24h)
    hour_end INTEGER NOT NULL,                         -- latest selectable start hour (local, 24h)
    deadline TIMESTAMP NOT NULL,                       -- naive UTC
    status TEXT NOT NULL DEFAULT 'collecting',         -- collecting | needs_organizer | decided | cancelled
    reminder_stage INTEGER NOT NULL DEFAULT 0,         -- 0 none, 1 first DM, 2 second DM, 3 public last call
    day_of_reminder_sent BOOLEAN NOT NULL DEFAULT FALSE,
    picked_slot TIMESTAMP,                             -- naive UTC start time of the locked-in draft
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE draft_responses (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES draft_sessions(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    is_out BOOLEAN NOT NULL DEFAULT FALSE,
    availability TEXT NOT NULL DEFAULT '{}',           -- JSON: {"2026-07-17": [18, 19, 20], ...} local start hours
    note TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(session_id, user_id)
);

CREATE INDEX idx_draft_sessions_status ON draft_sessions(status);
CREATE INDEX idx_draft_responses_session ON draft_responses(session_id);
