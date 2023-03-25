CREATE TABLE gotosleep (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    active BOOLEAN NOT NULL,
    monday_start_time TIME,
    monday_end_time TIME,
    tuesday_start_time TIME,
    tuesday_end_time TIME,
    wednesday_start_time TIME,
    wednesday_end_time TIME,
    thursday_start_time TIME,
    thursday_end_time TIME,
    friday_start_time TIME,
    friday_end_time TIME,
    saturday_start_time TIME,
    saturday_end_time TIME,
    sunday_start_time TIME,
    sunday_end_time TIME,
    UNIQUE (guild_id, user_id)
);