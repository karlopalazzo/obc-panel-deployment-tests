import pytest


@pytest.mark.integration
@pytest.mark.parametrize("panel_index", [1, 2, 3, 4])
def test_panel_deploys_within_two_seconds_after_release(satellite_client, panel_index: int):
    assert satellite_client.release_panel(panel_index) is True
    elapsed = satellite_client.wait_for_deployment(panel_index, timeout_s=2.0)
    assert elapsed <= 2.0
