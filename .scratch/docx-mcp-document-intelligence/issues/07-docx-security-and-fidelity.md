# 07: Add DOCX security scanning and fidelity validation

**What to build:** An LLM can statically assess a DOCX/DOCM package with `docx_security_scan` and `docx_validate`, receiving transparent findings for macros, embedded/active content, external relationships, package integrity, and unsupported or lossy features.

**Non-goals:** Macro execution, OLE/ActiveX execution, decryption, automatic remediation, or mutation of risky files.

**Blocked by:** 01: Establish DOCX service foundation.

**Status:** ready-for-agent

**Affected backend areas:** DOCX package inspector; security finding/risk model; built-in MCP DOCX tools; audit logging and error handling.

**Tests:** DOCX/DOCM security fixtures; embedded-object/external-relationship tests; malformed OOXML fixtures; risk-level determinism and no-execution regression tests.

- [ ] `docx_security_scan` reports macros, ActiveX/OLE objects, embedded binaries, external templates/relationships, suspicious URLs, protection, and encryption indicators when detectable.
- [ ] Findings include contributing evidence, a transparent risk level, and a recommended safe action.
- [ ] `docx_validate` distinguishes invalid packages from valid packages containing unsupported or fidelity-risking features.
- [ ] Tests prove static inspection never executes, opens, or follows active document content.
