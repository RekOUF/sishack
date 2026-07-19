"""DataUpdateCoordinator for Siseli Solar."""

import asyncio
import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .scraper import scrape_siseli

_LOGGER = logging.getLogger(__name__)

class SiseliSolarCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch Siseli solar + battery data."""

    def __init__(self, hass: HomeAssistant, config_entry):
        self.config_entry = config_entry
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        account = self.config_entry.data["account"]
        password = self.config_entry.data["password"]
        base_url = self.config_entry.data.get("base_url", "https://solar.siseli.com")

        try:
            data = await asyncio.to_thread(scrape_siseli, base_url, account, password)
        except Exception as exc:
            raise UpdateFailed(f"Failed to fetch Siseli data: {exc}") from exc

        if not data:
            raise UpdateFailed("No data returned from Siseli")

        _LOGGER.debug("Siseli data updated at %s", datetime.now().isoformat())
        return data
