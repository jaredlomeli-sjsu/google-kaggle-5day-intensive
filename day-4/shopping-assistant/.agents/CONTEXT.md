# Local Project Context & Secure Coding Standards

## Core Paved Roads
1. **Tool Input Validation**: Agent tools must validate parameters against Pydantic schemas, not raw dictionaries.
2. **No Shell Execution**: Avoid `run_command` unless explicitly approved by `hooks.json`.
3. **Pre-Commit Remediation Loop**: Treat pre-commit hook failures as refactoring tasks; apply fixes, test, retry commit.

## TDD Planning Gate
During Plan phase, decompose tasks into logical stages.
Every plan MUST include **Security Boundaries & Assertions** section outlining exploitable edge cases.
