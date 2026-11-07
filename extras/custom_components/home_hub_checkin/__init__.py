"""Home Hub check-in: tell whoever looks after this Home Assistant that it's online.

When Home Assistant starts, it sends one short message to the check-in address
(a webhook on the installer's own Home Assistant), and keeps retrying until it
gets through, so it works however long the box waits to be plugged in.
"""

from __future__ import annotations

import asyncio
import logging

import aiohttp

from homeassistant.components import network
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_HOUSE, CONF_REMOTE, CONF_URL, FIRST_RETRY_SECONDS, MAX_RETRY_SECONDS

_LOGGER = logging.getLogger(__name__)


async def check_in(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Send the "online" message, retrying until it is delivered."""
    session = async_get_clientsession(hass)
    delay = FIRST_RETRY_SECONDS
    while True:
        try:
            local_ip = await network.async_get_source_ip(hass)
        except Exception:  # noqa: BLE001 - no network yet
            local_ip = None
        payload = {
            "event": "online",
            "house": entry.data[CONF_HOUSE],
            "remote_url": entry.data.get(CONF_REMOTE) or "",
            "local_ip": local_ip or "",
            "ha_version": HA_VERSION,
        }
        try:
            async with session.post(entry.data[CONF_URL], json=payload, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status < 400:
                    _LOGGER.info("Checked in: %s is online", payload["house"])
                    return
                _LOGGER.warning("Check-in was refused (HTTP %s); will try again", resp.status)
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
            _LOGGER.debug("Check-in failed (%s); trying again in %s s", err, delay)
        await asyncio.sleep(delay)
        delay = min(delay * 2, MAX_RETRY_SECONDS)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Cancelled automatically if check-in is removed or reloaded
    entry.async_create_background_task(hass, check_in(hass, entry), "home_hub_checkin")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True
