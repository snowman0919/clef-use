"""Read-only product discovery, derived from installed tools and guide sources."""

from __future__ import annotations

import hashlib
import json
import sys
from functools import lru_cache
from pathlib import Path

from . import __version__

API_SCHEMA_VERSION = 1
GUIDE_CONTRACT_VERSION = 1
RUNTIME_PROTOCOL_VERSION = 1
SKILL_NAMES = ("clef-use", "clef-use-blender", "clef-use-diagnostics")


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def skill_root() -> Path:
    bundled = Path(__file__).parent / "agent-skills"
    if bundled.is_dir():
        return bundled
    source = Path(__file__).resolve().parents[2] / "agent-skills"
    if not source.is_dir():
        raise FileNotFoundError("Guide bundle missing; reinstall this runtime release")
    return source


def guide_manifest() -> dict:
    skills = {}
    for name in SKILL_NAMES:
        root = skill_root() / name
        if root.is_symlink():
            raise ValueError("Guide bundle must not contain symlinks")
        hashes = {}
        for path in sorted(root.rglob("*"), key=lambda path: path.relative_to(root).as_posix()):
            if path.is_symlink():
                raise ValueError("Guide bundle must not contain symlinks")
            if path.is_file():
                hashes[path.relative_to(root).as_posix()] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
        if "SKILL.md" not in hashes:
            raise ValueError(f"Missing guide: {name}")
        skills[name] = {"sha256": hashes, "digest": digest(hashes)}
    return {
        "runtime_version": __version__,
        "api_schema_version": API_SCHEMA_VERSION,
        "guide_contract_version": GUIDE_CONTRACT_VERSION,
        "api_range": ">=0.1.29,<0.2",
        "required_tools": [
            "computer_run",
            "computer_continue",
            "computer_observe",
            "computer_status",
            "computer_abort",
        ],
        "skills": skills,
    }


@lru_cache(maxsize=1)
def _schemas_json() -> str:
    from .mcp_server import create_server

    # FastMCP generates these parameters from the registered callable signatures.
    # Creating the facade does not start the runtime, capture or load models.
    server = create_server()
    return json.dumps({tool.name: tool.parameters for tool in server._tool_manager.list_tools()})


def tool_schemas() -> dict:
    return json.loads(_schemas_json())


@lru_cache(maxsize=1)
def schema_sha256() -> str:
    return digest(tool_schemas())


def capabilities(*, detail: bool = False, operation_id: str | None = None) -> dict:
    from .models import DEFAULT_DECISION_MODEL, MODEL_REVISIONS
    from .operations import operation_registry

    operations = list(operation_registry())
    for operation in operations:
        operation["default_runtime_availability"] = {
            "status": "BLOCKED",
            "scope": "shipped_default_runtime",
            "reason": "Default capture supplies no verified application state; the optional "
            "Blender public-RNA observer supplies only partial facts and does not prove "
            "effective keymap, popup, text/IME ownership, or global busy absence.",
            "missing_verified_facts": [
                name
                for name in operation["requires"]
                if name not in {"window", "foreground", "target_geometry"}
            ],
            "live_probe": "NOT_PROBED",
        }
        for selector in ("field", "operation", "modal"):
            conditional = operation.get(f"requires_by_{selector}")
            if conditional is not None:
                operation["default_runtime_availability"][
                    f"missing_verified_facts_by_{selector}"
                ] = {
                    value: [
                        name
                        for name in names
                        if name not in {"window", "foreground", "target_geometry"}
                    ]
                    for value, names in conditional.items()
                }
    if operation_id is not None:
        operation = next((op for op in operations if op["family"] == operation_id), None)
        if operation is None:
            raise ValueError("UNKNOWN_OPERATION: discover supported operation IDs first")
        return operation
    schemas = tool_schemas()
    result = {
        "runtime_version": __version__,
        "api_schema_version": API_SCHEMA_VERSION,
        "schema_sha256": schema_sha256(),
        "runtime_protocol_version": RUNTIME_PROTOCOL_VERSION,
        "guide_contract_version": GUIDE_CONTRACT_VERSION,
        "operation_registry_version": 6,
        "default_runtime_state": {
            "provider": "WINDOWS_UIA" if sys.platform == "win32" else "NONE",
            "observation_access_level": "PIXELS_ONLY",
            "trusted_application_evidence": "UNAVAILABLE",
            "provider_configuration_path": "config.toml: blender_state_socket "
            "(Linux X11 or Windows)",
            "operation_availability": "BLOCKED",
            "live_probe": "NOT_PROBED",
            "verified_operation_scope": "API_ASSISTED_FIXTURE_ONLY",
            "native_state": "Window identity may be available; desktop permissions are not probed.",
        },
        "tools": list(schemas),
        "built_in_state_providers": [
            {
                "provider": "WINDOWS_UIA",
                "platform": "win32",
                "activation": "automatic on Windows; native support requires a live probe",
                "availability": "NOT_PROBED",
                "facts": ["text_focus", "ime_composing"],
                "scope": "Fresh supported TextEdit control bound to native foreground PID, "
                "HWND, physical bounds and unchanged actual focus",
                "composition_absence": "Supported GetActiveComposition S_OK plus null range only",
                "limits": "Unsupported/error/stale remains UNKNOWN. No writability, global IME "
                "idle, popup absence, effective keymap or Blender operation admission inferred.",
                "isolation": "Owned stdlib worker with actual PID binding and bounded termination",
            }
        ],
        "optional_state_providers": [
            {
                "provider": "BLENDER_PUBLIC_RNA",
                "access_level": "APP_TELEMETRY_ASSISTED",
                "configuration": "blender_state_socket",
                "producer": "blender --python <clef-use blender-observer-script output> "
                "-- --clef-state-dir <new private directory>",
                "transport": "Linux private Unix socket with SO_PEERCRED and X-Resource local PID; "
                "Windows IPv4 loopback with native TCP peer PID, process token user, private "
                "NTFS endpoint metadata and foreground client identity",
                "availability": "PARTIAL; NOT_PROBED",
                "window_scope": "One RNA window matching the foreground native client dimensions",
                "raw_observations": [
                    "application_snapshot",
                    "editor_layout",
                    "keymap_inventory",
                    "selection_identities",
                    "scene_units",
                    "active_tool",
                ],
                "keymap_inventory": "Merged user bindings, tri-state modifiers and content digest; "
                "effective dispatch remains UNKNOWN",
                "selection_identities": "Complete selected-name map to process-scoped public "
                "ID.session_uid; unavailable or incoherent identity remains UNKNOWN",
                "scene_units": "Process-bound scene identity, length system/default unit and "
                "scale; does not establish field focus, modal unit or coordinate space",
                "active_tool": "Configured VIEW_3D workspace tool for the independently bound "
                "current window context mode and observed area IDs; focused editor and effective "
                "input dispatch remain UNKNOWN",
                "loading": "Positive-only busy evidence when the owning manager's public "
                "interface lock is True; False or unavailable leaves global idle UNKNOWN",
                "unknown_facts": ["popup", "text_focus", "ime_composing", "keymap"],
                "input_authority": "No operation readiness inferred from partial snapshots",
            }
        ],
        "modes": ["AUTO", "STRUCTURED", "VISUAL", "CANVAS", "ASSESS"],
        "inputs": {
            "legacy": ["text", "pointer", "press", "hotkey"],
            "typed": ["key", "chord", "text", "pointer", "gesture", "wheel"],
            "physical_code": "UNSUPPORTED",
            "ime": "composition context guard; no IME engine control",
            "unicode": "Windows native; X11 requires explicit clipboard, including ASCII literals",
            "macos_watchdog": "limited: native foreground and human-input query unavailable",
        },
        "operations": operations
        if detail
        else [
            {key: op[key] for key in ("family", "description", "default_runtime_availability")}
            for op in operations
        ],
        "platform": sys.platform,
        "model_policy": {
            "default_decision_model": DEFAULT_DECISION_MODEL,
            "pinned_revisions": MODEL_REVISIONS,
            "readiness": "NOT_PROBED",
        },
        "limitations": [
            "Discovery does not probe desktop permissions or initialize models.",
            "ASSESS sends no input; cached observations authorize no new input.",
            "State-dependent operations require verified fresh local provider facts.",
            "All six operations block on unknown facts in the default installation; "
            "the optional Blender public-RNA observer retains unknown dispatch context.",
            "Typed continuation requires an explicit operation; "
            "verify the complete goal with a new ASSESS contract.",
            "Operation SUCCEEDED verifies its typed effect; "
            "session NEEDS_REPLAN requires fresh goal ASSESS.",
            "No measured 100ms profile is advertised until native release gates pass.",
        ],
        "guides": guide_manifest(),
        "resources": [
            "clef-use://api/schema",
            *[f"clef-use://guides/{name}/SKILL.md" for name in SKILL_NAMES],
        ],
    }
    if detail:
        result["schemas"] = schemas
    return result
