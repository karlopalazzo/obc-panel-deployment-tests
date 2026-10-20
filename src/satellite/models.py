from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from time import monotonic

from satellite.faults import FaultProfile, RuntimeFaultState

# ICEYE task: panelIndex is 1..4 (1-based).
DEFAULT_PANEL_INDICES = (1, 2, 3, 4)


class HDRMState(Enum):
    HOLDING = auto()
    RELEASED = auto()
    FAILED = auto()


class SwitchState(Enum):
    UNPRESSED = auto()
    PRESSED = auto()


@dataclass
class HDRM:
    """Hold-Down Release Mechanism — holds the panel until triggered."""

    state: HDRMState = HDRMState.HOLDING

    def is_holding(self) -> bool:
        return self.state == HDRMState.HOLDING

    def release(self) -> None:
        if self.state == HDRMState.FAILED:
            return
        self.state = HDRMState.RELEASED


@dataclass
class DeploymentSwitch:
    """Feedback at end of panel travel (TRUE = switch pressed)."""

    state: SwitchState = SwitchState.UNPRESSED

    def is_pressed(self) -> bool:
        return self.state == SwitchState.PRESSED

    def press(self) -> None:
        self.state = SwitchState.PRESSED


@dataclass
class Panel:
    """
    One deployable solar panel.

    Current config: exactly one HDRM and one deployment switch per panel.
    Future: panel.hdrms: tuple[HDRM, ...] with redundant release logic.
    """

    index: int
    hdrm: HDRM = field(default_factory=HDRM)
    deployment_switch: DeploymentSwitch = field(default_factory=DeploymentSwitch)

    # Simulator clock: when switch should become pressed after successful release.
    _switch_press_deadline: float | None = field(default=None, repr=False)

    def schedule_switch_press_after_ms(self, delay_ms: float, now: float) -> None:
        self._switch_press_deadline = now + delay_ms / 1000.0

    def tick(self, now: float) -> None:
        if (
            self._switch_press_deadline is not None
            and now >= self._switch_press_deadline
            and self.hdrm.state == HDRMState.RELEASED
        ):
            self.deployment_switch.press()
            self._switch_press_deadline = None


@dataclass
class SatelliteSimulator:
    """
    Behavioral model behind OBC scripts in SIL.

    Not the pytest-facing API — tests talk to releasePanel.py / getReleaseStatus.py
    over SSH; those scripts call into this object.
    """

    panels: dict[int, Panel] = field(default_factory=dict)
    faults: FaultProfile = field(default_factory=FaultProfile.none)
    _runtime: RuntimeFaultState = field(default_factory=RuntimeFaultState)
    # Time for panel mechanics after HDRM release until switch is pressed.
    nominal_switch_press_delay_ms: float = 200.0

    @classmethod
    def with_panels(cls, indices: tuple[int, ...] = DEFAULT_PANEL_INDICES) -> SatelliteSimulator:
        return cls(panels={i: Panel(index=i) for i in indices})

    def tick(self) -> None:
        now = monotonic()
        for panel in self.panels.values():
            panel.tick(now)

    def release_panel(self, panel_index: int) -> bool:
        """
        Implements semantics of releasePanel.py output.

        TRUE  = Power Module confirmed the HDRM trigger request.
        FALSE = command not accepted / PM did not confirm.
        """
        if self.faults.drop_release_command:
            return False

        panel = self._panel(panel_index)
        if panel is None:
            return False

        if self.faults.power_module_rejects_release:
            return False

        if self.faults.hdrm_trigger_noop:
            return True

        panel.hdrm.release()
        delay = self.nominal_switch_press_delay_ms + self.faults.switch_press_delay_ms
        panel.schedule_switch_press_after_ms(delay, monotonic())
        return True

    def get_release_status(self, panel_index: int) -> bool:
        """
        Implements semantics of getReleaseStatus.py output.

        TRUE  = deployment switch pressed (panel at final position).
        FALSE = switch still unpressed.
        """
        self.tick()

        panel = self._panel(panel_index)
        if panel is None:
            return False

        pressed = panel.deployment_switch.is_pressed()

        if self.faults.flip_switch_on_alternate_read:
            count = self._runtime.release_status_poll_count.get(panel_index, 0)
            self._runtime.release_status_poll_count[panel_index] = count + 1
            if count % 2 == 1:
                pressed = not pressed

        return pressed

    def _panel(self, panel_index: int) -> Panel | None:
        return self.panels.get(panel_index)
