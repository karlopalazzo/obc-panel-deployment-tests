import pytest


@pytest.mark.integration
@pytest.mark.parametrize("panel_index", [1, 2, 3, 4])
def test_panel_deploys_within_two_seconds_after_release(satellite_client, panel_index: int):
    assert satellite_client.release_and_wait(panel_index=panel_index, timeout_s=2.0) <= 2.0

@pytest.mark.integration
def test_nonexistent_panel_release_returns_false(satellite_client):
    assert satellite_client.release_panel(5) is False


@pytest.mark.integration
def test_nonexistent_panel_release_raises_error_using_helper(satellite_client):
    with pytest.raises(RuntimeError, match="panel 5"):
        satellite_client.release_and_wait(5)
