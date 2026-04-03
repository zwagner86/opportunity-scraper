CREATE TABLE IF NOT EXISTS ingestion_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    sources_json TEXT NOT NULL DEFAULT '[]',
    config_snapshot_json TEXT NOT NULL DEFAULT '{}',
    item_count INTEGER NOT NULL DEFAULT 0,
    new_item_count INTEGER NOT NULL DEFAULT 0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    summary TEXT
);

CREATE TABLE IF NOT EXISTS clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    description TEXT,
    key_terms_json TEXT NOT NULL DEFAULT '[]',
    item_count INTEGER NOT NULL DEFAULT 0,
    avg_score REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    community TEXT NOT NULL,
    source_item_id TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    author TEXT,
    created_at TEXT NOT NULL,
    score REAL,
    comments_count INTEGER,
    raw_metadata_json TEXT NOT NULL DEFAULT '{}',
    content_type TEXT NOT NULL,
    parent_source_item_id TEXT,
    ingestion_run_id INTEGER NOT NULL,
    ingested_at TEXT NOT NULL,
    dedupe_hash TEXT NOT NULL,
    language_signals_json TEXT NOT NULL DEFAULT '[]',
    solution_types_json TEXT NOT NULL DEFAULT '[]',
    cluster_id INTEGER,
    saved INTEGER NOT NULL DEFAULT 0,
    dismissed INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT '',
    is_self_serve_friendly INTEGER NOT NULL DEFAULT 0,
    spam_score REAL NOT NULL DEFAULT 0,
    UNIQUE(source, source_item_id),
    FOREIGN KEY (ingestion_run_id) REFERENCES ingestion_runs(id) ON DELETE CASCADE,
    FOREIGN KEY (cluster_id) REFERENCES clusters(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_items_source ON items(source);
CREATE INDEX IF NOT EXISTS idx_items_community ON items(community);
CREATE INDEX IF NOT EXISTS idx_items_created_at ON items(created_at);
CREATE INDEX IF NOT EXISTS idx_items_dedupe_hash ON items(dedupe_hash);
CREATE INDEX IF NOT EXISTS idx_items_cluster_id ON items(cluster_id);
CREATE INDEX IF NOT EXISTS idx_items_saved ON items(saved);
CREATE INDEX IF NOT EXISTS idx_items_dismissed ON items(dismissed);

CREATE TABLE IF NOT EXISTS item_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    signal TEXT NOT NULL,
    phrase TEXT NOT NULL,
    snippet TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_item_evidence_item_id ON item_evidence(item_id);

CREATE TABLE IF NOT EXISTS item_scores (
    item_id INTEGER PRIMARY KEY,
    pain_intensity_score REAL NOT NULL DEFAULT 0,
    repetition_score REAL NOT NULL DEFAULT 0,
    workaround_score REAL NOT NULL DEFAULT 0,
    self_serve_score REAL NOT NULL DEFAULT 0,
    build_simplicity_score REAL NOT NULL DEFAULT 0,
    sales_friction_penalty REAL NOT NULL DEFAULT 0,
    competition_signal_score REAL NOT NULL DEFAULT 0,
    overall_opportunity_score REAL NOT NULL DEFAULT 0,
    rationale_json TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    tag_type TEXT NOT NULL,
    UNIQUE(name, tag_type)
);

CREATE TABLE IF NOT EXISTS item_tags (
    item_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (item_id, tag_id),
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_item_tags_item_id ON item_tags(item_id);
CREATE INDEX IF NOT EXISTS idx_item_tags_tag_id ON item_tags(tag_id);

CREATE TABLE IF NOT EXISTS cluster_items (
    cluster_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    similarity_score REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (cluster_id, item_id),
    FOREIGN KEY (cluster_id) REFERENCES clusters(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
    title,
    body,
    community,
    content='items',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS items_ai AFTER INSERT ON items BEGIN
    INSERT INTO items_fts(rowid, title, body, community)
    VALUES (new.id, new.title, new.body, new.community);
END;

CREATE TRIGGER IF NOT EXISTS items_ad AFTER DELETE ON items BEGIN
    INSERT INTO items_fts(items_fts, rowid, title, body, community)
    VALUES ('delete', old.id, old.title, old.body, old.community);
END;

CREATE TRIGGER IF NOT EXISTS items_au AFTER UPDATE ON items BEGIN
    INSERT INTO items_fts(items_fts, rowid, title, body, community)
    VALUES ('delete', old.id, old.title, old.body, old.community);
    INSERT INTO items_fts(rowid, title, body, community)
    VALUES (new.id, new.title, new.body, new.community);
END;

