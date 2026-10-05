import base64
import io
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from clef_use import provision
from clef_use.config import Config


def test_windows_profile_reuses_lock_hashes_without_generic_torch():
    text = (
        "pillow==1 \\\n    --hash=sha256:kept\n"
        "torch==2 \\\n    --hash=sha256:generic\n"
        "numpy==3 \\\n    --hash=sha256:also-kept\n"
    )
    observed = provision.common_ml_requirements(text)
    assert "torch==" not in observed and "sha256:generic" not in observed
    assert "pillow==1" in observed and "sha256:kept" in observed
    assert "numpy==3" in observed and "sha256:also-kept" in observed


def test_auto_profile_selects_only_observed_windows_gpu(monkeypatch):
    monkeypatch.setattr("clef_use.deployment_profiles.host_system", lambda: "windows")
    monkeypatch.setattr(
        provision.subprocess,
        "run",
        lambda *_a, **_kw: SimpleNamespace(
            returncode=0,
            stdout="Virtual Display Driver\nAMD Radeon(TM) 890M Graphics\n",
        ),
    )
    assert provision.select_profile(Config(), "auto") == "windows-rocm"
    assert provision.select_profile(Config(device="cpu"), "auto") == "windows-cpu"
    monkeypatch.setattr(
        provision.subprocess,
        "run",
        lambda *_a, **_kw: SimpleNamespace(
            returncode=0,
            stdout="AMD Radeon RX 9070 XT",
        ),
    )
    assert provision.select_profile(Config(), "auto") == "windows-rocm"


def test_rocm_rejects_python311_before_installation(monkeypatch):
    monkeypatch.setattr(provision.shutil, "which", lambda _: "python")
    monkeypatch.setattr(
        provision.subprocess,
        "run",
        lambda *_a, **_kw: SimpleNamespace(
            returncode=0,
            stdout="[3, 11]",
        ),
    )
    with pytest.raises(RuntimeError, match="Python 3.12"):
        provision.select_python("python", "windows-rocm")


@pytest.mark.parametrize("failure", ["probe", "model"])
def test_failed_clef_initialization_preserves_configuration(tmp_path, monkeypatch, failure):
    config_path = tmp_path / "config.toml"
    config_path.write_text("# preserve my config\n")
    monkeypatch.setenv("CLEF_USE_CONFIG", str(config_path))
    config = Config(
        model_dir=tmp_path / "models",
        ml_profile="linux-cpu",
        device="cpu",
        clef_python=tmp_path / "clef-env" / "bin" / "python",
        omni_python=tmp_path / "omni-env" / "bin" / "python",
    )
    for name in ("clef-env", "omni-env"):
        folder = tmp_path / name
        folder.mkdir()
        (folder / "pyvenv.cfg").touch()
    monkeypatch.setattr(provision, "select_python", lambda *_: "python")
    monkeypatch.setattr("clef_use.deployment_profiles.host_system", lambda: "linux")
    monkeypatch.setattr(provision, "select_profile", lambda *_: "linux-cpu")
    monkeypatch.setattr("clef_use.native_dependencies.install_native", lambda *_a, **_kw: None)
    monkeypatch.setattr(provision, "install_lock", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        "clef_use.doctor.ml_environment_probe", lambda *_: {"ready": failure != "probe"}
    )
    monkeypatch.setattr(
        provision.subprocess,
        "run",
        lambda *_a, **_kw: SimpleNamespace(
            returncode=0,
            stdout=provision.OMNI_SOURCE_REVISION,
        ),
    )
    monkeypatch.setattr(
        provision, "inventory", lambda *_: [{"model": "Cloudflare/clef-flash", "available": True}]
    )
    monkeypatch.setattr(provision, "download", lambda *_: pytest.fail("cached model downloaded"))
    closed = []

    class Worker:
        def __init__(self, _python, kind, _config):
            self.kind = kind

        def _start(self):
            raise RuntimeError("model load failed")

        def close(self):
            closed.append(self.kind)

    monkeypatch.setattr(provision, "JsonWorker", Worker)
    progress = []
    with pytest.raises(RuntimeError, match="probe failed|model load failed"):
        provision.prepare(config, progress=progress.append)
    assert any("Failed or interrupted:" in message for message in progress)
    assert not any("Saving verified model configuration" in message for message in progress)
    if failure == "model":
        assert any("already cached; skipping" in message for message in progress)
        assert any("Loading clef model" in message for message in progress)
    assert closed == (["clef"] if failure == "model" else [])
    assert config_path.read_text() == "# preserve my config\n"


@pytest.mark.parametrize("bad", [None, "vision", "joint"])
@pytest.mark.parametrize(
    ("hip", "free"), [(None, 512 * 1024**2), (None, 4 * 1024**3), ("7.14", 512 * 1024**2)]
)
def test_nf4_retains_vision_and_joint_head(tmp_path, monkeypatch, bad, hip, free):
    import importlib

    monkeypatch.syspath_prepend(str(Path(provision.__file__).parent))
    monkeypatch.delitem(sys.modules, "model_worker", raising=False)
    worker_module = importlib.import_module("model_worker")

    class Linear4bit:
        pass

    modules = [("language_model.layers.0", Linear4bit())]
    if bad == "vision":
        modules.append(("language_model.model.visual.layers.0", Linear4bit()))
    model = SimpleNamespace(
        named_modules=lambda: modules,
        head=SimpleNamespace(
            parameters=lambda: [
                SimpleNamespace(
                    is_floating_point=lambda: bad != "joint",
                )
            ]
        ),
    )
    recorded = {}
    offloaded = []
    monkeypatch.setattr(worker_module, "offload_output_embeddings", offloaded.append)

    def load(_path, **kwargs):
        recorded.update(kwargs)
        return model, object()

    torch = SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: True, mem_get_info=lambda: (free, 10 * 1024**3)),
        version=SimpleNamespace(hip=hip),
        float32="fp32",
        float16="fp16",
        bfloat16="bf16",
    )
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(
        sys.modules,
        "bitsandbytes",
        SimpleNamespace(
            nn=SimpleNamespace(
                Linear4bit=Linear4bit,
            )
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(
            BitsAndBytesConfig=lambda **kwargs: kwargs,
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "joint_schema_model",
        SimpleNamespace(
            load_release_model=load,
            systemone=lambda *_: None,
        ),
    )
    config = Config(
        model_dir=tmp_path, device="rocm" if hip else "cuda", quantization="4bit"
    ).model_dump(mode="json")
    if bad:
        with pytest.raises(RuntimeError, match="invariant|floating point"):
            worker_module.ClefWorker(config)
    else:
        worker = worker_module.ClefWorker(config)
        assert worker.quantized_modules == 1
        assert recorded["quantization_config"]["llm_int8_skip_modules"] == [
            "lm_head",
            "model.visual",
        ]
        assert recorded["attn_implementation"] == "sdpa"
        assert offloaded == ([] if hip or free >= 1024**3 else [model])
        assert recorded["dtype"] == "fp16"
        assert recorded["local_files_only"] is True


def test_clef_passes_both_pixel_bounds_to_processor(monkeypatch):
    import importlib

    from PIL import Image

    monkeypatch.syspath_prepend(str(Path(provision.__file__).parent))
    worker_module = importlib.import_module("model_worker")
    image = Image.new("RGB", (3840, 2160))
    data = io.BytesIO()
    image.save(data, format="PNG")
    recorded = {}
    worker = object.__new__(worker_module.ClefWorker)
    worker.device = "cuda"
    worker.model, worker.processor = object(), object()

    def systemone(_model, _processor, request, **kwargs):
        recorded.update(request)
        return {"answers": {}}

    worker.systemone = systemone
    worker.request({"image": base64.b64encode(data.getvalue()).decode()})
    assert recorded["media_kwargs"] == {"min_pixels": 56 * 56, "max_pixels": 512 * 512}
    assert recorded["images"][0].size == (3840, 2160)
