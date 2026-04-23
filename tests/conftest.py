"""Shared fixtures for hass-unifi-access tests."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Compatibility shim: pytest-homeassistant-custom-component pins HA 2025.1
# which doesn't have AddConfigEntryEntitiesCallback (added ~2025.4).
# Monkey-patch it so our integration code can import it.
# ---------------------------------------------------------------------------
from homeassistant.helpers import entity_platform as _ep

if not hasattr(_ep, "AddConfigEntryEntitiesCallback"):
    _ep.AddConfigEntryEntitiesCallback = _ep.AddEntitiesCallback

import threading
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from unifi_access_api import (
    Device,
    Door,
    DoorLockRelayStatus,
    DoorLockRuleStatus,
    DoorLockRuleType,
    DoorPositionStatus,
    EmergencyStatus,
)

from custom_components.unifi_access.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations for all tests."""


@pytest.fixture(autouse=True)
def _cleanup_stray_threads():
    """Mark known benign daemon threads so verify_cleanup ignores them.

    Python 3.12 + HA test framework can leave a ``_run_safe_shutdown_loop``
    daemon thread.  The framework's verify_cleanup only allows DummyThread or
    threads whose name starts with ``waitpid-``.  We rename only these known
    framework threads so they pass the check.
    """
    threads_before = frozenset(threading.enumerate())
    yield
    known_stray_threads = ("_run_safe_shutdown_loop",)
    for thread in frozenset(threading.enumerate()) - threads_before:
        if (
            thread.daemon
            and thread.is_alive()
            and any(name in thread.name for name in known_stray_threads)
        ):
            thread.name = f"waitpid-{thread.name}"


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

MOCK_CONFIG = {
    "host": "192.168.1.1",
    "api_token": "test-token",
    "verify_ssl": False,
    "use_polling": False,
}

MOCK_CONFIG_POLLING = {
    **MOCK_CONFIG,
    "use_polling": True,
}

SAMPLE_DOORS = [
    Door(
        id="door-001",
        name="Front Door",
        full_name="Building A / Front Door",
        floor_id="floor-1",
        type="door",
        is_bind_hub=False,
        door_position_status=DoorPositionStatus.OPEN,
        door_lock_relay_status=DoorLockRelayStatus.LOCK,
    ),
    Door(
        id="door-002",
        name="Back Door",
        full_name="Building A / Back Door",
        floor_id="floor-2",
        type="door",
        is_bind_hub=True,
        door_position_status=DoorPositionStatus.CLOSE,
        door_lock_relay_status=DoorLockRelayStatus.UNLOCK,
    ),
]

SAMPLE_DEVICES = [
    Device(
        id="hub-ugt-001",
        type="UGT",
        location_id="door-001",
        capabilities=["is_hub"],
    ),
    Device(
        id="hub-mini-001",
        type="UA-Hub-Door-Mini",
        location_id="door-002",
        capabilities=["is_hub"],
    ),
]

SAMPLE_DEVICE_DOOR_MAP = {device.id: device.location_id for device in SAMPLE_DEVICES}

SAMPLE_LOCK_RULE_STATUS = DoorLockRuleStatus(
    type=DoorLockRuleType.KEEP_LOCK,
    ended_time=1700000000,
)

SAMPLE_EMERGENCY_STATUS = EmergencyStatus(
    evacuation=False,
    lockdown=False,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        unique_id="192.168.1.1",
        title="Unifi Access Doors",
    )


@pytest.fixture
def mock_config_entry_polling() -> MockConfigEntry:
    """Return a mock config entry with polling enabled."""
    return MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_POLLING,
        unique_id="192.168.1.1",
        title="Unifi Access Doors",
    )


@pytest.fixture
def mock_api_client() -> AsyncMock:
    """Return a mocked UnifiAccessApiClient."""
    client = AsyncMock()
    client.authenticate = AsyncMock()
    client.get_doors = AsyncMock(return_value=SAMPLE_DOORS)
    client.get_door_lock_rule = AsyncMock(return_value=SAMPLE_LOCK_RULE_STATUS)
    client.get_emergency_status = AsyncMock(return_value=SAMPLE_EMERGENCY_STATUS)
    client.set_emergency_status = AsyncMock()
    client.set_door_lock_rule = AsyncMock()
    client.unlock_door = AsyncMock()
    client.get_devices = AsyncMock(return_value=SAMPLE_DEVICES)
    client.get_device_door_map = AsyncMock(return_value=SAMPLE_DEVICE_DOOR_MAP)
    client.resolve_door_id = MagicMock(side_effect=SAMPLE_DEVICE_DOOR_MAP.get)
    client.get_thumbnail = AsyncMock(return_value=b"fake-image-bytes")
    client.start_websocket = MagicMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
async def mock_setup_entry(hass: HomeAssistant) -> Any:
    """Patch the integration setup/unload to avoid full platform loading."""
    with (
        patch(
            "custom_components.unifi_access.async_setup_entry",
            return_value=True,
        ) as mock,
        patch(
            "custom_components.unifi_access.async_unload_entry",
            return_value=True,
        ),
    ):
        yield mock
        # Unload entries while patches are still active to avoid teardown errors
        for entry in hass.config_entries.async_entries(DOMAIN):
            await hass.config_entries.async_unload(entry.entry_id)
