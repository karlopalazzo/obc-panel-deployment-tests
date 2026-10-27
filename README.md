# OBC panel deployment tests

Portfolio project for satellite flight-software V&V: deploy solar panels via HDRM,
confirm deployment with switches, tested through OBC scripts over SSH.

## Architecture (layers)

```
pytest  →  SatelliteClient (SSH)  →  releasePanel.py / getReleaseStatus.py
                                              ↓
                                    persistence (simulator.json)
                                              ↓
                                    SatelliteSimulator (SIL model)
```

| Layer | Responsibility |
|-------|----------------|
| **Tests** | Unit: model, script subprocesses, fault injection. Integration: SSH, 2 s deploy timeout, invalid panel index |
| **Client** (`ssh_client.py`) | `release_panel()`, `get_release_status()`, `wait_for_deployment()`, `release_and_wait()`, `reset_simulator()` — same API for SIL and planned HIL |
| **OBC scripts** | CLI (`--panelIndex=1..4`, stdout `TRUE`/`FALSE`) |
| **Persistence** | Load/save simulator state between script processes (`OBC_STATE_PATH`) |
| **Simulator** | Panels, HDRM, deployment switches, `FaultProfile` for SIL negatives |

SIL today: Docker OBC on `localhost:2222`. HIL (e.g. Raspberry Pi with the same scripts) is planned, not implemented yet.

## Domain model

- **`releasePanel.py`** — `TRUE` means the **Power Module confirmed** the HDRM trigger, not that the panel is fully deployed.
- **`getReleaseStatus.py`** — `TRUE` means the **deployment switch is pressed** (panel at final position).

Valid panel indices are **1–4**. Other indices yield `FALSE` from the OBC scripts (no Python exception at script level).

One HDRM and one deployment switch per panel for now; redundant HDRMs per panel are a future extension on `Panel`.

## Status

- [x] Domain simulator + unit tests
- [x] OBC scripts + Docker SIL (SSH)
- [x] Integration tests (pytest + paramiko)
- [ ] CCSDS telemetry module (unit tests)
- [ ] CI (GitHub Actions)
- [ ] Design notes (SIL/HIL scalability, traceability table)

## Project layout

```text
src/satellite/          models, faults, persistence, ssh_client
obc/scripts/            OBC CLI scripts (also copied into Docker image)
docker/                 Dockerfile, entrypoint
tests/unit/             simulator, OBC scripts via subprocess
tests/integration/      SSH against running container
```

## Run tests

Install dev dependencies (pytest, paramiko):

```bash
pip install -e ".[dev]"
```

Unit tests only (no Docker):

```bash
pytest tests/unit -m unit
```

Integration tests (requires OBC container):

```bash
docker compose up -d
pytest tests/integration -m integration
```

Run all tests (integration is skipped if port 2222 is unreachable):

```bash
pytest
```

Before each integration test, the client calls `reset_simulator()` over SSH for a clean SIL state.

## SIL OBC (Docker + SSH)

Build and start (SSH on **localhost:2222**, user `obc`, password `password123`):

```bash
docker compose up --build -d
```

Manual check via SSH (Git Bash / WSL / Linux):

```bash
ssh -p 2222 obc@localhost "python3 /opt/scripts/releasePanel.py --panelIndex=1"
ssh -p 2222 obc@localhost "python3 /opt/scripts/getReleaseStatus.py --panelIndex=1"
```

Without SSH (e.g. PowerShell):

```bash
docker compose exec obc python3 /opt/scripts/releasePanel.py --panelIndex=1
docker compose exec obc python3 /opt/scripts/getReleaseStatus.py --panelIndex=1
```

Each script run is a **new process**; simulator state is stored in `/var/lib/obc/simulator.json` inside the container.

Optional SIL faults via `docker-compose.yml` environment variables (applied when the state file is first created):

| Variable | Effect |
|----------|--------|
| `OBC_FAULT_PM_REJECT=true` | `releasePanel` prints FALSE |
| `OBC_FAULT_HDRM_NOOP=true` | release TRUE but HDRM does not fire |
| `OBC_FAULT_SWITCH_DELAY_MS=3000` | slow switch press (regression >2s) |
| `OBC_FAULT_DROP_RELEASE=true` | release fails (command dropped) |
| `OBC_FAULT_FLIP_SWITCH_READ=true` | alternating FALSE/TRUE on status polls |

Reset state: `docker compose exec obc python3 -c "from satellite.persistence import reset_simulator; reset_simulator()"`, or recreate the container.

## Integration test coverage

| Test | What it checks |
|------|----------------|
| Parametrized panels 1–4 | `release_and_wait` completes within 2 s |
| `release_panel(5)` | Returns `FALSE` for invalid panel index |
| `release_and_wait(5)` | Raises `RuntimeError` (helper fails fast) |

SSH connection overrides: `OBC_SSH_HOST`, `OBC_SSH_PORT`, `OBC_SSH_USER`, `OBC_SSH_PASSWORD`.

## Unit test coverage (summary)

- HDRM release, PM reject, delayed switch, partial multi-panel deployment
- OBC scripts via subprocess with shared `OBC_STATE_PATH` (multi-process behaviour)
