# Docker / Container

You can also run the scraper+pusher inside a container.

## Build and run

```bash
cd sishack
docker compose up -d --build
```

## Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SISELI_ACCOUNT` | Siseli account / e-mail | required |
| `SISELI_PASSWORD` | Siseli password | required |
| `HA_URL` | Home Assistant URL | `http://homeassistant.local:8123` |
| `HA_TOKEN` | HA long-lived access token | required |
| `INTERVAL_MINUTES` | Scrape interval | `5` |

## HA OS / add-on

For Home Assistant OS you can run this as a [local add-on](https://developers.home-assistant.io/docs/add-ons/tutorial) by adding the repo folder as a local repository in the Add-on Store, or run the container via Portainer / Terminal & SSH.

### Quick Portainer / docker run on HA OS

```bash
docker run -d \
  --name sishack \
  --restart unless-stopped \
  -e SISELI_ACCOUNT=rvrhee@gmail.com \
  -e SISELI_PASSWORD=your_password \
  -e HA_URL=http://homeassistant.local:8123 \
  -e HA_TOKEN=your_token \
  -e INTERVAL_MINUTES=5 \
  ghcr.io/rekouf/sishack:latest
```

> Replace the image name with the locally built image or publish it to your own registry.
