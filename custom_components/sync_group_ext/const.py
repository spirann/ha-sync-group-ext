"""Constants for the Sync Switch & Light Group integration."""

DOMAIN = "sync_group_ext"

CONF_NAME = "name"
CONF_ICON = "icon"
CONF_MEMBERS = "members"
# Optional: an existing switch/light entity that acts as an additional
# "master" alongside the Main entity we create - e.g. a physical device
# whose on/off can be driven by its own integration/automation and should
# still be treated as a group-wide trigger.
CONF_LINKED_MASTER = "linked_master"

DEFAULT_ICON = "mdi:sync"

# Entity states we consider "real" on/off values. Anything else
# (unavailable, unknown, None, ...) is treated as noise and ignored.
STATE_VALUES = ("on", "off")

# Domains this integration is willing to link together as members.
SUPPORTED_DOMAINS = ("switch", "light")

PLATFORMS = ["switch"]
