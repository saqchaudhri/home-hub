"""Home Hub: a setup wizard that builds a family's wall-tablet and phone dashboards
and runs the doorbell popup, azan, tablet night mode and outdoor light schedule.

Home Hub owns its dashboards. They are created the first time it is set up and
rebuilt whenever it is reconfigured; restarts never overwrite edits made in
between. Dashboards that already exist with the same address are left alone.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import frontend
from homeassistant.components.lovelace import _register_panel
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.dashboard import LovelaceStorage
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from homeassistant.helpers import entity_registry as er

from .const import AZAN_PLAYING, DASHBOARDS, DOMAIN, PHONE, STOP_AZAN, TABLET_MODE, WALL, DashboardSpec
from .dashboards import build_phone, build_wall, house_title, load_templates
from .features import Features
from .house import find_prayer_sensors, gather_house_info

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SELECT]

_LOGGER = logging.getLogger(__name__)

BUILDERS = {WALL.id: build_wall, PHONE.id: build_phone}


def _settings(entry: ConfigEntry) -> dict[str, Any]:
    return {**entry.data, **entry.options}


def _item(spec: DashboardSpec) -> dict[str, Any]:
    """The dashboard's entry, in the same shape Home Assistant stores for its own dashboards."""
    return {
        "id": spec.id,
        "url_path": spec.url_path,
        "title": spec.title,
        "icon": spec.icon,
        "mode": "storage",
        "require_admin": False,
        "show_in_sidebar": True,
    }


def _owned(hass: HomeAssistant, spec: DashboardSpec) -> LovelaceStorage | None:
    """Return the dashboard if Home Hub registered it."""
    dash = hass.data[LOVELACE_DATA].dashboards.get(spec.url_path)
    if isinstance(dash, LovelaceStorage) and (dash.config or {}).get("id") == spec.id:
        return dash
    return None


def _register(hass: HomeAssistant, spec: DashboardSpec) -> LovelaceStorage | None:
    """Add the dashboard to the sidebar, unless something else already uses its address."""
    if dash := _owned(hass, spec):
        return dash
    in_use = spec.url_path in hass.data[LOVELACE_DATA].dashboards or spec.url_path in hass.data.get(frontend.DATA_PANELS, {})
    if in_use:
        _LOGGER.error("Can't add the %s dashboard: /%s is already in use", spec.title, spec.url_path)
        return None
    item = _item(spec)
    dash = LovelaceStorage(hass, item)
    hass.data[LOVELACE_DATA].dashboards[spec.url_path] = dash
    # Home Assistant's own helper for storage dashboards, so the sidebar entry
    # is registered exactly as for a dashboard made in Settings → Dashboards.
    _register_panel(hass, spec.url_path, "storage", item, False)
    return dash


def _unregister(hass: HomeAssistant, spec: DashboardSpec) -> LovelaceStorage | None:
    if (dash := _owned(hass, spec)) is None:
        return None
    frontend.async_remove_panel(hass, spec.url_path)
    hass.data[LOVELACE_DATA].dashboards.pop(spec.url_path, None)
    return dash


async def _apply(hass: HomeAssistant, entry: ConfigEntry, rebuild: bool) -> None:
    """Register the chosen dashboards, (re)building them where needed, and remove unchosen ones."""
    cfg = _settings(entry)
    templates = await hass.async_add_executor_job(load_templates)
    house = gather_house_info(hass, entry, cfg)
    for spec in DASHBOARDS:
        if not cfg.get(spec.option):
            if dash := _unregister(hass, spec):
                await dash.async_delete()
            continue
        if (dash := _register(hass, spec)) is None:
            continue
        is_new = (await dash.async_get_info()).get("mode") == "auto-gen"
        if rebuild or is_new:
            await dash.async_save(BUILDERS[spec.id](templates, cfg, house))
            _LOGGER.info("Built the %s dashboard for %s", spec.title, house_title(cfg))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Home Hub: start its features and make sure its dashboards are registered."""
    features = Features(hass, _settings(entry), find_prayer_sensors(hass))
    entry.runtime_data = features
    _forget_unused_entities(hass, entry, features)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    features.start()
    entry.async_on_unload(features.stop)
    # Rebuild only straight after the wizard; plain restarts keep hand edits
    rebuild = hass.data.setdefault(DOMAIN, {}).pop(entry.entry_id, False)
    await _apply(hass, entry, rebuild=rebuild)
    entry.async_on_unload(entry.add_update_listener(async_rebuild))
    return True


def _forget_unused_entities(hass: HomeAssistant, entry: ConfigEntry, features: Features) -> None:
    """Remove the entities of features that were turned off in the wizard."""
    registry = er.async_get(hass)
    for domain, key, used in (
        ("binary_sensor", AZAN_PLAYING, features.azan_enabled),
        ("button", STOP_AZAN, features.azan_enabled),
        ("select", TABLET_MODE, features.night_enabled),
    ):
        if not used and (entity_id := registry.async_get_entity_id(domain, DOMAIN, f"{entry.entry_id}_{key}")):
            registry.async_remove(entity_id)


async def async_rebuild(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """The wizard was run again: restart with its answers and rebuild the dashboards."""
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = True
    await hass.config_entries.async_reload(entry.entry_id)



async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Stop the features and take the dashboards out of the sidebar (their content is kept)."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    for spec in DASHBOARDS:
        _unregister(hass, spec)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Home Hub was deleted: delete the dashboards it made."""
    for spec in DASHBOARDS:
        await LovelaceStorage(hass, _item(spec)).async_delete()
