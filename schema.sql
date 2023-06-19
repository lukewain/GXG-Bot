CREATE TABLE IF NOT EXISTS levels (
    id BIGINT PRIMARY KEY,
    xp INT NOT NULL,
    modifier FLOAT NOT NULL,
    last_gained BIGINT
);

CREATE TABLE IF NOT EXISTS warnings (
    id BIGINT PRIMARY KEY,
    infractions INT NOT NULL,
    infraction_reasons TEXT[],
    removed_infractions INT
);

CREATE TABLE IF NOT EXISTS immune (
    id BIGINT PRIMARY KEY,
    added BIGINT NOT NULL
);

CREATE TABLE muted (
    id BIGINT PRIMARY KEY,
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
    moderator_id BIGINT PRIMARY KEY,
    unixtimestamp BIGINT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    moderatee_id BIGINT NOT NULL
);