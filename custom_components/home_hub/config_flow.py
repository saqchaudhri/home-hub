"""The Home Hub setup wizard.

The same pages are used for first-time setup and for "Reconfigure" later
(the options flow), so a house can swap devices at any time.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    AZAN_DEFAULT_PRAYERS,
    AZAN_SOUND_URL,
    CONF_AZAN,
    CONF_AZAN_PHONES,
    CONF_AZAN_PRAYERS,
    CONF_AZAN_SOUND,
    CONF_DOORBELL_SECONDS,
    CONF_DOORBELL_SENSOR,
    CONF_DOORBELL_TABLET,
    CONF_NIGHT_END,
    CONF_NIGHT_MODE,
    CONF_NIGHT_START,
    CONF_OUTDOOR_LIGHTS,
    DOORBELL_DEFAULT_SECONDS,
    PRAYERS,
    CONF_BATTERY_SENSORS,
    CONF_BIN_CALENDAR,
    CONF_CALENDAR,
    CONF_CLIMATES,
    CONF_DOORBELL_CAMERA,
    CONF_DRIVEWAY_CAMERA,
    CONF_EXTRA_MEDIA,
    CONF_HOUSE_NAME,
    CONF_LIGHTS,
    CONF_OFFICE_DOOR,
    CONF_OWNER_NAME,
    CONF_PEOPLE,
    CONF_PHONE_DASHBOARD,
    CONF_PRAYER_TIMES,
    CONF_SCREENSAVER_PHOTOS,
    CONF_SPEAKER,
    CONF_WALL_DASHBOARD,
    CONF_WEATHER,
    CONF_WHITE_NOISE,
    DOMAIN,
)
from .features import NIGHT_END, NIGHT_START
from .house import find_phones, find_prayer_sensors, find_tablets, missing_cards
from .suggest import suggest

STEPS = ("user", "people", "lights", "heating", "cameras", "info", "media", "doorbell", "azan", "schedules", "dashboards")


def _entity(domain: str | list[str], multiple: bool = False, device_class: str | None = None) -> selector.EntitySelector:
    cfg = selector.EntitySelectorConfig(domain=domain, multiple=multiple)
    if device_class:
        cfg = selector.EntitySelectorConfig(domain=domain, multiple=multiple, device_class=device_class)
    return selector.EntitySelector(cfg)


def _choose(options: dict[str, str], multiple: bool = False) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[selector.SelectOptionDict(value=k, label=v) for k, v in options.items()],
            multiple=multiple,
            custom_value=True,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _tablets(hass: HomeAssistant) -> selector.SelectSelector:
    return _choose(find_tablets(hass))


def _phones(hass: HomeAssistant) -> selector.SelectSelector:
    return _choose(find_phones(hass), multiple=True)


PRAYER_CHOICES = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=[selector.SelectOptionDict(value=p, label=p.capitalize()) for p in PRAYERS],
        multiple=True,
        mode=selector.SelectSelectorMode.LIST,
    )
)

# For each page: (field, selector or a function of hass that makes one, value when left empty)
FIELDS: dict[str, list[tuple[str, Any, Any]]] = {
    "user": [
        (CONF_HOUSE_NAME, selector.TextSelector(), "Home"),
        (CONF_OWNER_NAME, selector.TextSelector(), ""),
    ],
    "people": [(CONF_PEOPLE, _entity("person", multiple=True), [])],
    "lights": [(CONF_LIGHTS, _entity(["light", "switch"], multiple=True), [])],
    "heating": [(CONF_CLIMATES, _entity("climate", multiple=True), [])],
    "cameras": [
        (CONF_DRIVEWAY_CAMERA, _entity("camera"), None),
        (CONF_DOORBELL_CAMERA, _entity("camera"), None),
        (CONF_BATTERY_SENSORS, _entity("sensor", multiple=True, device_class="battery"), []),
    ],
    "info": [
        (CONF_WEATHER, _entity("weather"), None),
        (CONF_CALENDAR, _entity("calendar"), None),
        (CONF_BIN_CALENDAR, _entity("calendar"), None),
        (CONF_PRAYER_TIMES, selector.BooleanSelector(), False),
    ],
    "media": [
        (CONF_SPEAKER, _entity("media_player"), None),
        (CONF_WHITE_NOISE, selector.BooleanSelector(), False),
        (CONF_EXTRA_MEDIA, _entity("media_player", multiple=True), []),
    ],
    "doorbell": [
        (CONF_DOORBELL_SENSOR, _entity("binary_sensor"), None),
        (CONF_DOORBELL_TABLET, _tablets, None),
        (
            CONF_DOORBELL_SECONDS,
            selector.NumberSelector(
                selector.NumberSelectorConfig(min=10, max=120, step=5, unit_of_measurement="s", mode=selector.NumberSelectorMode.SLIDER)
            ),
            DOORBELL_DEFAULT_SECONDS,
        ),
    ],
    "azan": [
        (CONF_AZAN, selector.BooleanSelector(), False),
        (CONF_AZAN_PRAYERS, PRAYER_CHOICES, []),
        (CONF_AZAN_SOUND, selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.URL)), AZAN_SOUND_URL),
        (CONF_AZAN_PHONES, _phones, []),
    ],
    "schedules": [
        (CONF_NIGHT_MODE, selector.BooleanSelector(), False),
        (CONF_NIGHT_START, selector.TimeSelector(), NIGHT_START),
        (CONF_NIGHT_END, selector.TimeSelector(), NIGHT_END),
        (CONF_OUTDOOR_LIGHTS, _entity(["light", "switch"], multiple=True), []),
    ],
    "dashboards": [
        (CONF_WALL_DASHBOARD, selector.BooleanSelector(), False),
        (CONF_PHONE_DASHBOARD, selector.BooleanSelector(), False),
        (CONF_SCREENSAVER_PHOTOS, selector.BooleanSelector(), False),
        (CONF_OFFICE_DOOR, _entity("binary_sensor"), None),
    ],
}

# Starting values for a brand-new house
FIRST_RUN_DEFAULTS = {
    CONF_WHITE_NOISE: True,
    CONF_WALL_DASHBOARD: True,
    CONF_PHONE_DASHBOARD: True,
    CONF_SCREENSAVER_PHOTOS: True,
    CONF_DOORBELL_SECONDS: DOORBELL_DEFAULT_SECONDS,
    CONF_AZAN_PRAYERS: AZAN_DEFAULT_PRAYERS,
    CONF_AZAN_SOUND: AZAN_SOUND_URL,
    CONF_NIGHT_MODE: True,
    CONF_NIGHT_START: NIGHT_START,
    CONF_NIGHT_END: NIGHT_END,
}


class _Wizard:
    """The wizard pages, shared by the setup flow and the reconfigure (options) flow."""

    _values: dict[str, Any]
    # What the first-run guesses found, per page (empty when reconfiguring)
    _notes: dict[str, str] = {}

    def _schema(self, step: str) -> vol.Schema:
        schema: dict[Any, Any] = {}
        for key, sel, _empty in FIELDS[step]:
            value = self._values.get(key)
            if not isinstance(sel, selector.Selector):
                sel = sel(self.hass)
            if isinstance(sel, selector.BooleanSelector):
                schema[vol.Optional(key, default=bool(value))] = sel
            elif key == CONF_HOUSE_NAME:
                schema[vol.Required(key, default=value or "Home")] = sel
            else:
                # suggested_value prefills the field but still lets it be cleared
                schema[vol.Optional(key, description={"suggested_value": value})] = sel
        return vol.Schema(schema)

    async def _page(self, step: str, user_input: dict[str, Any] | None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            for key, _sel, empty in FIELDS[step]:
                value = user_input.get(key, empty)
                self._values[key] = value.strip() if isinstance(value, str) else value
            if step == "dashboards" and not (
                self._values.get(CONF_WALL_DASHBOARD) or self._values.get(CONF_PHONE_DASHBOARD)
            ):
                errors["base"] = "no_dashboard"
            if step == "info" and self._values.get(CONF_PRAYER_TIMES) and not find_prayer_sensors(self.hass):
                errors[CONF_PRAYER_TIMES] = "no_prayer_sensors"
            errors |= self._check(step)
            if not errors:
                index = STEPS.index(step)
                if index + 1 < len(STEPS):
                    return await getattr(self, f"async_step_{STEPS[index + 1]}")()
                return self._finish()

        return self.async_show_form(
            step_id=step,
            data_schema=self._schema(step),
            errors=errors,
            description_placeholders=await self._placeholders(step),
            last_step=step == STEPS[-1],
        )

    def _check(self, step: str) -> dict[str, str]:
        """Problems with the stage 2 pages that would stop a feature working."""
        v = self._values
        if step == "doorbell" and v.get(CONF_DOORBELL_SENSOR):
            if not v.get(CONF_DOORBELL_TABLET):
                return {CONF_DOORBELL_TABLET: "need_tablet"}
            if not (v.get(CONF_DRIVEWAY_CAMERA) or v.get(CONF_DOORBELL_CAMERA)):
                return {CONF_DOORBELL_SENSOR: "need_camera"}
        if step == "azan" and v.get(CONF_AZAN):
            if not find_prayer_sensors(self.hass):
                return {CONF_AZAN: "no_prayer_sensors"}
            if not v.get(CONF_AZAN_PRAYERS):
                return {CONF_AZAN_PRAYERS: "need_prayer"}
            if not (v.get(CONF_SPEAKER) or v.get(CONF_AZAN_PHONES)):
                return {CONF_AZAN: "need_speaker_or_phone"}
        return {}

    async def _placeholders(self, step: str) -> dict[str, str]:
        return {"found": self._notes.get(step, ""), **await self._step_placeholders(step)}

    async def _step_placeholders(self, step: str) -> dict[str, str]:
        if step == "user":
            missing = await missing_cards(self.hass)
            return {
                "missing": (
                    "All the custom cards the dashboards need are installed."
                    if not missing
                    else "**Install these from HACS first, or some cards will show errors:** " + ", ".join(missing)
                )
            }
        if step == "info":
            found = find_prayer_sensors(self.hass)
            return {
                "prayer_status": (
                    "Prayer time sensors found."
                    if found
                    else "No prayer time sensors found. Add the Islamic Prayer Times integration to use them."
                )
            }
        if step == "doorbell":
            tablets = find_tablets(self.hass)
            return {
                "tablets": (
                    "Tablets found: " + ", ".join(tablets.values()) + "."
                    if tablets
                    else "**No tablets found.** "
                    + (
                        "On the wall tablet, open **Browser Mod** in the sidebar, turn on **Register** and reload the "
                        "page, then run this wizard again."
                        if self.hass.config_entries.async_entries("browser_mod")
                        else "Add **Browser Mod** in Settings → Devices & services → Add integration (install it from "
                        "HACS first if it isn't listed). Then on the wall tablet open **Browser Mod** in the sidebar, "
                        "turn on **Register** and reload the page, and run this wizard again."
                    )
                )
            }
        if step == "azan":
            phones = find_phones(self.hass)
            return {
                "phones": (
                    "Phones found: " + ", ".join(phones.values()) + "."
                    if phones
                    else "No phones with the Home Assistant app were found, so the azan will only play on the speaker."
                )
            }
        return {}

    async def async_step_people(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._page("people", user_input)

    async def async_step_lights(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._page("lights", user_input)

    async def async_step_heating(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._page("heating", user_input)

    async def async_step_cameras(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._page("cameras", user_input)

    async def async_step_info(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._page("info", user_input)

    async def async_step_media(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._page("media", user_input)

    async def async_step_doorbell(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._page("doorbell", user_input)

    async def async_step_azan(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._page("azan", user_input)

    async def async_step_schedules(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._page("schedules", user_input)

    async def async_step_dashboards(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._page("dashboards", user_input)

    def _finish(self) -> ConfigFlowResult:
        raise NotImplementedError


class HomeHubConfigFlow(_Wizard, ConfigFlow, domain=DOMAIN):
    """First-time setup."""

    VERSION = 1

    def __init__(self) -> None:
        self._values = dict(FIRST_RUN_DEFAULTS)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is None and not self._notes:
            guesses = suggest(self.hass)
            self._values |= guesses.values
            self._notes = guesses.notes
            if guesses.values:
                self._notes["user"] = (
                    "Home Hub has looked through your devices and filled in its best guesses on each page. "
                    "Check each page and change anything that's wrong."
                )
            if find_prayer_sensors(self.hass):
                self._values.setdefault(CONF_PRAYER_TIMES, True)
        return await self._page("user", user_input)

    def _finish(self) -> ConfigFlowResult:
        return self.async_create_entry(title=self._values[CONF_HOUSE_NAME], data=self._values)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HomeHubOptionsFlow()


class HomeHubOptionsFlow(_Wizard, OptionsFlow):
    """Reconfigure: the same pages, prefilled with the current answers."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        # Defaults first, so settings added in a newer version start sensibly
        self._values = {**FIRST_RUN_DEFAULTS, **self.config_entry.data, **self.config_entry.options}
        return await self._page("user", None)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._page("user", user_input)

    def _finish(self) -> ConfigFlowResult:
        if self._values == dict(self.config_entry.options):
            # Home Assistant only tells Home Hub about changed answers, but running
            # the wizard again should always rebuild the dashboards.
            from . import async_rebuild

            self.hass.async_create_task(async_rebuild(self.hass, self.config_entry))
        return self.async_create_entry(data=self._values)
