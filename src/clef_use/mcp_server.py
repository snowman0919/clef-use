import asyncio
import json

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent, TextContent

from .client import RuntimeClient
from .config import load_config
from .schema import Contract, PointerInput, SessionResult, TextInput, VisualIntent
from .update_notice import startup_update_request


def create_server(client=None, update_request=""):
    client = client or RuntimeClient()
    server = FastMCP(
        "clef-use",
        instructions=(
            "Submit bounded GUI goals to computer_run. The local runtime owns all "
            "inner-loop actions. Observe after preparation to inspect fresh pixels "
            "before supplying paths, or after escalation. Use observe refresh=False for "
            "recorded diagnostic evidence, not fresh input/completion proof. "
            "Continue resumes escalation; "
            "abort stops input." + (" " + update_request if update_request else "")
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
        )
        result = await asyncio.to_thread(client.request, "run", **contract.model_dump(mode="json"))
        try:
            return SessionResult.model_validate(await asyncio.to_thread(client.wait, result))
        except asyncio.CancelledError:
            await asyncio.to_thread(client.request, "abort", session_id=result["session_id"])
            raise

    @server.tool()
    async def computer_continue(session_id: str, instruction: str) -> SessionResult:
        """Resume an escalated session with additional planner guidance and remaining budget."""
        result = await asyncio.to_thread(
            client.request, "continue", session_id=session_id, instruction=instruction
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

    @server.tool()
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

    return server


def main():
    create_server(update_request=startup_update_request()).run(transport="stdio")
