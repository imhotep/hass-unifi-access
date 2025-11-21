import sys
from pathlib import Path
import types

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LIB_ROOT = ROOT / "py-unifi-access"
if str(LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(LIB_ROOT))


class _DummyResponse:
    def __init__(self):
        self.status_code = 200

    def json(self):
        return {"data": {}}


def _stub_requests() -> None:
    exceptions_module = types.SimpleNamespace(
        ConnectionError=Exception, SSLError=Exception
    )
    requests_module = types.SimpleNamespace(
        request=lambda *args, **kwargs: _DummyResponse(), exceptions=exceptions_module
    )
    sys.modules.setdefault("requests", requests_module)
    sys.modules.setdefault("requests.exceptions", exceptions_module)


def _stub_websocket() -> None:
    class _DummyWebsocketApp:
        def __init__(self, *args, **kwargs):
            pass

        def run_forever(self, *args, **kwargs):
            return None

    websocket_module = types.SimpleNamespace(WebSocketApp=_DummyWebsocketApp)
    sys.modules.setdefault("websocket", websocket_module)


def _stub_urllib3() -> None:
    urllib3_module = types.SimpleNamespace(disable_warnings=lambda *args, **kwargs: None)
    sys.modules.setdefault("urllib3", urllib3_module)


def _stub_homeassistant() -> None:
    homeassistant_base = types.ModuleType("homeassistant")
    homeassistant_base.__path__ = []  # type: ignore[attr-defined]
    sys.modules.setdefault("homeassistant", homeassistant_base)
    ha_const = types.ModuleType("homeassistant.const")
    ha_const.Platform = types.SimpleNamespace(
        BINARY_SENSOR="binary_sensor",
        EVENT="event",
        IMAGE="image",
        LOCK="lock",
        NUMBER="number",
        SELECT="select",
        SENSOR="sensor",
        SWITCH="switch",
    )
    ha_core = types.ModuleType("homeassistant.core")
    ha_core.HomeAssistant = object
    ha_config_entries = types.ModuleType("homeassistant.config_entries")
    ha_config_entries.ConfigEntry = object
    ha_exceptions = types.ModuleType("homeassistant.exceptions")
    ha_exceptions.ConfigEntryAuthFailed = type("ConfigEntryAuthFailed", (Exception,), {})
    ha_exceptions.HomeAssistantError = type("HomeAssistantError", (Exception,), {})

    def _async_get(_hass=None):
        return types.SimpleNamespace(
            entities=types.SimpleNamespace(get_entries_for_config_entry_id=lambda *_: []),
            async_remove=lambda *_: None,
        )

    ha_entity_registry = types.ModuleType("homeassistant.helpers.entity_registry")
    ha_entity_registry.async_get = _async_get
    helpers_module = types.ModuleType("homeassistant.helpers")
    helpers_module.__path__ = []  # type: ignore[attr-defined]
    helpers_module.entity_registry = ha_entity_registry
    homeassistant_base.helpers = helpers_module
    sys.modules.setdefault("homeassistant.helpers", helpers_module)
    update_coordinator_module = types.ModuleType("homeassistant.helpers.update_coordinator")
    update_coordinator_module.DataUpdateCoordinator = type(
        "DataUpdateCoordinator", (object,), {}
    )
    update_coordinator_module.UpdateFailed = type("UpdateFailed", (Exception,), {})
    sys.modules.setdefault(
        "homeassistant.helpers.update_coordinator", update_coordinator_module
    )

    sys.modules.setdefault("homeassistant.const", ha_const)
    sys.modules.setdefault("homeassistant.core", ha_core)
    sys.modules.setdefault("homeassistant.config_entries", ha_config_entries)
    sys.modules.setdefault("homeassistant.exceptions", ha_exceptions)
    sys.modules.setdefault("homeassistant.helpers.entity_registry", ha_entity_registry)


_stub_requests()
_stub_websocket()
_stub_urllib3()
_stub_homeassistant()
