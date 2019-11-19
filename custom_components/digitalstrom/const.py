"""Define constants for the digitalSTROM component."""

DOMAIN = "digitalstrom"
DOMAIN_LISTENER = DOMAIN + "_listener"

HOST_FORMAT = "https://{host}:{port}"
SLUG_FORMAT = "{host}_{port}"
TITLE_FORMAT = "{alias} ({host}:{port})"

CONF_DELAY = "delay"

DIGITALSTROM_MANUFACTURERS = ["digitalSTROM AG", "aizo ag"]
DEFAULT_HOST = "dss.local"
DEFAULT_PORT = 8080
DEFAULT_DELAY = 500
DEFAULT_USERNAME = "dssadmin"
DEFAULT_ALIAS = "Apartment"
