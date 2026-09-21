"""Tests for async_open_door_direction (double-driveway entry_method)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.unifi_access.const import (
    GATE_DIRECTION_IN,
    GATE_DIRECTION_OUT,
)
from custom_components.unifi_access.hub import UnifiAccessHub


class TestHubDoorDirection:
    """Tests for async_open_door_direction (double-driveway entry_method)."""

    @pytest.fixture
    def hub(self, mock_api_client: AsyncMock) -> UnifiAccessHub:
        return UnifiAccessHub(mock_api_client)

    async def test_async_open_door_direction_in(
        self, hub: UnifiAccessHub, mock_api_client: AsyncMock
    ) -> None:
        """in direction uses entry_method, not control_cmd."""
        await hub.async_open_door_direction("door-001", GATE_DIRECTION_IN)
        mock_api_client.unlock_door.assert_called_once_with(
            "door-001", entry_method=GATE_DIRECTION_IN
        )
        assert "control_cmd" not in mock_api_client.unlock_door.call_args.kwargs

    async def test_async_open_door_direction_out(
        self, hub: UnifiAccessHub, mock_api_client: AsyncMock
    ) -> None:
        """out direction uses entry_method, not control_cmd."""
        await hub.async_open_door_direction("door-001", GATE_DIRECTION_OUT)
        mock_api_client.unlock_door.assert_called_once_with(
            "door-001", entry_method=GATE_DIRECTION_OUT
        )
        assert "control_cmd" not in mock_api_client.unlock_door.call_args.kwargs

    async def test_async_open_door_direction_invalid(
        self, hub: UnifiAccessHub, mock_api_client: AsyncMock
    ) -> None:
        """Invalid direction does not call unlock_door."""
        await hub.async_open_door_direction("door-001", "sideways")
        mock_api_client.unlock_door.assert_not_called()
