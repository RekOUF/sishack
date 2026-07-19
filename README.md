# sishack

Siseli / Solar of Things scraper + Home Assistant pusher.

Private repo — no credentials are committed. Copy `.env.example` to `.env` and fill in your secrets.

## Files

- `siseli_scraper.py` — Playwright browser scraper that logs into https://solar.siseli.com and captures solar + battery data.
- `siseli_ha_push.py` — Runs the scraper and pushes ~30 sensors to Home Assistant via the REST API.
- `siseli_api.py` — Direct API client with the reverse-engineered HMAC signing algorithm.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# edit .env with your Siseli account/password and HA token
```

## Run once

```bash
source .venv/bin/activate
python3 siseli_ha_push.py
```

## Run automatically

Via Hermes cron job `siseli-solar-ha-push` (every 5 minutes) or plain crontab:

```cron
*/5 * * * * cd /path/to/sishack && /path/to/sishack/.venv/bin/python3 siseli_ha_push.py >> /tmp/siseli_ha_cron.log 2>&1
```

## Home Assistant sensors created

`sensor.solar_*` — daily/monthly/yearly/total energy, installed capacity, CO2 saved, status.
`sensor.battery_*` — voltage, SOC, charge/discharge current & power, state, rated/bulk/float/low-cutoff voltages.
`sensor.solar_generation_power`, `sensor.solar_load_power`, `sensor.solar_feed_in_power`, `sensor.pv_input_power`.
`sensor.siseli_*_energy` — accumulated energy counters derived from instantaneous power readings.
