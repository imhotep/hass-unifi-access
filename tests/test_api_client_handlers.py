import json

import pytest

pytest.importorskip("unifi_access_api")
from unifi_access_api import UnifiAccessApiClient


def test_on_message_dispatches_registered_handler():
    captured = {}

    def handler(update):
        captured["event"] = update["event"]

    client = UnifiAccessApiClient("example.com")
    client.register_websocket_handler("custom.event", handler)

    client.on_message(None, json.dumps({"event": "custom.event", "data": {}}))

    assert captured["event"] == "custom.event"
