"""
Server-side user settings — singleton rows persisted in SQLite so every
client window, API consumer, and headless flow reads the same preferences.

Two domains live here: capture/refine defaults and long-form generation
defaults. Each has a ``get_*`` that lazily creates the row with defaults and
an ``update_*`` that accepts a partial payload.
"""

from typing import Any

from sqlalchemy.orm import Session

from ..database import CaptureSettings as DBCaptureSettings
from ..database import DownloadSettings as DBDownloadSettings
from ..database import GenerationSettings as DBGenerationSettings
from ..utils.capture_chords import (
    default_push_to_talk_chord,
    default_toggle_to_talk_chord,
)


SINGLETON_ID = 1


def _get_or_create_capture_row(db: Session) -> DBCaptureSettings:
    row = db.query(DBCaptureSettings).filter(DBCaptureSettings.id == SINGLETON_ID).first()
    if row is None:
        row = DBCaptureSettings(
            id=SINGLETON_ID,
            chord_push_to_talk_keys=default_push_to_talk_chord(),
            chord_toggle_to_talk_keys=default_toggle_to_talk_chord(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _get_or_create_generation_row(db: Session) -> DBGenerationSettings:
    row = db.query(DBGenerationSettings).filter(DBGenerationSettings.id == SINGLETON_ID).first()
    if row is None:
        row = DBGenerationSettings(id=SINGLETON_ID)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _get_or_create_download_row(db: Session) -> DBDownloadSettings:
    row = db.query(DBDownloadSettings).filter(DBDownloadSettings.id == SINGLETON_ID).first()
    if row is None:
        row = DBDownloadSettings(id=SINGLETON_ID)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _apply_patch(row: Any, patch: dict[str, Any]) -> None:
    """Apply a partial update to a settings row.

    Values explicitly set to ``None`` are honored only for columns where the
    schema allows it — clearing ``default_playback_voice_id`` works, but a
    ``None`` for a non-nullable field is dropped rather than crashing the
    request. Unknown keys are ignored.
    """
    columns = type(row).__table__.columns
    for key, value in patch.items():
        col = columns.get(key)
        if col is None:
            continue
        if value is None and not col.nullable:
            continue
        setattr(row, key, value)


def get_capture_settings(db: Session) -> DBCaptureSettings:
    """Return the capture settings row, creating it with defaults if missing."""
    return _get_or_create_capture_row(db)


def update_capture_settings(db: Session, patch: dict[str, Any]) -> DBCaptureSettings:
    row = _get_or_create_capture_row(db)
    _apply_patch(row, patch)
    db.commit()
    db.refresh(row)
    return row


def get_generation_settings(db: Session) -> DBGenerationSettings:
    """Return the generation settings row, creating it with defaults if missing."""
    return _get_or_create_generation_row(db)


def update_generation_settings(db: Session, patch: dict[str, Any]) -> DBGenerationSettings:
    row = _get_or_create_generation_row(db)
    _apply_patch(row, patch)
    db.commit()
    db.refresh(row)
    return row


def get_download_settings(db: Session) -> DBDownloadSettings:
    """Return download settings, creating the singleton row if missing."""
    return _get_or_create_download_row(db)


def update_download_settings(db: Session, patch: dict[str, Any]) -> DBDownloadSettings:
    row = _get_or_create_download_row(db)
    _apply_patch(row, patch)
    db.commit()
    db.refresh(row)
    return row


def get_download_settings_snapshot() -> tuple[str, bool]:
    """Read download settings outside a FastAPI request."""
    try:
        from ..database import session as db_session

        if db_session.SessionLocal is None:
            return "modelscope", False
        db = db_session.SessionLocal()
        try:
            row = get_download_settings(db)
            return row.model_source, row.github_mirror_enabled
        finally:
            db.close()
    except Exception:
        return "modelscope", False
