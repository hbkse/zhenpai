CREATE TABLE remindme (
  id SERIAL PRIMARY KEY,
  guild_id BIGINT,
  user_id BIGINT NOT NULL,
  channel_id BIGINT,
  remind_time TIMESTAMPTZ NOT NULL,
  content VARCHAR(4800) NOT NULL
);