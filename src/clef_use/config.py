from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import Field

from .deployment_profiles import ProfileName
from .schema import StrictModel


def config_path() -> Path:
    return Path(os.environ.get("CLEF_USE_CONFIG", Path.home() / ".config/clef-use/config.toml"))


def state_dir() -> Path:
    return Path(os.environ.get("CLEF_USE_STATE_DIR", Path.home() / ".local/state/clef-use"))


class Config(StrictModel):
    decision_model: Literal["Cloudflare/clef-flash", "Cloudflare/clef"] = "Cloudflare/clef-flash"
    device: Literal["auto", "cpu", "cuda", "rocm", "xpu", "mps"] = "auto"
    parser_device: Literal["auto", "cpu", "cuda", "rocm", "xpu", "mps"] = "auto"
    quantization: Literal["none", "4bit"] = "none"
    ml_profile: ProfileName = "auto"
    rocm_arch: str | None = Field(default=None, pattern=r"^gfx[0-9a-f]+$")
    model_dir: Path = Path.home() / ".cache/clef-use/models"
    clef_python: Path | None = None
    omni_python: Path | None = None
    omni_source: Path | None = None
    max_steps: int = Field(default=30, ge=1, le=100)
    confidence_threshold: float = Field(default=0.55, ge=0.05, le=1)
    no_progress_limit: int = Field(default=3, ge=2, le=10)
    settle_seconds: float = Field(default=0.3, ge=0, le=5)
    screen_timeout: float = Field(default=5, ge=0.05, le=30)
    screen_interval: float = Field(default=0.05, ge=0.005, le=0.5)
    screen_stable_samples: int = Field(default=2, ge=2, le=10)
    perception_cache: bool = True
    backend_timeout: float = Field(default=180, ge=1, le=600)
    max_candidates: int = Field(default=48, ge=12, le=100)
    activity_overlay: bool = True
    debug: bool = False


def load_config() -> Config:
    path = config_path()
    return Config.model_validate(tomllib.loads(path.read_text()) if path.exists() else {})
