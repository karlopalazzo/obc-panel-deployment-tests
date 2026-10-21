import subprocess
import sys
import time
from pathlib import Path

import pytest

from satellite.persistence import load_simulator, reset_simulator, save_simulator


def _run_script(script: str, panel_index: int, env: dict[str, str]) -> str:
    root = Path(__file__).resolve().parents[2]
    path = root / "obc" / "scripts" / script
    result = subprocess.run(
        [sys.executable, str(path), f"--panelIndex={panel_index}"],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    return result.stdout.strip()


@pytest.fixture
def obc_env(tmp_path, monkeypatch):
    path = tmp_path / "simulator.json"
    monkeypatch.setenv("OBC_STATE_PATH", str(path))
    reset_simulator()
    sim = load_simulator()
    sim.nominal_switch_press_delay_ms = 800
    save_simulator(sim)
    import os

    env = {**os.environ, "OBC_STATE_PATH": str(path)}
    yield env


@pytest.mark.unit
def test_scripts_happy_path(obc_env):
    assert _run_script("releasePanel.py", 2, obc_env) == "TRUE"
    assert _run_script("getReleaseStatus.py", 2, obc_env) == "FALSE"
    time.sleep(0.85)
    assert _run_script("getReleaseStatus.py", 2, obc_env) == "TRUE"
