---
name: git-main-guard
description: Intercepts git add/commit requests on the main branch. Use this skill when a user asks to add and commit changes to the codebase, specifically to prevent direct commits to the main or master branch by creating a new feature branch instead.
---

# Git Main Guard

## Overview
This skill ensures that changes are never committed directly to the `main` or `master` branch. When a user requests a `git add` and `git commit` while on a protected branch, the skill redirects the workflow to create a new branch first.

## Protected Branches
- `main`
- `master`

## Workflow

When the user asks to `git add` and `git commit`:

1. **Check Current Branch**: Run `git branch --show-current` to identify the current branch.
2. **Branch Guard Logic**:
   - If the current branch is **NOT** `main` or `master`, proceed with the user's request as normal.
   - If the current branch **IS** `main` or `master`:
     a. **Generate Branch Name**: Create a descriptive branch name based on the commit message or the changes being made (e.g., `feat/add-login-system` or `fix/issue-123`).
     b. **Create and Switch**: Run `git checkout -b <new-branch-name>`.
     c. **Execute Original Request**: Run the `git add` and `git commit` commands on the new branch.
     d. **Notify User**: Inform the user that you've created a new branch to avoid committing directly to the protected branch.

## Example Scenario

**User**: "git add . and commit 'add user profile page'"
**Current Branch**: `main`

**Action**:
1. Check branch: `main`
2. Generate branch name: `feature/user-profile-page`
3. Command: `git checkout -b feature/user-profile-page`
4. Command: `git add .`
5. Command: `git commit -m "add user profile page"`
6. Response: "I've created a new branch `feature/user-profile-page` and committed your changes there to keep the `main` branch clean."
