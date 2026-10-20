# OBC panel deployment tests

Portfolio project based on a satellite flight-software test exercise: deploy solar panels via HDRM,
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
| **OBC scripts** | CLI compatible with the exercise (`--panelIndex=1..4`, stdout `TRUE`/`FALSE`) |
| **Simulator** | Panels, HDRM, deployment switches, fault injection |

## Domain model (OBC script semantics)

- **`releasePanel.py`** — `TRUE` means the **Power Module confirmed** the HDRM trigger, not that the panel is fully deployed.
- **`getReleaseStatus.py`** — `TRUE` means the **deployment switch is pressed** (panel at final position).

One HDRM and one switch per panel for now; redundant HDRMs per panel are a future extension on `Panel`.

## Status

- [x] Domain simulator + unit tests
- [ ] Docker OBC + SSH scripts
- [ ] Integration tests (pytest + paramiko)
- [ ] CI, CCSDS telemetry module, written answers for Q2/Q3

## Run unit tests

```bash
pip install -e ".[dev]"
pytest tests/unit -m unit
```
