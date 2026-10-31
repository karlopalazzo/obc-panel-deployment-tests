# Design notes — OBC panel deployment tests

This document describes verification strategy, scalability, and traceability for the portfolio project. It complements the README (how to run) with **why** the architecture looks this way.

## Goals

1. Test **panel deployment** through the same **OBC script interface** used in SIL (and planned HIL): `releasePanel.py` / `getReleaseStatus.py` over SSH.
2. Keep **pytest** tests readable for V&V: timeouts, parametrized panels, negative cases, separate unit vs integration markers.
3. Provide a **standalone CCSDS Space Packet** module for binary telemetry V&V (not yet wired to the OBC deploy path).
4. Support **repeatable SIL** in Docker and **future HIL** by swapping SSH target configuration only.

## Verification vs validation

| Term | Meaning in this project |
|------|-------------------------|
| **Verification** | Does the implementation match the specified behaviour? Examples: after accepted release, switch reads TRUE within 2 s; invalid panel index returns FALSE; CCSDS packet length matches buffer. |
| **Validation** | Does the system meet the mission need? This repo does not validate real flight worthiness; it models one OBC interface and test criteria suitable for a portfolio / exercise. |

Tests in this repository are **verification** artefacts. Traceability links requirements to test cases below.

## Architecture (summary)

```text
pytest  →  SatelliteClient (SSH)  →  OBC scripts  →  persistence  →  SatelliteSimulator
```

- **Integration tests** must not import `SatelliteSimulator` directly; they exercise the **operational interface** (SSH + scripts).
- **Unit tests** may target the simulator, persistence, scripts via subprocess, and CCSDS pack/unpack in isolation.

## SIL vs HIL

| Environment | Today | Planned |
|-------------|-------|---------|
| **SIL** | Docker OBC, `localhost:2222`, state in `/var/lib/obc/simulator.json` | Same; used in CI |
| **HIL** | Not implemented | Raspberry Pi (or lab OBC) with identical scripts; `SatelliteClient` configured via `OBC_SSH_*` env vars |

The **same** `SatelliteClient` API (`release_panel`, `wait_for_deployment`, `release_and_wait`) applies to both; only host/port and credentials change.

## Scalability

### Panel count

- Panels are keyed by integer index (default **1–4**). Tests use `@pytest.mark.parametrize` over panel indices.
- Adding panel 5+ is a **configuration change** in `SatelliteSimulator.with_panels(...)` and documentation; script CLI already accepts an integer index.

### Redundant HDRM per panel

- Current model: **one HDRM + one deployment switch per panel**.
- Future: replace `Panel.hdrm` with a collection and define release policy (e.g. both must fire). Tests should remain parametrized by panel id; simulator encapsulates redundancy rules.

### CCSDS and ground segment

- `satellite.telemetry` implements **Space Packet** primary header only.
- **PUS** (services) and **CSP** (routing) are out of scope until a ground segment or TC/TM path is modelled realistically (telecommand bytes, not script source in payload).
- CCSDS remains **decoupled** from SIL deploy until that design is specified.

## Negative testing and fault injection

SIL faults are configured via environment variables when the simulator state file is first created (`OBC_FAULT_*` in `docker-compose.yml`). Examples:

- Power module rejects release → `releasePanel` returns FALSE.
- Delayed switch press → deployment exceeds 2 s timeout in integration tests.
- Alternating status reads → inconsistent polling behaviour.

This supports regression scenarios without changing pytest code.

## Requirements traceability

| ID | Requirement (summary) | Test evidence |
|----|------------------------|---------------|
| REQ-DEP-01 | After accepted release, deployment switch TRUE within 2 s | `test_panel_deploys_within_two_seconds_after_release` |
| REQ-DEP-02 | Invalid panel index → release not accepted (FALSE) | `test_nonexistent_panel_release_returns_false` |
| REQ-DEP-03 | Helper fails fast on invalid panel | `test_nonexistent_panel_release_raises_error_using_helper` |
| REQ-TM-01 | Space Packet header encodes APID and sequence | `test_pack_unpack_roundtrip`, `test_known_header_hex` |
| REQ-TM-02 | Truncated telemetry buffer rejected | `test_truncated_buffer_raises`, `test_truncated_user_data_raises` |

## CI

GitHub Actions workflow `.github/workflows/ci.yml`:

1. **Unit job** — `pytest tests/unit -m unit` on every push/PR to `main`.
2. **Integration job** — builds and starts `docker compose`, waits for port 2222, runs `pytest tests/integration -m integration`.

Integration failures attach OBC container logs in the workflow log.

## Known limitations

- No real radio link, encryption, or multi-segment CCSDS chains.
- No PUS service layer or mission-specific APID catalogue beyond test constants.
- CLI scripts and simulator state use simplified TRUE/FALSE semantics aligned with the portfolio scenario, not a specific flight database.
- C/C++ flight software is not included; tests assume Python scripts on the OBC.

## Future work

- HIL on Raspberry Pi with GPIO stand-in for deployment switch.
- GitLab CI mirror (Scanway stack) if needed for interviews.
- Optional TM/TC path integrated with the same command semantics as CLI scripts (realistic telecommand payload, not embedded script source).
- Extended traceability export (CSV / ReqIF) for formal V&V tooling.
