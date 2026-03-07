"""Tests for hub.py — the core state manager."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from unifi_access_api import (
    ApiError,
    Door,
    DoorLockRelayStatus,
    DoorLockRuleStatus,
    DoorLockRuleType,
    DoorPositionStatus,
    EmergencyStatus,
)

from custom_components.unifi_access.hub import DoorState, UnifiAccessHub, _normalize_name

from .conftest import SAMPLE_DOORS, SAMPLE_EMERGENCY_STATUS, SAMPLE_LOCK_RULE_STATUS


# ---------------------------------------------------------------------------
# DoorState basics
# ---------------------------------------------------------------------------


class TestDoorState:
    """Tests for the DoorState dataclass."""

    def test_properties(self) -> None:
        """Test basic property access."""
        state = DoorState(door=SAMPLE_DOORS[0])
        assert state.id == "door-001"
        assert state.name == "Front Door"
        assert state.is_locked is True  # LOCK
        assert state.is_open is True  # OPEN

    def test_doorbell_pressed(self) -> None:
        """Test doorbell_pressed property."""
        state = DoorState(door=SAMPLE_DOORS[0])
        assert state.doorbell_pressed is False

        state.doorbell_request_id = "req-123"
        assert state.doorbell_pressed is True

    def test_event_listeners(self) -> None:
        """Test add/remove/trigger event listeners."""
        state = DoorState(door=SAMPLE_DOORS[0])
        received = []

        def listener(event: str, attrs: dict) -> None:
            received.append((event, attrs))

        state.add_event_listener("access", listener)
        state.trigger_event("access", {"actor": "test"})
        assert len(received) == 1
        assert received[0] == ("access", {"actor": "test"})

        # Triggering a different event should not call the listener
        state.trigger_event("doorbell_press", {"type": "start"})
        assert len(received) == 1

        # Remove and verify no more calls
        state.remove_event_listener("access", listener)
        state.trigger_event("access", {"actor": "another"})
        assert len(received) == 1

    def test_remove_nonexistent_listener(self) -> None:
        """Removing a listener that was never added should not raise."""
        state = DoorState(door=SAMPLE_DOORS[0])
        state.remove_event_listener("access", lambda e, a: None)  # no-op


# ---------------------------------------------------------------------------
# _normalize_name
# ---------------------------------------------------------------------------


class TestNormalizeName:
    """Tests for the _normalize_name helper."""

    def test_empty(self) -> None:
        assert _normalize_name("") == ""

    def test_strips_whitespace(self) -> None:
        assert _normalize_name("  Front Door  ") == "Front Door"

    def test_nfc_normalization(self) -> None:
        # ä composed vs decomposed
        composed = "\u00e4"     # ä
        decomposed = "a\u0308"  # a + combining ¨
        assert _normalize_name(composed) == _normalize_name(decomposed)


# ---------------------------------------------------------------------------
# UnifiAccessHub — data fetching
# ---------------------------------------------------------------------------


class TestHubUpdate:
    """Tests for UnifiAccessHub data fetching."""

    @pytest.fixture
    def hub(self, mock_api_client: AsyncMock) -> UnifiAccessHub:
        return UnifiAccessHub(mock_api_client)

    async def test_async_update_populates_doors(self, hub: UnifiAccessHub) -> None:
        """First update should populate the doors dict."""
        doors = await hub.async_update()
        assert "door-001" in doors
        assert "door-002" in doors
        assert doors["door-001"].name == "Front Door"
        assert doors["door-001"].lock_rule == "keep_lock"

    async def test_async_update_preserves_existing_state(
        self, hub: UnifiAccessHub, mock_api_client: AsyncMock
    ) -> None:
        """Second update should update door objects, not replace DoorState."""
        await hub.async_update()
        state_001 = hub.doors["door-001"]
        state_001.hub_type = "UA-Hub"  # set by device_update handler

        await hub.async_update()
        # Same DoorState object, just updated door
        assert hub.doors["door-001"] is state_001
        assert hub.doors["door-001"].hub_type == "UA-Hub"

    async def test_async_update_lock_rule_failure(
        self, hub: UnifiAccessHub, mock_api_client: AsyncMock
    ) -> None:
        """If lock rule fetching fails with 404, supports_door_lock_rules becomes False."""
        mock_api_client.get_door_lock_rule.side_effect = ApiError(
            "not supported", status_code=404
        )
        await hub.async_update()
        assert hub.supports_door_lock_rules is False

    async def test_async_get_emergency_status(self, hub: UnifiAccessHub) -> None:
        """Test fetching emergency status."""
        status = await hub.async_get_emergency_status()
        assert status.evacuation is False
        assert status.lockdown is False
        assert hub.evacuation is False

    async def test_async_set_emergency_status(
        self, hub: UnifiAccessHub, mock_api_client: AsyncMock
    ) -> None:
        """Test setting emergency status."""
        await hub.async_set_emergency_status(evacuation=True)
        assert hub.evacuation is True
        assert hub.lockdown is False
        mock_api_client.set_emergency_status.assert_called_once()

    async def test_async_set_lock_rule(
        self, hub: UnifiAccessHub, mock_api_client: AsyncMock
    ) -> None:
        """Test setting a door lock rule."""
        await hub.async_update()  # populate doors
        hub.doors["door-001"].lock_rule_interval = 30
        await hub.async_set_lock_rule("door-001", "keep_lock")
        mock_api_client.set_door_lock_rule.assert_called_once()
        rule = mock_api_client.set_door_lock_rule.call_args[0][1]
        assert rule.type == DoorLockRuleType.KEEP_LOCK
        assert rule.interval == 30


# ---------------------------------------------------------------------------
# UnifiAccessHub — notifications
# ---------------------------------------------------------------------------


class TestHubNotifications:
    """Tests for hub notification callbacks."""

    @pytest.fixture
    def hub(self, mock_api_client: AsyncMock) -> UnifiAccessHub:
        return UnifiAccessHub(mock_api_client)

    async def test_notify_doors_updated(self, hub: UnifiAccessHub) -> None:
        """Verify on_doors_updated callback is called."""
        callback = MagicMock()
        hub.on_doors_updated = callback
        hub._notify_doors_updated()
        callback.assert_called_once()

    async def test_notify_doors_updated_none(self, hub: UnifiAccessHub) -> None:
        """No callback set should not raise."""
        hub._notify_doors_updated()  # Should not raise

    async def test_notify_emergency_updated(self, hub: UnifiAccessHub) -> None:
        """Verify on_emergency_updated callback is called."""
        callback = MagicMock()
        hub.on_emergency_updated = callback
        hub._notify_emergency_updated()
        callback.assert_called_once()


# ---------------------------------------------------------------------------
# UnifiAccessHub — WebSocket handlers
# ---------------------------------------------------------------------------


class TestHubWebSocketHandlers:
    """Tests for WebSocket event handlers."""

    @pytest.fixture
    async def hub(self, mock_api_client: AsyncMock) -> UnifiAccessHub:
        hub = UnifiAccessHub(mock_api_client)
        await hub.async_update()
        hub.on_doors_updated = MagicMock()
        hub.on_emergency_updated = MagicMock()
        return hub

    async def test_handle_location_update(self, hub: UnifiAccessHub) -> None:
        """Test location_update_v2 handler."""
        msg = MagicMock()
        msg.data.id = "door-001"
        msg.data.state = MagicMock()
        msg.data.state.dps = DoorPositionStatus.CLOSE
        msg.data.state.lock = "unlocked"
        msg.data.state.remain_lock = None
        msg.data.state.remain_unlock = None
        msg.data.thumbnail = None

        await hub._handle_location_update(msg)

        assert hub.doors["door-001"].door.door_position_status == DoorPositionStatus.CLOSE
        assert hub.doors["door-001"].door.door_lock_relay_status == DoorLockRelayStatus.UNLOCK
        hub.on_doors_updated.assert_called_once()

    async def test_handle_location_update_unknown_door(self, hub: UnifiAccessHub) -> None:
        """Ignore updates for unknown doors."""
        msg = MagicMock()
        msg.data.id = "door-unknown"
        await hub._handle_location_update(msg)
        hub.on_doors_updated.assert_not_called()

    async def test_handle_remote_view(self, hub: UnifiAccessHub) -> None:
        """Test doorbell press start handler."""
        msg = MagicMock()
        msg.data.door_name = "Front Door"
        msg.data.request_id = "req-abc"

        events_received = []
        hub.doors["door-001"].add_event_listener(
            "doorbell_press", lambda e, a: events_received.append((e, a))
        )

        await hub._handle_remote_view(msg)

        assert hub.doors["door-001"].doorbell_request_id == "req-abc"
        assert len(events_received) == 1
        hub.on_doors_updated.assert_called_once()

    async def test_handle_remote_view_change(self, hub: UnifiAccessHub) -> None:
        """Test doorbell press stop handler."""
        hub.doors["door-001"].doorbell_request_id = "req-abc"

        msg = MagicMock()
        msg.data.remote_call_request_id = "req-abc"

        await hub._handle_remote_view_change(msg)

        assert hub.doors["door-001"].doorbell_request_id is None
        hub.on_doors_updated.assert_called_once()

    async def test_handle_device_update(self, hub: UnifiAccessHub) -> None:
        """Test device update handler assigns hub type."""
        msg = MagicMock()
        msg.data.unique_id = "hub-001"
        msg.data.device_type = "UA-Hub"
        msg.data.door = MagicMock()
        msg.data.door.unique_id = "door-001"

        await hub._handle_device_update(msg)

        assert hub.doors["door-001"].hub_type == "UA-Hub"
        assert hub.doors["door-001"].hub_id == "hub-001"
        hub.on_doors_updated.assert_called_once()

    async def test_handle_device_update_already_set(self, hub: UnifiAccessHub) -> None:
        """Device update should be ignored if hub is already set."""
        hub.doors["door-001"].hub_id = "existing"
        hub.doors["door-001"].hub_type = "existing"

        msg = MagicMock()
        msg.data.unique_id = "hub-002"
        msg.data.device_type = "UA-Hub-New"
        msg.data.door = MagicMock()
        msg.data.door.unique_id = "door-001"

        await hub._handle_device_update(msg)

        assert hub.doors["door-001"].hub_id == "existing"
        hub.on_doors_updated.assert_not_called()

    async def test_handle_settings_update(self, hub: UnifiAccessHub) -> None:
        """Test settings (evacuation/lockdown) update handler."""
        msg = MagicMock()
        msg.data.evacuation = True
        msg.data.lockdown = True

        await hub._handle_settings_update(msg)

        assert hub.evacuation is True
        assert hub.lockdown is True
        hub.on_emergency_updated.assert_called_once()

    async def test_start_websocket(
        self, hub: UnifiAccessHub, mock_api_client: AsyncMock
    ) -> None:
        """Test that start_websocket registers all expected handlers."""
        hub.start_websocket()
        mock_api_client.start_websocket.assert_called_once()
        handlers = mock_api_client.start_websocket.call_args[0][0]
        assert "access.data.device.location_update_v2" in handlers
        assert "access.remote_view" in handlers
        assert "access.remote_view.change" in handlers
        assert "access.data.device.update" in handlers
        assert "access.logs.add" in handlers
        assert "access.hw.door_bell" in handlers
        assert "access.data.setting.update" in handlers

    async def test_async_close(
        self, hub: UnifiAccessHub, mock_api_client: AsyncMock
    ) -> None:
        """Test that close delegates to client."""
        await hub.async_close()
        mock_api_client.close.assert_called_once()
