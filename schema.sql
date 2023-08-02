CREATE TABLE IF NOT EXISTS levels (
    id BIGINT PRIMARY KEY,
    level INT DEFAULT 0,
    overflow_xp INT NOT NULL,
    modifier FLOAT NOT NULL DEFAULT 1,
    last_gained BIGINT,
    messages INT DEFAULT 1
);

CREATE TABLE IF NOT EXISTS warnings (
    warning_id SERIAL PRIMARY KEY,
    user_id BIGINT,
    reason TEXT NOT NULL,
    unixtimestamp BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS immune (
    id BIGINT PRIMARY KEY,
    type TEXT NOT NULL -- Will either be User or Role
);

CREATE TABLE IF NOT EXISTS muted (
    mute_id SERIAL PRIMARY KEY,
    id BIGINT,
    reason TEXT,
    duration INT NOT NULL,
    expires BIGINT NOT NULL,
    expired BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS errorlog (
    id SERIAL PRIMARY KEY,
    unixtimestamp BIGINT NOT NULL,
    traceback TEXT NOT NULL,
    item TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS moderationlog(
    entry_id SERIAL PRIMARY KEY,
    moderator_id BIGINT,
    unixtimestamp BIGINT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    moderatee_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS modmail (
    user_id BIGINT PRIMARY KEY,
    blocked BOOLEAN DEFAULT FALSE,
    thread_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS xp_blocked (
    id BIGINT PRIMARY KEY,
    type TEXT NOT NULL, -- Will be either 'channel' or 'user'
    added_by BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS blacklist (
    id BIGINT PRIMARY KEY,
    moderator_id BIGINT NOT NULL,
    added_at BIGINT NOT NULL,
    in_server BOOLEAN DEFAULT TRUE
);

-- CREATE TYPE mode as enum (
--     'Unrated',
--     'Competitive',
--     'Other'
-- );

CREATE TABLE IF NOT EXISTS lfg (
    id SERIAL,
    msg_id BIGINT,
    author_id BIGINT NOT NULL,
    gamemode mode,
    players BIGINT[],
    player_limit INT,
    expires_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS val_users (
    id SERIAL,
    user_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    tag TEXT NOT NULL,
    last_verified BIGINT NOT NULL
);