# Baseline API: checked against clef-use 0.1.29 source

These are logical tool names, not client-specific namespace strings.
Use the current session's advertised schemas before submitting arguments.

| Tool | Purpose |
|---|---|
| `computer_run` | Bounded GUI goal; supports input-free `ASSESS` mode |
| `computer_continue` | Resume the identified escalated session with new guidance |
| `computer_observe` | Fresh idle observation by default; optional returned image |
| `computer_status` | Read status without starting another goal |
| `computer_abort` | Cancel and release runtime-owned input |

## Read fresh current evidence

```json
{"include_image": true, "refresh": true}
```

Send to the actually exposed `computer_observe`. For recorded evidence use
`refresh: false`, but do not treat it as a fresh screenshot.

## Input-free assessment

```json
{
  "goal": "Determine whether the Blender File menu is visibly open",
  "success_conditions": ["The File menu is visibly open in Blender"],
  "execution_mode": "ASSESS",
  "max_steps": 4
}
```

Assessment can be uncertain or fail. Do not alter the desktop to make it true
unless the user asked for that change in a separate authorized goal.

## A bounded task in an already prepared, non-sensitive fixture

```json
{
  "goal": "In the open Calculator, compute 123 * 456",
  "success_conditions": ["Calculator shows 56088"],
  "constraints": ["Do not close unrelated applications"],
  "max_steps": 20
}
```

Only use this as a smoke test in an appropriate desktop when the user authorized
input. Setup verification should use status/capabilities first, not this task.

## Exact text

`text_inputs` carries literal values and optional `target_label`. Inspect its
schema; do not put a command or arbitrary code into a text field to bypass a
missing runtime capability. `pointer_inputs` needs real observation-bound data,
not a guessed frame hash. `visual_intent` is constrained by the installed backend.

## Newer releases

A capability tool or registered operation request may be available in newer
releases. Use it only when advertised. Examples for new operations must come
from the installed schema/registry, not from guessed argument names.
