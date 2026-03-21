"""Tests for hub.py — the core state manager."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from unifi_access_api import (
    ApiNotFoundError,
    DoorLockRelayStatus,
    DoorLockRuleType,
    DoorPositionStatus,
)

from custom_components.unifi_access.hub import (
    DoorState,
    UnifiAccessHub,
    _normalize_name,
)

from .conftest import SAMPLE_DOORS

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
        mock_api_client.get_door_lock_rule.side_effect = ApiNotFoundError(
            "not supported"
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

    async def test_handle_insights_add(self, hub: UnifiAccessHub) -> None:
        """Test insights add handler triggers access event."""
        msg = MagicMock()
        msg.data.metadata.door = [MagicMock(id="door-001")]
        msg.data.metadata.actor.display_name = "Raphael"
        msg.data.metadata.authentication.display_name = "FACE"
        msg.data.metadata.opened_method = [MagicMock(display_name="face")]
        msg.data.metadata.opened_direction = [MagicMock(display_name="entry")]
        msg.data.event_type = "access.door.unlock"
        msg.data.result = "ACCESS"

        events_received = []
        hub.doors["door-001"].add_event_listener(
            "access", lambda e, a: events_received.append((e, a))
        )

        await hub._handle_insights_add(msg)

        assert len(events_received) == 1
        assert events_received[0][1]["actor"] == "Raphael"
        assert events_received[0][1]["authentication"] == "FACE"
        assert events_received[0][1]["type"] == "unifi_access_entry"
        assert events_received[0][1]["method"] == "face"
        assert events_received[0][1]["result"] == "ACCESS"
        hub.on_doors_updated.assert_not_called()

    async def test_handle_insights_add_unknown_door(
        self, hub: UnifiAccessHub
    ) -> None:
        """Ignore insights for unknown doors."""
        msg = MagicMock()
        msg.data.metadata.door = [MagicMock(id="door-unknown")]
        await hub._handle_insights_add(msg)
        hub.on_doors_updated.assert_not_called()

    async def test_handle_v2_location_update(self, hub: UnifiAccessHub) -> None:
        """Test V2 location update handler."""
        msg = MagicMock()
        msg.data.id = "door-001"
        msg.data.state = MagicMock()
        msg.data.state.dps = DoorPositionStatus.CLOSE
        msg.data.state.lock = "unlocked"
        msg.data.thumbnail = None

        await hub._handle_v2_location_update(msg)

        assert hub.doors["door-001"].door.door_position_status == DoorPositionStatus.CLOSE
        assert hub.doors["door-001"].door.door_lock_relay_status == DoorLockRelayStatus.UNLOCK
        hub.on_doors_updated.assert_called_once()

    async def test_handle_v2_location_update_unknown_door(
        self, hub: UnifiAccessHub
    ) -> None:
        """Ignore V2 location updates for unknown doors."""
        msg = MagicMock()
        msg.data.id = "door-unknown"
        await hub._handle_v2_location_update(msg)
        hub.on_doors_updated.assert_not_called()

    async def test_handle_v2_location_update_with_thumbnail(
        self, hub: UnifiAccessHub, mock_api_client: AsyncMock
    ) -> None:
        """Test V2 location update fetches thumbnail when present."""
        mock_api_client.get_thumbnail = AsyncMock(return_value=b"thumb")

        msg = MagicMock()
        msg.data.id = "door-001"
        msg.data.state = None
        msg.data.thumbnail = MagicMock()
        msg.data.thumbnail.url = "/thumb.jpg"
        msg.data.thumbnail.door_thumbnail_last_update = 1700000000

        await hub._handle_v2_location_update(msg)

        assert hub.doors["door-001"].thumbnail == b"thumb"
        assert hub.doors["door-001"].thumbnail_last_updated is not None
        hub.on_doors_updated.assert_called_once()

    async def test_handle_v2_device_update(self, hub: UnifiAccessHub) -> None:
        """Test V2 device update handler updates door state."""
        msg = MagicMock()
        msg.data.id = "hub-001"
        msg.data.device_type = "UA-Hub"
        msg.data.alias = "My Hub"
        msg.data.name = "Hub"
        msg.data.online = True
        msg.data.firmware = "v1.4.6.0"

        loc_state = MagicMock()
        loc_state.location_id = "door-001"
        loc_state.dps = DoorPositionStatus.CLOSE
        loc_state.lock = "unlocked"
        msg.data.location_states = [loc_state]

        await hub._handle_v2_device_update(msg)

        assert hub.doors["door-001"].hub_type == "UA-Hub"
        assert hub.doors["door-001"].hub_id == "hub-001"
        assert hub.doors["door-001"].door.door_position_status == DoorPositionStatus.CLOSE
        assert hub.doors["door-001"].door.door_lock_relay_status == DoorLockRelayStatus.UNLOCK
        hub.on_doors_updated.assert_called_once()

    async def test_handle_v2_device_update_unknown_location(
        self, hub: UnifiAccessHub
    ) -> None:
        """V2 device update with unknown location_id should be skipped."""
        msg = MagicMock()
        msg.data.id = "hub-001"
        msg.data.device_type = "UA-Hub"
        msg.data.alias = "Hub"
        msg.data.name = "Hub"
        msg.data.online = True
        msg.data.firmware = "v1.4.6.0"

        loc_state = MagicMock()
        loc_state.location_id = "door-unknown"
        loc_state.dps = DoorPositionStatus.CLOSE
        loc_state.lock = "locked"
        msg.data.location_states = [loc_state]

        await hub._handle_v2_device_update(msg)
        hub.on_doors_updated.assert_not_called()

    async def test_handle_v2_device_update_hub_already_set(
        self, hub: UnifiAccessHub
    ) -> None:
        """V2 device update should not overwrite existing hub_id."""
        hub.doors["door-001"].hub_id = "existing-hub"
        hub.doors["door-001"].hub_type = "UA-Hub-Old"

        msg = MagicMock()
        msg.data.id = "hub-new"
        msg.data.device_type = "UA-Hub-New"
        msg.data.alias = "New Hub"
        msg.data.name = "Hub"
        msg.data.online = True
        msg.data.firmware = "v2.0"

        loc_state = MagicMock()
        loc_state.location_id = "door-001"
        loc_state.dps = DoorPositionStatus.CLOSE
        loc_state.lock = "unlocked"
        msg.data.location_states = [loc_state]

        await hub._handle_v2_device_update(msg)

        assert hub.doors["door-001"].hub_id == "existing-hub"
        assert hub.doors["door-001"].hub_type == "UA-Hub-Old"
        assert hub.doors["door-001"].door.door_position_status == DoorPositionStatus.CLOSE
        hub.on_doors_updated.assert_called_once()

    async def test_handle_location_update_legacy(
        self, hub: UnifiAccessHub, mock_api_client: AsyncMock
    ) -> None:
        """Test legacy location update handler fetches thumbnail."""
        mock_api_client.get_thumbnail = AsyncMock(return_value=b"thumb")

        msg = MagicMock()
        msg.data.unique_id = "door-001"
        msg.data.extras = {
            "door_thumbnail": "/thumb.jpg",
            "door_thumbnail_last_update": 1700000000,
        }

        await hub._handle_location_update_legacy(msg)

        assert hub.doors["door-001"].thumbnail == b"thumb"
        assert hub.doors["door-001"].thumbnail_last_updated is not None
        hub.on_doors_updated.assert_called_once()

    async def test_handle_location_update_legacy_unknown_door(
        self, hub: UnifiAccessHub
    ) -> None:
        """Ignore legacy location updates for unknown doors."""
        msg = MagicMock()
        msg.data.unique_id = "door-unknown"
        await hub._handle_location_update_legacy(msg)
        hub.on_doors_updated.assert_not_called()

    async def test_handle_location_update_legacy_no_extras(
        self, hub: UnifiAccessHub
    ) -> None:
        """Legacy location update with no extras should not notify."""
        msg = MagicMock()
        msg.data.unique_id = "door-001"
        msg.data.extras = None

        await hub._handle_location_update_legacy(msg)
        hub.on_doors_updated.assert_not_called()

    async def test_handle_base_info(self, hub: UnifiAccessHub) -> None:
        """Test base info handler does not crash."""
        msg = MagicMock()
        msg.data.top_log_count = 42
        await hub._handle_base_info(msg)
        # Should not trigger any state updates
        hub.on_doors_updated.assert_not_called()

    async def test_handle_logs_add_logging_only(
        self, hub: UnifiAccessHub
    ) -> None:
        """logs.add should only log, not trigger events (insights_add is primary)."""
        msg = MagicMock()
        msg.data.source.target = [
            MagicMock(type="door", id="door-001"),
        ]
        msg.data.source.actor.display_name = "Test"
        msg.data.source.event.result = "ACCESS"
        msg.data.source.authentication.credential_provider = "NFC"

        events_received = []
        hub.doors["door-001"].add_event_listener(
            "access", lambda e, a: events_received.append(a)
        )

        # Simulate a recent insights.add so logs.add is suppressed
        hub._last_insight_time["door-001"] = time.monotonic()

        await hub._handle_logs_add(msg)

        hub.on_doors_updated.assert_not_called()
        assert len(events_received) == 0

    async def test_handle_insights_add_empty_direction(
        self, hub: UnifiAccessHub
    ) -> None:
        """InsightsAdd with empty opened_direction should use generic event type."""
        msg = MagicMock()
        msg.data.metadata.door = [MagicMock(id="door-001")]
        msg.data.metadata.actor.display_name = "Test"
        msg.data.metadata.authentication.display_name = "NFC"
        msg.data.metadata.opened_method = [MagicMock(display_name="nfc")]
        msg.data.metadata.opened_direction = [MagicMock(display_name="")]
        msg.data.event_type = "access.door.unlock"
        msg.data.result = "ACCESS"

        events_received = []
        hub.doors["door-001"].add_event_listener(
            "access", lambda e, a: events_received.append(a)
        )

        await hub._handle_insights_add(msg)

        assert len(events_received) == 1
        assert events_received[0]["type"] == "unifi_access_access"
        hub.on_doors_updated.assert_not_called()

    async def test_handle_insights_add_unknown_direction(
        self, hub: UnifiAccessHub
    ) -> None:
        """InsightsAdd with unexpected direction should use generic event type."""
        msg = MagicMock()
        msg.data.metadata.door = [MagicMock(id="door-001")]
        msg.data.metadata.actor.display_name = "Test"
        msg.data.metadata.authentication.display_name = "NFC"
        msg.data.metadata.opened_method = [MagicMock(display_name="nfc")]
        msg.data.metadata.opened_direction = [MagicMock(display_name="denied")]
        msg.data.event_type = "access.door.unlock"
        msg.data.result = "ACCESS"

        events_received = []
        hub.doors["door-001"].add_event_listener(
            "access", lambda e, a: events_received.append(a)
        )

        await hub._handle_insights_add(msg)

        assert len(events_received) == 1
        assert events_received[0]["type"] == "unifi_access_access"

    async def test_handle_insights_add_missing_door_metadata(
        self, hub: UnifiAccessHub
    ) -> None:
        """InsightsAdd without door metadata should be ignored."""
        msg = MagicMock()
        msg.data.metadata.door = []

        await hub._handle_insights_add(msg)

        hub.on_doors_updated.assert_not_called()

    async def test_apply_lock_dps(self, hub: UnifiAccessHub) -> None:
        """Test the _apply_lock_dps helper updates door state."""
        state = hub.doors["door-001"]
        UnifiAccessHub._apply_lock_dps(
            state, dps=DoorPositionStatus.CLOSE, lock="unlocked"
        )
        assert state.door.door_position_status == DoorPositionStatus.CLOSE
        assert state.door.door_lock_relay_status == DoorLockRelayStatus.UNLOCK

    async def test_apply_lock_dps_unknown_lock(
        self, hub: UnifiAccessHub
    ) -> None:
        """Unknown lock value should only update DPS, not lock relay."""
        state = hub.doors["door-001"]
        original_lock = state.door.door_lock_relay_status
        UnifiAccessHub._apply_lock_dps(
            state, dps=DoorPositionStatus.CLOSE, lock="unknown"
        )
        assert state.door.door_position_status == DoorPositionStatus.CLOSE
        assert state.door.door_lock_relay_status == original_lock

    async def test_start_websocket(
        self, hub: UnifiAccessHub, mock_api_client: AsyncMock
    ) -> None:
        """Test that start_websocket registers all expected handlers."""
        hub.start_websocket()
        mock_api_client.start_websocket.assert_called_once()
        handlers = mock_api_client.start_websocket.call_args[0][0]
        assert "access.data.device.location_update_v2" in handlers
        assert "access.data.v2.location.update" in handlers
        assert "access.data.location.update" in handlers
        assert "access.data.v2.device.update" in handlers
        assert "access.logs.insights.add" in handlers
        assert "access.base.info" in handlers
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
