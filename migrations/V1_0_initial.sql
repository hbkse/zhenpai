CREATE TABLE tags (
  id SERIAL PRIMARY KEY,
  guild_id VARCHAR(255) NOT NULL,
  creator_id VARCHAR(255) NOT NULL,
  tag VARCHAR(255) NOT NULL,
  content VARCHAR(4800) NOT NULL,
  UNIQUE (guild_id, tag)
);