import hashlib
import json

import pytest

from clef_use.capabilities import capabilities, guide_manifest, tool_schemas
from clef_use.mcp_server import create_server


async def test_capability_schema_matches_actual_exposed_tools():
    server = create_server()
    exposed = await server.list_tools()
    schemas = tool_schemas()
    assert schemas == {tool.name: tool.inputSchema for tool in exposed}
    report = capabilities(detail=True)
    assert report["schemas"] == schemas
    assert (
        report["schema_sha256"]
        == hashlib.sha256(
            json.dumps(schemas, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    assert {op["family"] for op in report["operations"]} == {
        "menu_assess",
        "command_search",
        "numeric_transform",
        "property_edit",
        "viewport_gesture",
        "modal_cancel",
    }


async def test_capabilities_do_not_start_service_or_initialize_models(monkeypatch):
    from clef_use.client import RuntimeClient

    def forbidden(*args, **kwargs):
        pytest.fail("read-only discovery started runtime work")

    monkeypatch.setattr(RuntimeClient, "_ensure", forbidden)
    monkeypatch.setattr(RuntimeClient, "request", forbidden)
    result = await create_server().call_tool("computer_capabilities", {})
    text = result[0][0].text if isinstance(result, tuple) else result[0].text
    assert json.loads(text)["api_schema_version"] == 1


def test_unknown_operation_is_not_discovered_as_executable():
    with pytest.raises(ValueError, match="UNKNOWN_OPERATION"):
        capabilities(operation_id="shell")


def test_default_operation_availability_matches_unknown_compiled_state():
    from PIL import Image

    from clef_use.schema import Frame, Observation
    from clef_use.state import FactValidity, StateCompiler

    state = StateCompiler().compile(Observation("default", Frame(Image.new("RGB", (64, 64))), ()))
    report = capabilities(detail=True)
    assert report["default_runtime_state"]["provider"] == "NONE"
    assert report["default_runtime_state"]["provider_configuration_path"] == "UNAVAILABLE"
    for operation in report["operations"]:
        available = operation["default_runtime_availability"]
        assert available["status"] == "BLOCKED"
        assert all(
            state.fact(name).validity == FactValidity.UNKNOWN
            for name in available["missing_verified_facts"]
        )
    cancel = capabilities(operation_id="modal_cancel")
    assert cancel["requires_owned_modal"] == {
        "scope": "same_session",
        "identity": "exact_current_modal_id",
    }


def test_bundle_manifest_covers_references_and_detects_actual_content():
    manifest = guide_manifest()
    assert set(manifest["skills"]) == {"clef-use", "clef-use-blender", "clef-use-diagnostics"}
    for skill in manifest["skills"].values():
        assert "SKILL.md" in skill["sha256"]
        assert any(name.startswith("references/") for name in skill["sha256"])


def test_guide_directory_symlink_cannot_publish_outside_files(tmp_path, monkeypatch):
    from clef_use import capabilities as discovery

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "SKILL.md").write_text("private outside document")
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    try:
        (bundle / "clef-use").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation permission unavailable")
    monkeypatch.setattr(discovery, "skill_root", lambda: bundle)
    with pytest.raises(ValueError, match="symlinks"):
        guide_manifest()
    with pytest.raises(ValueError, match="escapes"):
        create_server()
