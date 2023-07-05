CREATE TABLE IF NOT EXISTS levels (
    user_id BIGINT PRIMARY KEY,
    xp INT NOT NULL,
    modifier FLOAT NOT NULL,
    last_gained BIGINT
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