# OBC panel deployment tests

Portfolio project for satellite flight-software V&V: deploy solar panels via HDRM,
confirm deployment with switches, tested through OBC scripts over SSH.

## Architecture (layers)

```
pytest  →  SatelliteClient (SSH)  →  releasePanel.py / getReleaseStatus.py  →  SatelliteSimulator
              ↑ SIL: Docker OBC              ↑ same scripts in HIL: real Raspberry Pi OBC
```

| Layer | Responsibility |
|-------|----------------|
| **Tests** | Timeouts (2 s), parametrized panels, negative cases, future CCSDS telemetry |
| **Client** | `release_panel()`, poll `get_release_status()` — identical for SIL and HIL |
| **OBC scripts** | CLI (`--panelIndex=1..4`, stdout `TRUE`/`FALSE`) |
| **Simulator** | Panels, HDRM, deployment switches, fault injection |

## Domain model

- **`releasePanel.py`** — `TRUE` means the **Power Module confirmed** the HDRM trigger, not that the panel is fully deployed.
- **`getReleaseStatus.py`** — `TRUE` means the **deployment switch is pressed** (panel at final position).

One HDRM and one switch per panel for now; redundant HDRMs per panel are a future extension on `Panel`.

## Status

- [x] Domain simulator + unit tests
- [x] OBC scripts + Docker SIL (SSH)
- [ ] Integration tests (pytest + paramiko)
- [ ] CI, CCSDS telemetry module, design notes (SIL/HIL scalability)

## Run unit tests

```bash
pip install -e ".[dev]"
pytest tests/unit -m unit
```

## SIL OBC (Docker + SSH)

Build and start (SSH on **localhost:2222**, user `obc`, password `password123`):

```bash
docker compose up --build -d
```

Manual check (Git Bash / WSL / Linux):

```bash
ssh -p 2222 obc@localhost "python3 /opt/scripts/releasePanel.py --panelIndex=1"
ssh -p 2222 obc@localhost "python3 /opt/scripts/getReleaseStatus.py --panelIndex=1"
```

Each script run is a **new process**; simulator state is stored in `/var/lib/obc/simulator.json` inside the container.

Optional SIL faults via `docker-compose.yml` environment variables:

| Variable | Effect |
|----------|--------|
| `OBC_FAULT_PM_REJECT=true` | `releasePanel` prints FALSE |
| `OBC_FAULT_HDRM_NOOP=true` | release TRUE but HDRM does not fire |
| `OBC_FAULT_SWITCH_DELAY_MS=3000` | slow switch press (regression >2s) |
| `OBC_FAULT_DROP_RELEASE` | release fails (command dropped) |
| `OBC_FAULT_FLIP_SWITCH_READ` | alternating FALSE/TRUE on status polls |

Reset state: `docker compose down -v` and up again, or delete `simulator.json` in the container.
