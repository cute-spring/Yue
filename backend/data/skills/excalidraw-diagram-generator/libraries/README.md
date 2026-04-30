# Excalidraw Icon Libraries

This directory stores split Excalidraw icon libraries used by `excalidraw-diagram-generator`.

## Standard Structure

Each icon set must use this layout:

```text
libraries/<icon-set>/
  <icon-set>.excalidrawlib
  reference.md
  icons/
    <icon-name>.json
```

## Metadata Requirements

Each `reference.md` must include:

- source
- version
- license
- last_updated

## Naming Rules

- Use lowercase kebab-case for `<icon-set>` directories.
- Keep `.excalidrawlib` filename aligned with directory name.
- Keep icon JSON filenames stable for deterministic lookup.

## Import Workflow

1. Download a `.excalidrawlib` file from <https://libraries.excalidraw.com/>.
2. Place it under `libraries/<icon-set>/`.
3. Run:

```bash
python /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/excalidraw-diagram-generator/scripts/split-excalidraw-library.py /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/excalidraw-diagram-generator/libraries/<icon-set>/
```

4. Verify `reference.md` exists and `icons/` contains icon JSON files.
