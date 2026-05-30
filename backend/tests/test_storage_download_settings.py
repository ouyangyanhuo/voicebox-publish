import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import config
from backend.database.models import Base
from backend.services import settings as settings_service
from backend.services import cuda, model_sources


def test_install_roots_and_cache_env_are_install_local(tmp_path):
    original_install = config.get_install_dir()
    try:
        config.set_install_dir(tmp_path)

        assert config.get_data_dir() == tmp_path / "data"
        assert config.get_cache_root_dir() == tmp_path / "cache"
        assert config.get_models_dir() == tmp_path / "model"
        assert config.get_huggingface_models_dir() == tmp_path / "model" / "huggingface"
        assert config.get_modelscope_models_dir() == tmp_path / "model" / "modelscope"

        assert Path(os.environ["HF_HOME"]) == tmp_path / "cache" / "huggingface"
        assert Path(os.environ["HF_HUB_CACHE"]) == tmp_path / "model" / "huggingface"
        assert Path(os.environ["MODELSCOPE_CACHE"]) == tmp_path / "model" / "modelscope"
        assert Path(os.environ["TORCH_HOME"]) == tmp_path / "cache" / "torch"
    finally:
        config.set_install_dir(original_install)


def test_download_settings_defaults_and_updates():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine)
    db = session_local()
    try:
        row = settings_service.get_download_settings(db)
        assert row.model_source == "modelscope"
        assert row.github_mirror_enabled is False

        updated = settings_service.update_download_settings(
            db,
            {"model_source": "modelscope", "github_mirror_enabled": True},
        )
        assert updated.model_source == "modelscope"
        assert updated.github_mirror_enabled is True
    finally:
        db.close()


def test_modelscope_missing_mapping_fails_without_hf_fallback(monkeypatch):
    monkeypatch.setattr(model_sources, "get_download_settings_snapshot", lambda: ("modelscope", False))

    with pytest.raises(RuntimeError, match="not mapped"):
        model_sources.resolve_model_reference("example/missing-model")


def test_github_proxy_builder_uses_fixed_proxy(monkeypatch):
    monkeypatch.setattr(settings_service, "get_download_settings_snapshot", lambda: ("huggingface", True))

    url = "https://github.com/jamiepine/voicebox/releases/download/v1/file.tar.gz"
    assert cuda.build_github_download_url(url) == f"{cuda.GITHUB_PROXY_BASE}{url}"
