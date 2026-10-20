import time

import pytest

from satellite.faults import FaultProfile
from satellite.models import HDRMState, SatelliteSimulator, SwitchState


@pytest.mark.unit
def test_release_panel_happy_path_switch_presses_after_delay():
    sim = SatelliteSimulator.with_panels((1,))
    sim.nominal_switch_press_delay_ms = 50

    assert sim.release_panel(1) is True
    assert sim.get_release_status(1) is False

    time.sleep(0.08)
    assert sim.get_release_status(1) is True


@pytest.mark.unit
def test_power_module_reject_returns_false_and_switch_stays_unpressed():
    sim = SatelliteSimulator.with_panels((1,))
    sim.faults = FaultProfile(power_module_rejects_release=True)

    assert sim.release_panel(1) is False
    assert sim.panels[1].hdrm.state == HDRMState.HOLDING
    assert sim.get_release_status(1) is False


@pytest.mark.unit
def test_delayed_switch_exceeds_two_second_budget():
    sim = SatelliteSimulator.with_panels((2,))
    sim.nominal_switch_press_delay_ms = 0
    sim.faults = FaultProfile(switch_press_delay_ms=2500)

    assert sim.release_panel(2) is True
    time.sleep(0.05)
    assert sim.get_release_status(2) is False


@pytest.mark.unit
def test_partial_deployment_only_requested_panel():
    sim = SatelliteSimulator.with_panels((1, 2))
    sim.nominal_switch_press_delay_ms = 10

    assert sim.release_panel(1) is True
    time.sleep(0.05)

    assert sim.get_release_status(1) is True
    assert sim.get_release_status(2) is False
    assert sim.panels[2].deployment_switch.state == SwitchState.UNPRESSED
