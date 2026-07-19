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

> When running in Docker, set `HA_URL` to the **IP** of your HA host (e.g. `http://192.168.177.87:8123`) and use `--network host` (see below). `homeassistant.local` usually does not resolve inside a container.

## HA OS / add-on

For Home Assistant OS you can run this as a [local add-on](https://developers.home-assistant.io/docs/add-ons/tutorial) by adding the repo folder as a local repository in the Add-on Store, or run the container via Portainer / Terminal & SSH.

### Quick Portainer / docker run on HA OS

```bash
docker run -d \
  --name sishack \
  --restart unless-stopped \
  --network host \
  -e SISELI_ACCOUNT=rvrhee@gmail.com \
  -e SISELI_PASSWORD=your_password \
  -e HA_URL=http://192.168.177.87:8123 \
  -e HA_TOKEN=your_token \
  -e INTERVAL_MINUTES=5 \
  ghcr.io/rekouf/sishack:latest
```

> Use the IP of your Home Assistant instance. The default `homeassistant.local` mDNS name usually does **not** resolve inside a container.
