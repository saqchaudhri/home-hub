"""Constants for Home Hub check-in."""

DOMAIN = "home_hub_checkin"
CONF_HOUSE = "house"
CONF_URL = "url"
CONF_REMOTE = "remote"

# Keep trying until the message gets through: quickly at first, then every few minutes
FIRST_RETRY_SECONDS = 15
MAX_RETRY_SECONDS = 300
