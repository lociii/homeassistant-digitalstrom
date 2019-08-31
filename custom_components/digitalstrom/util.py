from homeassistant.util import slugify

from .const import SLUG_FORMAT


def slugify_entry(host, port):
    return slugify(SLUG_FORMAT.format(host=host, port=port))
