from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  model_source TEXT NOT NULL DEFAULT 'modelscope',
  github_mirror_enabled INTEGER NOT NULL DEFAULT 0,
  gpu_mode TEXT NOT NULL DEFAULT 'cpu',
  use_fp16 INTEGER NOT NULL DEFAULT 0,
  use_cuda_kernel INTEGER NOT NULL DEFAULT 0,
  use_deepspeed INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO settings (id) VALUES (1);

CREATE TABLE IF NOT EXISTS roles (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  language TEXT NOT NULL DEFAULT 'zh',
  avatar_path TEXT,
  default_emo_alpha REAL NOT NULL DEFAULT 1.0,
  default_emo_vector TEXT,
  default_emo_text TEXT,
  default_emo_audio_path TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS role_samples (
  id TEXT PRIMARY KEY,
  role_id TEXT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  audio_path TEXT NOT NULL,
  reference_text TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'upload',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS emotion_presets (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  emo_alpha REAL NOT NULL DEFAULT 1.0,
  emo_vector TEXT,
  emo_text TEXT,
  emo_audio_path TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stories (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS story_lines (
  id TEXT PRIMARY KEY,
  story_id TEXT NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
  role_id TEXT REFERENCES roles(id) ON DELETE SET NULL,
  text TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  active_generation_id TEXT,
  emotion_override TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS generations (
  id TEXT PRIMARY KEY,
  role_id TEXT REFERENCES roles(id) ON DELETE SET NULL,
  story_id TEXT REFERENCES stories(id) ON DELETE SET NULL,
  story_line_id TEXT REFERENCES story_lines(id) ON DELETE SET NULL,
  text TEXT NOT NULL,
  language TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  audio_path TEXT,
  duration REAL,
  emotion_snapshot TEXT,
  parameters_snapshot TEXT,
  error TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS generation_versions (
  id TEXT PRIMARY KEY,
  generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
  audio_path TEXT NOT NULL,
  label TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audio_library_items (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  language TEXT,
  gender TEXT,
  style TEXT,
  tags TEXT,
  audio_path TEXT NOT NULL,
  reference_text TEXT,
  source TEXT NOT NULL DEFAULT 'user',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def initialize_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def connect(database_path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    finally:
        conn.close()
