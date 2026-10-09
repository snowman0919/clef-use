import json

import pytest

from clef_use import cli, provision
from clef_use.config import Config


@pytest.mark.parametrize("action", ["list", "prepare"])
def test_cli_explicit_candidate_selection_never_changes_the_active_default(
    action, monkeypatch, capsys
):
    active = Config(decision_model="Cloudflare/clef-flash", quantization="4bit")
    monkeypatch.setattr(cli, "load_config", lambda: active)
    seen = []

    def prepare(config, *args, decision_model=None, **kwargs):
        seen.append((config, decision_model))
        assert config is active and config.quantization == "4bit"
        return {"status": "PREPARED", "active_model_unchanged": True}

    monkeypatch.setattr(provision, "prepare", prepare)
    monkeypatch.setattr(
        "clef_use.models.inventory", lambda root, model, **kwargs: [{"model": model}]
    )
    status = cli.main(["models", action, "--decision-model", "LiquidAI/d1-3B", "--json"])
    assert status == 0
    result = json.loads(capsys.readouterr().out)
    assert active.decision_model == "Cloudflare/clef-flash" and active.quantization == "4bit"
    if action == "prepare":
        assert seen == [(active, "LiquidAI/d1-3B")]
    else:
        assert result["models"][0]["model"] == "LiquidAI/d1-3B"
        assert result["active_decision_model"] == "Cloudflare/clef-flash"


def test_candidate_prepare_rejects_clef_specific_quantization_before_install(monkeypatch, tmp_path):
    monkeypatch.setattr(
        provision,
        "select_python",
        lambda *_: (_ for _ in ()).throw(
            AssertionError("unsupported precision must fail before installer work")
        ),
    )
    with pytest.raises(ValueError, match="quantization none"):
        provision.prepare(
            Config(model_dir=tmp_path),
            profile="linux-cuda",
            quantization="4bit",
            decision_model="LiquidAI/d1-3B",
        )
