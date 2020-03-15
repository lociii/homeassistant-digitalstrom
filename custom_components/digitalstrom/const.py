"""Define constants for the digitalSTROM component."""
from typing import List

from pydigitalstrom import constants as dsconst

DOMAIN: str = "digitalstrom"

HOST_FORMAT: str = "https://{host}:{port}"
SLUG_FORMAT: str = "{host}_{port}"
TITLE_FORMAT: str = "{alias} ({host}:{port})"

CONF_DELAY: str = "delay"

DIGITALSTROM_MANUFACTURERS: List[str] = ["digitalSTROM AG", "aizo ag"]
DEFAULT_HOST: str = "dss.local"
DEFAULT_PORT: int = 8080
DEFAULT_DELAY: int = 500
DEFAULT_USERNAME: str = "dssadmin"
DEFAULT_ALIAS: str = "Apartment"
