# Home Assistant OS Add-on

For Home Assistant OS (the dummy-proof way).

## Install

1. In Home Assistant, go to **Settings > Add-ons > Add-on Store**.
2. Click the three dots top-right → **Repositories**.
3. Add this repository URL: `https://github.com/ReKOUF/sishack`
4. Click **Add**.
5. Find **Siseli Solar** in the store and click **Install**.
6. After install, go to **Configuration** and fill in:
   - **SISELI_ACCOUNT**: your Siseli account / e-mail
   - **SISELI_PASSWORD**: your Siseli password
   - **HA_URL**: `http://homeassistant:8123` (default, usually works inside HA OS)
   - **HA_TOKEN**: a Home Assistant long-lived access token
   - **INTERVAL_MINUTES**: `5`
7. Click **Start**.

The add-on will scrape Siseli every 5 minutes and push all sensors to Home Assistant.

## Note

This add-on uses a pre-built container image. First install requires the image to be downloaded from GitHub Container Registry.
