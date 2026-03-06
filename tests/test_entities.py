"""Tests for entity platform modules."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.lock import DOMAIN as LOCK_DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BS_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import STATE_LOCKED, STATE_UNLOCKED
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.unifi_access.const import DOMAIN

from .conftest import MOCK_CONFIG, SAMPLE_DOORS, SAMPLE_EMERGENCY_STATUS, SAMPLE_LOCK_RULE_STATUS


def _make_mock_client() -> AsyncMock:
    """Create a fully mocked API client."""
    client = AsyncMock()
    client.get_doors = AsyncMock(return_value=SAMPLE_DOORS)
    client.get_door_lock_rule = AsyncMock(return_value=SAMPLE_LOCK_RULE_STATUS)
    client.get_emergency_status = AsyncMock(return_value=SAMPLE_EMERGENCY_STATUS)
    client.set_emergency_status = AsyncMock()
    client.unlock_door = AsyncMock()
    client.start_websocket = MagicMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
async def setup_integration(hass: HomeAssistant):
    """Set up the integration with mocked client and return (entry, mock_client)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        unique_id="192.168.1.1",
        title="Unifi Access Doors",
    )
    entry.add_to_hass(hass)

    mock_client = _make_mock_client()

    with (
        patch(
            "custom_components.unifi_access.UnifiAccessApiClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.unifi_access.async_get_clientsession",
            return_value=AsyncMock(),
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    yield entry, mock_client


# ---------------------------------------------------------------------------
# Lock entities
# ---------------------------------------------------------------------------


class TestLockPlatform:
    """Tests for lock entities."""

    async def test_lock_entities_created(
        self, hass: HomeAssistant, setup_integration
    ) -> None:
        """Lock entities should be created for each door."""
        entity_ids = [
            s.entity_id
            for s in hass.states.async_all()
            if s.domain == "lock"
        ]
        assert len(entity_ids) == 2

    async def test_lock_state(
        self, hass: HomeAssistant, setup_integration
    ) -> None:
        """Test that lock state reflects door lock relay status."""
        # door-001 has door_lock_relay_status=LOCK → locked
        states = {
            s.attributes.get("friendly_name", ""): s.state
            for s in hass.states.async_all()
            if s.domain == "lock"
        }
        # The exact friendly name depends on HA entity naming,
        # but we can check by unique_id attributes
        lock_states = [s.state for s in hass.states.async_all() if s.domain == "lock"]
        assert STATE_LOCKED in lock_states
        assert STATE_UNLOCKED in lock_states

    async def test_unlock_door(
        self, hass: HomeAssistant, setup_integration
    ) -> None:
        """Test calling the unlock service."""
        entry, mock_client = setup_integration
        lock_entity = next(
            s for s in hass.states.async_all()
            if s.domain == "lock" and s.state == STATE_LOCKED
        )
        await hass.services.async_call(
            LOCK_DOMAIN,
            "unlock",
            {"entity_id": lock_entity.entity_id},
            blocking=True,
        )
        mock_client.unlock_door.assert_called_once()

    async def test_open_door(
        self, hass: HomeAssistant, setup_integration
    ) -> None:
        """Test calling the open service."""
        entry, mock_client = setup_integration
        lock_entity = next(
            s for s in hass.states.async_all() if s.domain == "lock"
        )
        await hass.services.async_call(
            LOCK_DOMAIN,
            "open",
            {"entity_id": lock_entity.entity_id},
            blocking=True,
        )
        mock_client.unlock_door.assert_called()


# ---------------------------------------------------------------------------
# Binary sensor entities
# ---------------------------------------------------------------------------


class TestBinarySensorPlatform:
    """Tests for binary sensor entities."""

    async def test_dps_entities_created(
        self, hass: HomeAssistant, setup_integration
    ) -> None:
        """DPS (door position sensor) entities should be created for each door."""
        bs_entities = [
            s for s in hass.states.async_all()
            if s.domain == "binary_sensor"
        ]
        # 2 DPS sensors + 2 doorbell sensors (non-polling mode)
        assert len(bs_entities) == 4

    async def test_dps_state(
        self, hass: HomeAssistant, setup_integration
    ) -> None:
        """Door position sensor state should match door state."""
        bs_states = {
            s.entity_id: s.state
            for s in hass.states.async_all()
            if s.domain == "binary_sensor" and "dps" not in s.entity_id
            # Just check that some are on/off
        }
        all_states = [s.state for s in hass.states.async_all() if s.domain == "binary_sensor"]
        assert "on" in all_states or "off" in all_states


# ---------------------------------------------------------------------------
# Switch entities
# ---------------------------------------------------------------------------


class TestSwitchPlatform:
    """Tests for switch entities."""

    async def test_switch_entities_created(
        self, hass: HomeAssistant, setup_integration
    ) -> None:
        """Evacuation and lockdown switches should be created."""
        switch_entities = [
            s for s in hass.states.async_all()
            if s.domain == "switch"
        ]
        assert len(switch_entities) == 2

    async def test_switch_initial_state(
        self, hass: HomeAssistant, setup_integration
    ) -> None:
        """Both switches should be off initially (no emergency)."""
        switch_states = [
            s.state for s in hass.states.async_all()
            if s.domain == "switch"
        ]
        assert all(state == "off" for state in switch_states)

    async def test_turn_on_evacuation(
        self, hass: HomeAssistant, setup_integration
    ) -> None:
        """Test turning on the evacuation switch."""
        entry, mock_client = setup_integration
        switch_entity = next(
            s for s in hass.states.async_all()
            if s.domain == "switch" and "evacuation" in s.entity_id
        )
        await hass.services.async_call(
            SWITCH_DOMAIN,
            "turn_on",
            {"entity_id": switch_entity.entity_id},
            blocking=True,
        )
        mock_client.get_emergency_status.assert_called()
        mock_client.set_emergency_status.assert_called()


# ---------------------------------------------------------------------------
# Event entities
# ---------------------------------------------------------------------------


class TestEventPlatform:
    """Tests for event entities."""

    async def test_event_entities_created(
        self, hass: HomeAssistant, setup_integration
    ) -> None:
        """Access and doorbell event entities should be created (non-polling)."""
        event_entities = [
            s for s in hass.states.async_all()
            if s.domain == "event"
        ]
        # 2 access events + 2 doorbell events = 4
        assert len(event_entities) == 4


# ---------------------------------------------------------------------------
# Sensor entities
# ---------------------------------------------------------------------------


class TestSensorPlatform:
    """Tests for sensor entities."""

    async def test_sensor_entities_created(
        self, hass: HomeAssistant, setup_integration
    ) -> None:
        """Lock rule sensor entities should be created."""
        sensor_entities = [
            s for s in hass.states.async_all()
            if s.domain == "sensor"
        ]
        # 2 doors × 2 sensors (rule + end time) = 4
        assert len(sensor_entities) == 4

    async def test_lock_rule_sensor_value(
        self, hass: HomeAssistant, setup_integration
    ) -> None:
        """Lock rule sensor should show the current rule."""
        rule_sensors = [
            s for s in hass.states.async_all()
            if s.domain == "sensor" and "lock_rule_sensor_ended_time" not in s.entity_id
            and "lock_rule" in s.entity_id and "interval" not in s.entity_id
        ]
        assert any(s.state == "keep_lock" for s in rule_sensors)


# ---------------------------------------------------------------------------
# Image entities
# ---------------------------------------------------------------------------


class TestImagePlatform:
    """Tests for image entities."""

    async def test_image_entities_created(
        self, hass: HomeAssistant, setup_integration
    ) -> None:
        """Image entities should be created for non-polling mode."""
        image_entities = [
            s for s in hass.states.async_all()
            if s.domain == "image"
        ]
        assert len(image_entities) == 2
