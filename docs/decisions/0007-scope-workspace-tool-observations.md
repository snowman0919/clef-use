# Scope configured workspace tool observations

Status: accepted software contract, 2026-10-12.

The State Compiler supports `active_tool`, but the optional Blender observer
previously supplied no tool evidence. Public workspace tool references describe
configured tools by editor space and context mode; they do not identify the
focused editor or prove effective input dispatch.

The read-only collector retains initialized workspace tool references, refusing
more than 128 rather than truncating them. It reads `Context.mode` only when the
native context window, workspace and view layer match the owning window. The
provider requires exactly one nonempty VIEW_3D tool for that mode and complete,
unique, process-bound VIEW_3D area identities. `active_tool` carries this scope
explicitly, including UNKNOWN focused editor and effective dispatch. Missing,
ambiguous or malformed evidence stays UNKNOWN. Other operation guards retain
their independent requirements.

Alternatives: deriving context mode from `Object.mode` loses distinctions such
as EDIT versus EDIT_MESH. Treating all retained references as the current tool
confuses configuration across modes. Context overrides, tool creation or refresh
would change the passive collector contract. Guessing focus from a tool reference
would authorize input without evidence.

Costs: uninitialized tools, foreign contexts and unsupported editor spaces cannot
produce this fact. Multiple VIEW_3D areas share a workspace configuration; the
fact preserves all observed area IDs instead of selecting one. Consumers needing
focused-tool dispatch must obtain separate fresh evidence. This observation alone
does not make an operation ready. Native verification and its limits are recorded
separately in `docs/EXECUTION_STATUS.md`.
