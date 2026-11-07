"""Home Hub check-in: the Pi tells its installer it's online."""

from __future__ import annotations

import asyncio

import aiohttp
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

import custom_components.home_hub_checkin as checkin
from custom_components.home_hub_checkin.const import DOMAIN

URL = "https://installer.example/api/webhook/abc123"
DATA = {"house": "Yusuf's house", "url": URL, "remote": "http://home-hub-yusuf:8123"}


@pytest.fixture(autouse=True)
def quick_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checkin, "FIRST_RETRY_SECONDS", 0)
    monkeypatch.setattr(checkin, "MAX_RETRY_SECONDS", 0)


async def _wait_for_calls(mock: AiohttpClientMocker, count: int) -> None:
    for _ in range(200):
        if mock.call_count >= count:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"only {mock.call_count} check-in attempts")


async def test_checks_in_once_online(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.post(URL, status=200)
    entry = MockConfigEntry(domain=DOMAIN, title=DATA["house"], data=DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await _wait_for_calls(aioclient_mock, 1)
    await asyncio.sleep(0.05)
    assert aioclient_mock.call_count == 1  # stops after it got through
    _method, url, body, _headers = aioclient_mock.mock_calls[0]
    assert str(url) == URL
    assert body["event"] == "online"
    assert body["house"] == "Yusuf's house"
    assert body["remote_url"] == "http://home-hub-yusuf:8123"


async def test_keeps_trying_until_connected(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """No internet yet (cable not plugged in): it keeps trying."""
    aioclient_mock.post(URL, exc=aiohttp.ClientConnectionError())
    entry = MockConfigEntry(domain=DOMAIN, title=DATA["house"], data=DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await _wait_for_calls(aioclient_mock, 3)
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_setup_page(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {**DATA, "url": "installer.example"})
    assert result["errors"] == {"url": "bad_url"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], DATA)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Yusuf's house"
