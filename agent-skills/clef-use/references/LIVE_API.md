# Installed contract examples

API schema version 1; discover the installed runtime first.
These examples do not authorize input. Operations require trusted local state;
missing editor/keymap/selection evidence returns BLOCKED. No 100ms claim is made.

Send to `computer_capabilities`:

```json
{
  "detail": false
}
```

Send to `computer_observe`:

```json
{
  "include_image": true,
  "refresh": true
}
```

Send to `computer_run`:

```json
{
  "goal": "Assess whether the Blender File menu is open",
  "execution_mode": "ASSESS",
  "operation": {
    "family": "menu_assess",
    "menu": "File"
  }
}
```

## CLI

```sh
clef-use capabilities --json
clef-use capabilities --detail --json
clef-use capabilities --operation-id numeric_transform --json
clef-use integrate codex --dry-run
clef-use integrate codex --scope user --skills core --skills blender --skills diagnostics
clef-use integrate hermes --scope user
clef-use integrate omp --scope user
clef-use integrations status --json
clef-use integrations verify codex --live --read-only
clef-use integrations remove codex --dry-run
clef-use integrations refresh --managed-only
```
