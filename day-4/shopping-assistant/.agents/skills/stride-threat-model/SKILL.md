---
name: stride-threat-model
description: Performs systematic STRIDE threat modeling assessment on codebase and architecture.
---

# STRIDE Threat Modeling Skill

## Goal
Analyze workspace structure to produce structured threat_model.md assessment.

## Instructions
1. **Analyze System Boundaries**: Map entry points (tools, workflows, prompts) and data storage.
2. **STRIDE Evaluation**:
   - **Spoofing**: Verify caller identity boundaries before sensitive operations
   - **Tampering**: Check for data flow manipulation vulnerabilities
   - **Repudiation**: Assess transaction logging security
   - **Information Disclosure**: Identify PII/token leakage risks
   - **Denial of Service**: Verify rate limits on expensive queries
   - **Elevation of Privilege**: Check access control bypasses
3. **Output**: Generate threat_model.md in workspace root
