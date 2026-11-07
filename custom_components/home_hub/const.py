"""Constants for Home Hub."""

from __future__ import annotations

from dataclasses import dataclass

DOMAIN = "home_hub"

# Wizard fields
CONF_HOUSE_NAME = "house_name"
CONF_OWNER_NAME = "owner_name"
CONF_PEOPLE = "people"
CONF_LIGHTS = "lights"
CONF_CLIMATES = "climates"
CONF_DRIVEWAY_CAMERA = "driveway_camera"
CONF_DOORBELL_CAMERA = "doorbell_camera"
CONF_BATTERY_SENSORS = "battery_sensors"
CONF_WEATHER = "weather"
CONF_CALENDAR = "calendar"
CONF_BIN_CALENDAR = "bin_calendar"
CONF_PRAYER_TIMES = "prayer_times"
CONF_SPEAKER = "speaker"
CONF_WHITE_NOISE = "white_noise"
CONF_EXTRA_MEDIA = "extra_media"
CONF_WALL_DASHBOARD = "wall_dashboard"
CONF_PHONE_DASHBOARD = "phone_dashboard"
CONF_SCREENSAVER_PHOTOS = "screensaver_photos"
CONF_OFFICE_DOOR = "office_door"
# Stage 2: things Home Hub does by itself
CONF_DOORBELL_SENSOR = "doorbell_sensor"
CONF_DOORBELL_TABLET = "doorbell_tablet"
CONF_DOORBELL_SECONDS = "doorbell_seconds"
CONF_AZAN = "azan"
CONF_AZAN_PRAYERS = "azan_prayers"
CONF_AZAN_SOUND = "azan_sound"
CONF_AZAN_PHONES = "azan_phones"
CONF_NIGHT_MODE = "night_mode"
CONF_NIGHT_START = "night_start"
CONF_NIGHT_END = "night_end"
CONF_OUTDOOR_LIGHTS = "outdoor_lights"

AZAN_SOUND_URL = "http://praytimes.org/audio/adhan/Sunni/Adhan%20Makkah.mp3"
AZAN_DEFAULT_PRAYERS = ["dhuhr", "asr", "maghrib", "isha"]
# The "Mute azan" button on the phone notification
AZAN_STOP_ACTION = "HOME_HUB_STOP_AZAN"
# How long the azan is treated as playing if the speaker never reports it stopped
AZAN_MAX_MINUTES = 6
DOORBELL_DEFAULT_SECONDS = 30

# Entities Home Hub adds (unique id suffixes)
AZAN_PLAYING = "azan_playing"
STOP_AZAN = "stop_azan"
TABLET_MODE = "tablet_mode"
SIGNAL_UPDATE = "home_hub_update"

WHITE_NOISE_URL = (
    "https://ia600204.us.archive.org/15/items/"
    "12HoursOfWhiteNoiseStaticInStereo.FavoriteItForTheFuture.StudyingSleepTinnitus/"
    "12HoursOfWhiteNoisestaticInStereo.mp3"
)

PRAYERS = ("fajr", "dhuhr", "asr", "maghrib", "isha")

# Custom cards the dashboards use, matched against the Lovelace resource URLs
REQUIRED_CARDS = {
    "button-card": "button-card",
    "mushroom": "Mushroom",
    "card-mod": "card-mod",
    "wallpanel": "WallPanel",
}


@dataclass(frozen=True)
class DashboardSpec:
    """A dashboard Home Hub owns."""

    id: str
    url_path: str
    title: str
    icon: str
    option: str


WALL = DashboardSpec("home_hub_wall", "home-hub-wall", "Wall tablet", "mdi:tablet-dashboard", CONF_WALL_DASHBOARD)
PHONE = DashboardSpec("home_hub_phone", "home-hub-phone", "Phone", "mdi:cellphone", CONF_PHONE_DASHBOARD)
DASHBOARDS = (WALL, PHONE)
