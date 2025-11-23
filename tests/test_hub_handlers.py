import asyncio
import json
from threading import Thread

import pytest

pytest.importorskip("unifi_access_api")
from custom_components.unifi_access.const import DOORBELL_START_EVENT
from custom_components.unifi_access.hub import UnifiAccessHub
from unifi_access_api.door import UnifiAccessDoor


def _start_loop():
    loop = asyncio.new_event_loop()
    thread = Thread(target=loop.run_forever, daemon=True)
    thread.start()
    return loop, thread


def _stop_loop(loop, thread):
    loop.call_soon_threadsafe(loop.stop)
    thread.join()


def test_remote_view_handler_triggers_doorbell_event():
    loop, thread = _start_loop()
    hub = UnifiAccessHub("example.com")
    hub.loop = loop

    door = UnifiAccessDoor(
        door_id="door-1",
        name="Front Door",
        door_position_status="close",
        door_lock_relay_status="lock",
        door_lock_rule="",
        door_lock_rule_ended_time=0,
        hub=hub,
    )
    hub.doors[door.id] = door

    captured_events = []

    def _listener(event_type, attributes):
        captured_events.append((event_type, attributes["door_id"]))

    door.add_event_listener("doorbell_press", _listener)

    hub.on_message(
        None,
        json.dumps(
            {
                "event": "access.remote_view",
                "data": {"door_name": "Front Door", "request_id": "req-1"},
            }
        ),
    )

    asyncio.run_coroutine_threadsafe(asyncio.sleep(0), loop).result()
    loop.call_soon_threadsafe(loop.stop)
    thread.join()

    assert captured_events[0][0] == DOORBELL_START_EVENT
    assert captured_events[0][1] == door.id


def test_location_update_changes_state():
    loop, thread = _start_loop()
    hub = UnifiAccessHub("example.com")
    hub.loop = loop

    door = UnifiAccessDoor(
        door_id="door-1",
        name="Front Door",
        door_position_status="close",
        door_lock_relay_status="lock",
        door_lock_rule="",
        door_lock_rule_ended_time=0,
        hub=hub,
    )
    hub.doors[door.id] = door

    hub.on_message(
        None,
        json.dumps(
            {
                "event": "access.data.v2.location.update",
                "data": {
                    "location_type": "door",
                    "id": "door-1",
                    "state": {"dps": "open", "lock": "unlocked"},
                },
            }
        ),
    )

    asyncio.run_coroutine_threadsafe(asyncio.sleep(0), loop).result()
    _stop_loop(loop, thread)

    assert door.door_position_status == "open"
    assert door.door_lock_relay_status == "unlock"
