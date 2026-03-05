pub const SCHEMA_SQL: &str = r#"
CREATE TABLE IF NOT EXISTS saves (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    state_json TEXT NOT NULL,
    conversation_history TEXT DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS saves (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    state_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY,
    save_id INTEGER REFERENCES saves(id),
    turn INTEGER NOT NULL,
    player_input TEXT,
    summary TEXT,
    narrative TEXT,
    keywords TEXT
);
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY,
    save_id INTEGER REFERENCES saves(id),
    turn INTEGER NOT NULL,
    summary TEXT,
    keywords TEXT
);

-- Cache for LLM-generated civilization templates
CREATE TABLE IF NOT EXISTS generated_templates (
    id INTEGER PRIMARY KEY,
    era_id TEXT NOT NULL,
    location_id TEXT NOT NULL,
    template_json TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(era_id, location_id)
);

"#;
