"""Generate/check common examples against the actual MCP schema and CLI parser."""

from __future__ import annotations

import argparse
import ast
import json
import re
import shlex
import tomllib
from pathlib import Path

from jsonschema import ValidationError, validate

from clef_use.capabilities import (
    SKILL_NAMES,
    capabilities,
    guide_manifest,
    skill_root,
    tool_schemas,
)
from clef_use.cli import parser

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = [
    {"tool": "computer_capabilities", "arguments": {"detail": False}},
    {"tool": "computer_capabilities", "arguments": {"operation_id": "numeric_transform"}},
    {"tool": "computer_observe", "arguments": {"include_image": True, "refresh": True}},
    {
        "tool": "computer_run",
        "arguments": {
            "goal": "Assess whether the Blender File menu is open",
            "execution_mode": "ASSESS",
            "operation": {"family": "menu_assess", "menu": "File"},
        },
    },
]
COMMANDS = [
    "clef-use capabilities --json",
    "clef-use capabilities --detail --json",
    "clef-use capabilities --operation-id numeric_transform --json",
    "clef-use integrate codex --dry-run",
    "clef-use integrate codex --scope user --skills core --skills blender --skills diagnostics",
    "clef-use integrate hermes --scope user",
    "clef-use integrate omp --scope user",
    "clef-use integrations status --json",
    "clef-use integrations verify codex --live --read-only",
    "clef-use integrations remove codex --dry-run",
    "clef-use integrations refresh --managed-only",
]


def validate_examples():
    schemas = tool_schemas()
    for example in EXAMPLES:
        validate(example["arguments"], schemas[example["tool"]])
    cli = parser()
    for command in COMMANDS:
        cli.parse_args(shlex.split(command)[1:])
    for name in SKILL_NAMES:
        root = skill_root() / name
        body = (root / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = body.split("---", 2)[1]
        if not re.search(rf"^name: {re.escape(name)}$", frontmatter, re.M):
            raise ValueError(f"guide name mismatch: {name}")
        if len(body.splitlines()) > 180:
            raise ValueError(f"guide exceeds 180 lines: {name}")
        for ref in re.findall(r"\]\((references/[^)]+)\)", body):
            if not (root / ref).is_file() or not (root / ref).resolve().is_relative_to(
                root.resolve()
            ):
                raise ValueError(f"missing or escaped reference: {ref}")
        for relative in ("SKILL.md", *[str(p.relative_to(root)) for p in root.rglob("*.md")]):
            text = (root / relative).read_text(encoding="utf-8")
            for block in re.findall(r"```json\s*\n(.*?)\n```", text, re.S):
                value = json.loads(block)
                # Baseline standalone arguments are unambiguous by their fields.
                tool = (
                    "computer_observe"
                    if "refresh" in value
                    else "computer_run"
                    if "goal" in value
                    else None
                )
                if tool:
                    validate(value, schemas[tool])


def outputs():
    capability = capabilities()
    reference = "# Installed contract examples\n\n"
    reference += (
        f"API schema version {capability['api_schema_version']}; "
        "discover the installed runtime first.\n"
    )
    reference += "These examples do not authorize input. Operations require trusted local state;\n"
    reference += (
        "missing editor/keymap/selection evidence returns BLOCKED. No 100ms claim is made.\n\n"
    )
    for example in EXAMPLES:
        reference += f"Send to `{example['tool']}`:\n\n```json\n"
        reference += json.dumps(example["arguments"], indent=2) + "\n```\n\n"
    reference += "## CLI\n\n```sh\n" + "\n".join(COMMANDS) + "\n```\n"
    return {
        ROOT / "agent-skills/clef-use/references/LIVE_API.md": reference,
        ROOT / "agent-skills/examples.json": json.dumps(
            {"tools": EXAMPLES, "cli": COMMANDS}, indent=2
        )
        + "\n",
    }


def _published_documents(root: Path):
    documents = [root / "README.md"]
    historical = {"evidence", "validation", "decisions"}
    records = {"BASELINE_AND_SOURCES.md", "PRIOR_PLATFORM_PLAN.md", "EXECUTION_STATUS.md"}
    documents.extend(
        path
        for path in (root / "docs").rglob("*.md")
        if not historical.intersection(path.relative_to(root / "docs").parts)
        and path.name not in records
    )
    documents.extend((root / "agent-skills").rglob("*.md"))
    return sorted(documents)


def validate_published_examples(root: Path = ROOT) -> int:
    cli = parser()
    count = 0
    for path in _published_documents(root):
        text = path.read_text(encoding="utf-8")
        for block in re.findall(r"```(?:sh|bash|powershell)\s*\n(.*?)\n```", text, re.S):
            for line in re.sub(r"\\\r?\n", " ", block).splitlines():
                tokens = shlex.split(line, comments=True)
                if tokens[:2] == ["uv", "run"]:
                    tokens = tokens[2:]
                if not tokens or tokens[0] != "clef-use":
                    continue
                try:
                    cli.parse_args(tokens[1:])
                except SystemExit as error:
                    raise ValueError(
                        f"invalid published CLI example in {path.relative_to(root)}: {line}"
                    ) from error
                count += 1
    return count


def validate_published_tool_examples(root: Path = ROOT) -> int:
    schemas = tool_schemas()
    count = 0

    class JsonConstants(ast.NodeTransformer):
        def visit_Name(self, node):
            values = {"true": True, "false": False, "null": None}
            return ast.Constant(values[node.id]) if node.id in values else node

    for path in _published_documents(root):
        text = path.read_text(encoding="utf-8")
        for code in re.findall(r"(?<!`)`([^`]+)`(?!`)", text, re.S):
            if not re.fullmatch(r"computer_\w+\(.*\)", code, re.S):
                continue
            try:
                call = ast.parse(code, mode="eval").body
                if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
                    raise ValueError("expected a named tool call")
                schema = schemas[call.func.id]
                properties = schema["properties"]
                parameters = list(properties)
                values, placeholders = {}, set()

                arguments = [(parameters[index], value) for index, value in enumerate(call.args)]
                arguments.extend((keyword.arg, keyword.value) for keyword in call.keywords)
                for name, value in arguments:
                    if name not in properties or name in values or name in placeholders:
                        raise ValueError("unknown or repeated parameter")
                    if isinstance(value, ast.Name) and value.id == name:
                        # API signatures document a named parameter without
                        # supplying a task-specific value, such as run(goal).
                        placeholders.add(name)
                    else:
                        values[name] = ast.literal_eval(JsonConstants().visit(value))

                validate(
                    values,
                    {
                        **schema,
                        "required": [
                            n for n in schema.get("required", []) if n not in placeholders
                        ],
                    },
                )
            except (
                KeyError,
                IndexError,
                SyntaxError,
                ValueError,
                TypeError,
                ValidationError,
            ) as error:
                raise ValueError(
                    f"invalid published tool example in {path.relative_to(root)}: {code}"
                ) from error
            count += 1
    return count


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--check", action="store_true")
    args = argparser.parse_args()
    generated = outputs()
    for path, text in generated.items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                raise ValueError(f"generated examples drifted: {path.relative_to(ROOT)}")
        else:
            path.write_text(text, encoding="utf-8", newline="\n")
    validate_examples()
    manifest_path = ROOT / "agent-skills/manifest.json"
    bundle = guide_manifest()
    bundle["runtime_version"] = tomllib.loads(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]["version"]
    manifest = json.dumps(bundle, indent=2) + "\n"
    if args.check:
        if manifest_path.read_text(encoding="utf-8") != manifest:
            raise ValueError("guide manifest drifted; regenerate agent contract")
    else:
        manifest_path.write_text(manifest, encoding="utf-8", newline="\n")
    for language in ("en", "ko", "zh-CN", "ja"):
        path = ROOT / f"docs/{language}/AGENT_GUIDE.md"
        if not path.exists():
            continue
        blocks = re.findall(r"```sh\s*\n(.*?)\n```", path.read_text(encoding="utf-8"), re.S)
        if not blocks or blocks[0].splitlines() != COMMANDS:
            raise ValueError(f"localized command drift: {language}")
    published_examples = validate_published_examples()
    published_tools = validate_published_tool_examples()
    print(
        json.dumps(
            {
                "status": "PASS",
                "tool_examples": len(EXAMPLES),
                "cli_examples": len(COMMANDS),
                "published_cli_examples": published_examples,
                "published_tool_examples": published_tools,
                "guides": list(SKILL_NAMES),
            }
        )
    )


if __name__ == "__main__":
    main()
