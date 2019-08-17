"""Define constants for the digitalSTROM component."""

DOMAIN = 'digitalstrom'
DOMAIN_LISTENER = DOMAIN + '_listener'

CONFIG_PATH = '.digitalstrom/auth_{host}.json'
HOST_FORMAT = 'https://{host}:{port}'
SLUG_FORMAT = '{host}_{port}'
TITLE_FORMAT = 'digitalSTROM @ {host}'
CONF_SLUG = 'slug'

DIGITALSTROM_MANUFACTURERS = ['digitalSTROM AG', 'aizo ag']
DEFAULT_HOST = 'dss.local'
DEFAULT_PORT = 8080
DEFAULT_USERNAME = 'dssadmin'
DEFAULT_ALIAS = 'Apartment'
