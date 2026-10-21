from dataclasses import dataclass, field


@dataclass
class FaultProfile:
    """Injectable faults for SIL negative tests and slow-deployment scenarios."""

    # releasePanel.py never reaches the simulator (command fails to send).
    drop_release_command: bool = False
    # Power Module does not confirm the HDRM trigger (script prints FALSE).
    power_module_rejects_release: bool = False
    # HDRM accepts trigger but mechanism does not fire.
    hdrm_trigger_noop: bool = False
    # Extra delay before the deployment switch reads as pressed (milliseconds).
    switch_press_delay_ms: float = 0.0
    # If set, odd/even polls return opposite values (inconsistent feedback).
    flip_switch_on_alternate_read: bool = False

    @classmethod
    def none(cls) -> "FaultProfile":
        return cls()


@dataclass
class RuntimeFaultState:
    """Mutable counters used while simulating (e.g. alternating reads)."""

    release_status_poll_count: dict[int, int] = field(default_factory=dict)
