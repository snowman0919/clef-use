import asyncio
import json
import os
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent, TextContent, ToolAnnotations
from pydantic import Field

from .client import RuntimeClient
from .config import load_config
from .operations import OperationRequest, operation_registry
from .schema import Contract, PointerInput, SessionResult, TextInput, VisualIntent
from .update_notice import startup_update_request


def create_server(client=None, update_request="", read_only=False):
    client = client or RuntimeClient(start=not read_only)
    operation_ids = [operation["family"] for operation in operation_registry()]
    server = FastMCP(
        "clef-use",
        instructions=(
            "Use clef-use only for user-authorized GUI work or explicit requests about "
            "clef-use capabilities and schemas. Do not invoke it for ordinary code-only "
            "questions or when the user forbids runtime access. These instructions "
            "apply only after the task selects clef-use. Load the applicable installed "
            "Agent Skill before invoking runtime tools. "
            + (
                "This read-only connection exposes computer_capabilities and "
                "computer_status. Use computer_capabilities to discover versions, "
                "supported operations and schemas without a running GUI service. "
                "Schema/guide resources are also advertised; use an actually discovered "
                "harness reader and preserve the exact resource URI. Do not invent "
                "resource addresses or aliases. computer_status reads an "
                "existing runtime session and does not start a service; it is not "
                "capability or Blender-state discovery. This connection cannot capture, "
                "run, continue or abort GUI work."
                if read_only
                else "Submit bounded GUI goals to computer_run. The local runtime owns all "
                "inner-loop actions. Observe after preparation to inspect fresh pixels "
                "before supplying paths, or after escalation. Use observe refresh=False for "
                "recorded diagnostic evidence, not fresh input/completion proof. "
                "Continue resumes escalation; "
                "abort stops input. Discover current schemas and registered operations with "
                "computer_capabilities before using a newer guide. ASSESS never sends input. "
                "Only continue/abort your own identified session. WAIT and executed input are "
                "not completion proof; never lower confidence gates to bypass ambiguity."
            )
            + (" " + update_request if update_request else "")
        ),
    )

    @server.tool()
    async def computer_run(
        goal: str,
        success_conditions: list[str] | None = None,
        constraints: list[str] | None = None,
        max_steps: int | None = None,
        confidence_threshold: float | None = None,
        text_inputs: list[TextInput] | None = None,
        pointer_inputs: list[PointerInput] | None = None,
        execution_mode: str = "AUTO",
        visual_intent: VisualIntent | None = None,
        operation: OperationRequest | None = None,
    ) -> SessionResult:
        """Execute a bounded GUI goal; ASSESS verifies it without permitting input."""
        config = load_config()
        contract = Contract(
            goal=goal,
            success_conditions=success_conditions or [],
            constraints=constraints or [],
            max_steps=max_steps if max_steps is not None else config.max_steps,
            confidence_threshold=confidence_threshold
            if confidence_threshold is not None
            else config.confidence_threshold,
            text_inputs=text_inputs or [],
            pointer_inputs=pointer_inputs or [],
            execution_mode=execution_mode,
            visual_intent=visual_intent,
            operation=operation.model_dump(mode="json") if operation else None,
        )
        result = await asyncio.to_thread(client.request, "run", **contract.model_dump(mode="json"))
        try:
            return SessionResult.model_validate(await asyncio.to_thread(client.wait, result))
        except asyncio.CancelledError:
            await asyncio.to_thread(client.request, "abort", session_id=result["session_id"])
            raise

    @server.tool()
    async def computer_continue(
        session_id: str, instruction: str, operation: OperationRequest | None = None
    ) -> SessionResult:
        """Resume an escalated session with additional planner guidance and remaining budget."""
        result = await asyncio.to_thread(
            client.request,
            "continue",
            session_id=session_id,
            instruction=instruction,
            **({"operation": operation.model_dump(mode="json")} if operation else {}),
        )
        try:
            return SessionResult.model_validate(await asyncio.to_thread(client.wait, result))
        except asyncio.CancelledError:
            await asyncio.to_thread(client.request, "abort", session_id=session_id)
            raise

    @server.tool()
    async def computer_observe(
        session_id: str | None = None, include_image: bool = False, refresh: bool = True
    ) -> list:
        """Refresh idle pixels by default; refresh=False reads only recorded session evidence."""
        result = await asyncio.to_thread(
            client.request,
            "observe",
            session_id=session_id,
            include_image=include_image,
            refresh=refresh,
        )
        image = result.pop("image_png", None)
        contents = [TextContent(type="text", text=json.dumps(result))]
        if image:
            contents.append(ImageContent(type="image", data=image, mimeType="image/png"))
        return contents

    @server.tool(
        annotations=ToolAnnotations(
            readOnlyHint=read_only, destructiveHint=False, openWorldHint=False
        )
    )
    async def computer_status(session_id: str | None = None) -> SessionResult:
        """Read session status without starting new GUI work."""
        return SessionResult.model_validate(
            await asyncio.to_thread(client.request, "status", session_id=session_id)
        )

    @server.tool()
    async def computer_abort(session_id: str | None = None) -> SessionResult:
        """Cancel execution and release all runtime-owned input state."""
        return SessionResult.model_validate(
            await asyncio.to_thread(client.request, "abort", session_id=session_id)
        )

    @server.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
        )
    )
    def computer_capabilities(
        detail: bool = False,
        operation_id: Annotated[
            str | None,
            Field(
                description="Exact registered family from operations[].family; omit to discover "
                "IDs. Application names are not operation IDs.",
                json_schema_extra={"enum": [*operation_ids, None]},
            ),
        ] = None,
    ) -> dict:
        """Discover installed product versions, inputs and schemas; no capture/model/input."""
        from .capabilities import capabilities, digest

        result = capabilities(detail=detail, operation_id=operation_id)
        if read_only and operation_id is None:
            schemas = {tool.name: tool.parameters for tool in server._tool_manager.list_tools()}
            result.update(tools=list(schemas), schema_sha256=digest(schemas), read_only_facade=True)
            if detail:
                result["schemas"] = schemas
        return result

    @server.resource("clef-use://api/schema")
    def api_schema() -> str:
        return json.dumps(computer_capabilities(detail=True))

    from .capabilities import SKILL_NAMES, skill_root

    bundle = skill_root().resolve()

    def guide_reader(path):
        def read_guide() -> str:
            if path.is_symlink() or not path.resolve().is_relative_to(bundle):
                raise ValueError("Guide resource escapes installed bundle")
            return path.read_text(encoding="utf-8")

        return read_guide

    for name in SKILL_NAMES:
        root = skill_root() / name
        for path in sorted(root.rglob("*.md")):
            if path.is_symlink() or not path.resolve().is_relative_to(bundle):
                raise ValueError("Guide resource escapes installed bundle")
            uri = f"clef-use://guides/{name}/{path.relative_to(root).as_posix()}"
            server.resource(uri)(guide_reader(path))

    if read_only:
        for name in ("computer_run", "computer_continue", "computer_observe", "computer_abort"):
            server.remove_tool(name)

    return server


def main(read_only=False):
    read_only = read_only or os.environ.get("CLEF_USE_MCP_READ_ONLY") == "1"
    create_server(
        update_request="" if read_only else startup_update_request(), read_only=read_only
    ).run(transport="stdio")
