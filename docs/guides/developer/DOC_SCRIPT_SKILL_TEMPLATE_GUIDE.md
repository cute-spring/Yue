# Doc Script Skill Template Guide

## Purpose

This guide standardizes how to build reusable "document plus script" skills.

## Directory Conventions

- `references/`: knowledge docs and schema references.
- `scripts/`: executable scripts for runtime actions.
- `templates/`: sample output structures and starter files.
- `libraries/`: optional external assets used by scripts.
- `actions`: declared in `manifest.yaml` and mapped to scripts.

## Required Fields

Minimum required fields for `manifest.yaml.example`:

- `name`
- `version`
- `entrypoint`
- `actions`
- `input_schema`
- `output_schema`

## Minimal Runnable Example

1. Create `SKILL.md` with capability levels and action descriptions.
2. Add one script under `scripts/`.
3. Declare one action in `manifest.yaml` with approval policy and schemas.
4. Produce an artifact path in `output_schema` as `output_file_path`.

## Migration Steps

1. Start from read-only mode with `references/` and `templates/`.
2. Add script execution in `scripts/` and wire action descriptors.
3. Add schema validation and approval gate for every action.
4. Add unit tests for success and failure paths before rollout.
