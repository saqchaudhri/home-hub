"""Stop azan: stops the speaker, but only while it is the azan that's playing."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import STOP_AZAN
from .entity import HomeHubEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    if entry.runtime_data.azan_enabled:
        async_add_entities([StopAzan(entry, STOP_AZAN)])


class StopAzan(HomeHubEntity, ButtonEntity):
    _attr_icon = "mdi:volume-off"

    async def async_press(self) -> None:
        await self.features.stop_azan()
