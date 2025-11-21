# py-unifi-access

A reusable Python client for the UniFi Access local API with support for websocket event handlers. This repository hosts the shared library used by the Home Assistant custom component in `hass-unifi-access`.

## Features
- REST and websocket support for UniFi Access
- Configurable websocket handler registration
- Door model helpers and normalization utilities

## Installation
```bash
pip install py-unifi-access
```

## Usage
```python
from unifi_access_api import UnifiAccessApiClient

client = UnifiAccessApiClient("https://unifi-access.local")
client.register_websocket_handler("access.logs.add", lambda payload: print(payload))
client.fetch_and_set_doors()
client.start_websocket()
```
