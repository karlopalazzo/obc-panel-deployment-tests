from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from satellite.faults import FaultProfile, RuntimeFaultState
from satellite.models import (
    DEFAULT_PANEL_INDICES,
    DeploymentSwitch,
    HDRM,
    HDRMState,
    Panel,
    SatelliteSimulator,
    SwitchState,
)

DEFAULT_STATE_PATH = Path("/var/lib/obc/simulator.json")


def _faults_from_env() -> FaultProfile:
    """Reads Docker compose"""
    def flag(name: str) -> bool:
        return os.environ.get(name, "").lower() in ("1", "true", "yes")

    delay = float(os.environ.get("OBC_FAULT_SWITCH_DELAY_MS", "0") or "0")
    return FaultProfile(
        drop_release_command=flag("OBC_FAULT_DROP_RELEASE"),
        power_module_rejects_release=flag("OBC_FAULT_PM_REJECT"),
        hdrm_trigger_noop=flag("OBC_FAULT_HDRM_NOOP"),
        switch_press_delay_ms=delay,
        flip_switch_on_alternate_read=flag("OBC_FAULT_FLIP_SWITCH_READ"),
    )


def simulator_to_dict(sim: SatelliteSimulator) -> dict[str, Any]:
    """SatelliteSimulator() Python object → dict → then JSON"""
    panels: dict[str, Any] = {}
    for index, panel in sim.panels.items():
        panels[str(index)] = {
            "hdrm": panel.hdrm.state.name,
            "switch": panel.deployment_switch.state.name,
            "switch_press_deadline": panel._switch_press_deadline,
        }
    return {
        "version": 1,
        "nominal_switch_press_delay_ms": sim.nominal_switch_press_delay_ms,
        "faults": {
            "drop_release_command": sim.faults.drop_release_command,
            "power_module_rejects_release": sim.faults.power_module_rejects_release,
            "hdrm_trigger_noop": sim.faults.hdrm_trigger_noop,
            "switch_press_delay_ms": sim.faults.switch_press_delay_ms,
            "flip_switch_on_alternate_read": sim.faults.flip_switch_on_alternate_read,
        },
        "runtime": {
            "release_status_poll_count": sim._runtime.release_status_poll_count,
        },
        "panels": panels,
    }


def simulator_from_dict(data: dict[str, Any]) -> SatelliteSimulator:
    """JSON → dict → SatelliteSimulator() Python object"""
    faults_data = data.get("faults", {})
    faults = FaultProfile(
        drop_release_command=faults_data.get("drop_release_command", False),
        power_module_rejects_release=faults_data.get("power_module_rejects_release", False),
        hdrm_trigger_noop=faults_data.get("hdrm_trigger_noop", False),
        switch_press_delay_ms=float(faults_data.get("switch_press_delay_ms", 0)),
        flip_switch_on_alternate_read=faults_data.get("flip_switch_on_alternate_read", False),
    )
    runtime_data = data.get("runtime", {})
    runtime = RuntimeFaultState(
        release_status_poll_count={
            int(k): int(v) for k, v in runtime_data.get("release_status_poll_count", {}).items()
        }
    )
    panels: dict[int, Panel] = {}
    for key, pdata in data.get("panels", {}).items():
        index = int(key)
        panel = Panel(index=index)
        panel.hdrm.state = HDRMState[pdata["hdrm"]]
        panel.deployment_switch.state = SwitchState[pdata["switch"]]
        panel._switch_press_deadline = pdata.get("switch_press_deadline")
        panels[index] = panel
    return SatelliteSimulator(
        panels=panels,
        faults=faults,
        _runtime=runtime,
        nominal_switch_press_delay_ms=float(data.get("nominal_switch_press_delay_ms", 200.0)),
    )


def state_path() -> Path:
    """Get state path from env or get default state."""
    return Path(os.environ.get("OBC_STATE_PATH", str(DEFAULT_STATE_PATH)))


def load_simulator() -> SatelliteSimulator:
    path = state_path()
    if not path.is_file():
        sim = SatelliteSimulator.with_panels(DEFAULT_PANEL_INDICES)
        sim.faults = _faults_from_env()
        return sim
    data = json.loads(path.read_text(encoding="utf-8"))
    sim = simulator_from_dict(data)
    # Env faults apply on fresh container start; keep stored faults when state file exists.
    return sim


def save_simulator(sim: SatelliteSimulator) -> None:
    """Create catlogs, save JSON with indentation."""
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(simulator_to_dict(sim), indent=2), encoding="utf-8")


def reset_simulator() -> SatelliteSimulator:
    """Remove the simulator file, clear the faults from env, save - for clean start."""
    path = state_path()
    if path.is_file():
        path.unlink()
    sim = SatelliteSimulator.with_panels(DEFAULT_PANEL_INDICES)
    sim.faults = _faults_from_env()
    save_simulator(sim)
    return sim
