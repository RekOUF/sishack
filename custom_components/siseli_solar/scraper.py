"""Siseli Solar scraper used by the HA integration."""

import asyncio
import json
import os
import tempfile
from datetime import datetime

from playwright.async_api import async_playwright

DEVICE_ID = "425066051514892288"


class APICapture:
    def __init__(self):
        self.responses = []

    async def on_response(self, response):
        if "/apis/" in response.url:
            try:
                body = await response.json()
                self.responses.append({"url": response.url, "data": body})
            except Exception:
                pass

    def get_data(self):
        result = {}
        for r in self.responses:
            path = r["url"].split("?")[0].rsplit("/apis", 1)[-1]
            if not path.startswith("/"):
                path = "/apis" + path
            else:
                path = "/apis" + path
            result[path] = r["data"]
        return result


async def _scrape_async(base_url: str, account: str, password: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        cap = APICapture()
        page.on("response", cap.on_response)

        await page.goto(f"{base_url}/#/user/login", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        try:
            await page.click('role=tab[name="Account"]', timeout=3000)
        except Exception:
            pass
        await page.fill('input[placeholder="Account"]', account)
        await page.fill('input[placeholder="Password"]', password)
        await page.click('button:has-text("Sign In")')
        await page.wait_for_timeout(5000)

        if page.url.endswith("#/user/login") or page.url.endswith("/user/login"):
            await browser.close()
            raise RuntimeError("Siseli login failed")

        # Overview
        await page.goto(f"{base_url}/#/operations/overview", wait_until="networkidle")
        await page.wait_for_timeout(5000)

        # Station list
        await page.goto(f"{base_url}/#/operations/station/list", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        try:
            station_link = page.locator('text=schuurPlant')
            if await station_link.count() > 0:
                await station_link.first.click()
                await page.wait_for_timeout(5000)
        except Exception:
            pass

        # Device detail + battery tab
        device_url = (
            f"{base_url}/#/operator/stationDevice/deviceList/deviceDetails"
            f"?activeTabKey=dataOverview&deviceId={DEVICE_ID}"
        )
        await page.goto(device_url, wait_until="networkidle")
        await page.wait_for_timeout(8000)
        try:
            battery_tab = page.get_by_text("Battery")
            if await battery_tab.count() > 0 and await battery_tab.first.is_visible(timeout=3000):
                await battery_tab.first.click(timeout=5000)
                await page.wait_for_timeout(5000)
        except Exception:
            pass

        await page.wait_for_timeout(5000)
        page.remove_listener("response", cap.on_response)
        all_data = cap.get_data()
        await browser.close()

        return _parse(all_data)


def _to_float(value, default=None):
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse(all_data: dict) -> dict:
    result = {
        "timestamp": datetime.now().isoformat(),
        "overview": {},
        "station": {},
        "daily_power_curve": [],
        "devices": [],
        "battery": {},
        "power": {},
    }

    def _get_field(fields, key):
        if isinstance(fields, dict) and key in fields:
            return fields[key].get("value")
        return None

    def _get_field_display(fields, key):
        if isinstance(fields, dict) and key in fields:
            return fields[key].get("valueDisplay")
        return None

    for path, data in all_data.items():
        if not isinstance(data, dict):
            continue
        d = data.get("data")
        if not isinstance(d, dict):
            continue

        if "ownerStatistics" in path:
            result["overview"] = {
                "total_power_kw": d.get("totalPower"),
                "daily_kwh": d.get("dailyProducedQuantity"),
                "monthly_kwh": d.get("monthlyProducedQuantity"),
                "yearly_kwh": d.get("yearlyProducedQuantity"),
                "total_kwh": d.get("totalProducedQuantity"),
                "installed_capacity_kwp": d.get("allInstalledCapacity"),
                "device_count": d.get("deviceTotal"),
                "co2_reduction_kg": d.get("co2EmissionReduction"),
                "carbon_saved_kg": d.get("savingStandardCarbon"),
            }

        if path.endswith("/station/list") and "list" in d:
            for st in d.get("list", []):
                if isinstance(st, dict):
                    result["station"] = {
                        "id": st.get("id"),
                        "name": st.get("name"),
                        "status": st.get("stateDict"),
                        "type": st.get("stationTypeDict"),
                        "installed_capacity_kwp": st.get("installedCapacity"),
                        "production_power_kw": st.get("producingPower"),
                        "daily_kwh": st.get("dailyProducedQuantity"),
                        "monthly_kwh": st.get("monthlyProducedQuantity"),
                        "yearly_kwh": st.get("yearlyProducedQuantity"),
                        "total_kwh": st.get("totalProducedQuantity"),
                        "co2_reduction_kg": st.get("co2EmissionReduction"),
                    }

        if "stateAttributeSummary" in path and "daily" in path:
            for prop in d.get("properties", []):
                if isinstance(prop, dict) and prop.get("property", {}).get("key") == "generationPower":
                    result["daily_power_curve"] = [
                        {"time": tp["timeDisplay"], "power_kw": tp["value"]}
                        for tp in prop.get("timePoints", [])
                    ]

        if "/device/list" in path:
            for dev in d.get("list", []):
                if isinstance(dev, dict):
                    result["devices"].append({
                        "id": dev.get("id"),
                        "name": dev.get("name"),
                        "sn": dev.get("sn"),
                        "type": dev.get("deviceTypeDict"),
                        "status": dev.get("stateDict"),
                        "power_kw": dev.get("producingPower"),
                    })

        if "deviceState/simple/state/latest" in path and isinstance(d, dict) and "fields" in d:
            fields = d.get("fields", {})
            battery = {
                "voltage_v": _to_float(_get_field(fields, "batteryVoltage")),
                "capacity_pct": _to_float(_get_field(fields, "batteryCapacity")),
                "soc_pct": _to_float(_get_field(fields, "batterySoc")),
                "charging_current_a": _to_float(_get_field(fields, "batteryChargingCurrent")),
                "discharge_current_a": _to_float(_get_field(fields, "batteryDischargeCurrent")),
                "state_code": _get_field(fields, "batteryState"),
                "state_text": _get_field_display(fields, "batteryState"),
                "type_code": _get_field(fields, "batteryType"),
                "type_text": _get_field_display(fields, "batteryType"),
                "rated_voltage_v": _to_float(_get_field(fields, "batteryRatedVoltage")),
                "low_cutoff_voltage_v": _to_float(_get_field(fields, "batteryLowCutoffVoltage")),
                "bulk_charging_voltage_v": _to_float(_get_field(fields, "batteryBulkChargingVoltage")),
                "float_charging_voltage_v": _to_float(_get_field(fields, "batteryFloatChargingVoltage")),
                "equalization_voltage_v": _to_float(_get_field(fields, "batteryEqualizationVoltage")),
                "max_charge_current_a": _to_float(_get_field(fields, "batteryMaxChargeCurrent")),
                "utility_charge_current_a": _to_float(_get_field(fields, "utilityChargeCurrent")),
                "charge_priority_code": _get_field(fields, "chargePriority"),
                "charge_priority_text": _get_field_display(fields, "chargePriority"),
            }
            result["battery"] = battery

        if "deviceState/simple/energy/flow" in path and isinstance(d, dict) and "fields" in d:
            fields = d.get("fields", {})
            result["power"] = {
                "generation_kw": _to_float(_get_field(fields, "generationPower")),
                "load_kw": _to_float(_get_field(fields, "loadPower")),
                "feed_in_w": _to_float(_get_field(fields, "feedInPower")),
                "pv_input_w": _to_float(_get_field(fields, "pvInputPower")),
                "battery_charge_power_w": _to_float(_get_field(fields, "batteryChargePower")),
                "battery_discharge_power_w": _to_float(_get_field(fields, "batteryDischargePower")),
            }

    return result


def scrape_siseli(base_url: str, account: str, password: str) -> dict:
    return asyncio.run(_scrape_async(base_url, account, password))
