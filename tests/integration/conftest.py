import socket

import pytest

from satellite.ssh_client import ObcSshConfig, SatelliteClient


def _obc_port_open(config: ObcSshConfig) -> bool:
    try:
        with socket.create_connection((config.host, config.port), timeout=2):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def obc_ssh_config() -> ObcSshConfig:
    return ObcSshConfig.from_env()


@pytest.fixture(scope="session")
def require_obc(obc_ssh_config: ObcSshConfig) -> ObcSshConfig:
    if not _obc_port_open(obc_ssh_config):
        pytest.skip(
            "OBC SIL not reachable. Start it with: docker compose up -d "
            f"(expected SSH at {obc_ssh_config.host}:{obc_ssh_config.port})"
        )
    return obc_ssh_config


@pytest.fixture
def satellite_client(require_obc: ObcSshConfig) -> SatelliteClient:
    client = SatelliteClient(require_obc)
    client.reset_simulator()
    return client
