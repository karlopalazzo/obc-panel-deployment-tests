from __future__ import annotations

import os
import time
from dataclasses import dataclass

import paramiko


@dataclass(frozen=True)
class ObcSshConfig:
    host: str = "localhost"
    port: int = 2222
    username: str = "obc"
    password: str = "password123"
    release_script: str = "/opt/scripts/releasePanel.py"
    status_script: str = "/opt/scripts/getReleaseStatus.py"

    @classmethod
    def from_env(cls) -> ObcSshConfig:
        return cls(
            host=os.environ.get("OBC_SSH_HOST", "localhost"),
            port=int(os.environ.get("OBC_SSH_PORT", "2222")),
            username=os.environ.get("OBC_SSH_USER", "obc"),
            password=os.environ.get("OBC_SSH_PASSWORD", "password123"),
        )


class SatelliteClient:
    """Layer 4: talks to OBC only through SSH and OBC scripts."""

    def __init__(self, config: ObcSshConfig | None = None) -> None:
        self._config = config or ObcSshConfig.from_env()

    def run_remote_command(self, command: str) -> str:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=self._config.host,
                port=self._config.port,
                username=self._config.username,
                password=self._config.password,
                timeout=10,
                allow_agent=False,
                look_for_keys=False,
            )
            _, stdout, stderr = client.exec_command(command, timeout=30)
            exit_code = stdout.channel.recv_exit_status()
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            if exit_code != 0:
                raise RuntimeError(
                    f"Remote command failed (exit {exit_code}): {command}\n{err or out}"
                )
            return out
        finally:
            client.close()

    def _run_script(self, script_path: str, panel_index: int) -> str:
        command = f"python3 {script_path} --panelIndex={panel_index}"
        return self.run_remote_command(command)

    def reset_simulator(self) -> None:
        self.run_remote_command(
            'python3 -c "from satellite.persistence import reset_simulator; reset_simulator()"'
        )

    def release_panel(self, panel_index: int) -> bool:
        output = self._run_script(self._config.release_script, panel_index)
        return output == "TRUE"

    def get_release_status(self, panel_index: int) -> bool:
        output = self._run_script(self._config.status_script, panel_index)
        return output == "TRUE"

    def wait_for_deployment(
        self,
        panel_index: int,
        timeout_s: float = 2.0,
        poll_interval_s: float = 0.05,
    ) -> float:
        """
        Poll deployment switch until TRUE or timeout.

        Returns seconds from first poll to first TRUE.
        Raises TimeoutError if switch is not pressed within timeout_s.
        """
        deadline = time.perf_counter() + timeout_s
        started = time.perf_counter()
        while time.perf_counter() < deadline:
            if self.get_release_status(panel_index):
                return time.perf_counter() - started
            time.sleep(poll_interval_s)
        raise TimeoutError(
            f"Panel {panel_index} deployment switch not TRUE within {timeout_s}s"
        )
