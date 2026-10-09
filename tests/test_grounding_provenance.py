"""The isolated ML header boundary must produce a safe, typed setup error."""

import sys
from types import SimpleNamespace

import pytest

from clef_use.grounding import (
    SIGLIP_MODEL,
    SIGLIP_REVISION,
    GroundingHeadProvenanceError,
    load_grounding_head,
)


@pytest.mark.parametrize(
    "invalid",
    [
        {"format": "clef-use-grounding-head-v2"},
        {"backbone_model": "other/backbone"},
        {"backbone_revision": "other-revision"},
        {"temperature": "0.05"},
    ],
)
def test_incompatible_head_header_is_a_typed_setup_failure(monkeypatch, tmp_path, invalid):
    metadata = {
        "format": "clef-use-grounding-head-v3",
        "backbone_model": SIGLIP_MODEL,
        "backbone_revision": SIGLIP_REVISION,
        "temperature": "1",
        **invalid,
    }

    class HeaderBoundary:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def metadata(self):
            return metadata

        def get_tensor(self, name):
            pytest.fail("incompatible provenance must be rejected before tensor loading")

    # safetensors/Torch live in separate ML environments. Simulate only that
    # external header-read boundary, not the provenance or weight validators.
    monkeypatch.setitem(
        sys.modules, "safetensors", SimpleNamespace(safe_open=lambda *a, **kw: HeaderBoundary())
    )
    with pytest.raises(GroundingHeadProvenanceError):
        load_grounding_head(tmp_path / "head.safetensors", dimension=768)
