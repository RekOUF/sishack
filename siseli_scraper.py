#!/usr/bin/env python3
"""Siseli Solar Dashboard Scraper v7 — reliable full data capture.

Strategy: Playwright browser login, intercept ALL API responses while navigating
through every page. Force fresh API calls by clearing cache between pages.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright

URL = os.environ.get("SISELI_URL", "https://solar.siseli.com")
ACCOUNT = os.environ.get("SISELI_ACCOUNT", "")
PASSWORD = os.environ.get("SISELI_PASSWORD", "")

# Device detail URL for battery data (the inverter/PV device with battery telemetry)
DEVICE_ID = "425066051514892288"
DEVICE_DETAIL_URL = (
    f"{URL}/#/operator/stationDevice/deviceList/deviceDetails"
    f"?activeTabKey=dataOverview&deviceId={DEVICE_ID}"
)


class APICapture:
    def __init__(self):
        self.responses = []
        self._seen = set()

    async def on_response(self, response):
        if "/apis/" in response.url:
            # Deduplicate by URL
            key = response.url.split("?")[0].replace(URL, "")
            if key not in self._seen:
                self._seen.add(key)
                try:
                    body = await response.json()
                    self.responses.append({"url": response.url, "data": body})
                except Exception:
                    pass
            else:
                # Still capture but mark as duplicate
                try:
                    body = await response.json()
                    self.responses.append({"url": response.url, "data": body})
                except Exception:
                    pass

    def get_data(self):
        # Return ALL data, last write wins for same path
        result = {}
        for r in self.responses:
            path = r["url"].replace(URL, "").split("?")[0]
            result[path] = r["data"]
        return result


async def login(page):
    await page.goto(f"{URL}/#/user/login", wait_until="networkidle")
    await page.wait_for_timeout(2000)
    try:
        await page.click('role=tab[name="Account"]', timeout=3000)
    except Exception:
        pass
    await page.fill('input[placeholder="Account"]', ACCOUNT)
    await page.fill('input[placeholder="Password"]', PASSWORD)
    await page.click('button:has-text("Sign In")')
    await page.wait_for_timeout(5000)
    try:
        # Wait for any of several post-login indicators
        await page.wait_for_selector('text=Overview, text=Production Power, text=Total Power, text=Station', timeout=15000)
        return True
    except Exception:
        # Also accept if URL changed away from login page
        return not page.url.endswith("#/user/login") and not page.url.endswith("/user/login")


async def main():
    output_file = sys.argv[1] if len(sys.argv) > 1 else "/tmp/siseli_data.json"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        cap = APICapture()
        page.on("response", cap.on_response)

        print("Logging in...", flush=True)
        if not await login(page):
            await page.screenshot(path="/tmp/siseli_login_fail.png")
            print("Login failed!")
            await browser.close()
            return

        # Navigate to overview first
        print("Overview...", flush=True)
        await page.goto(f"{URL}/#/operations/overview", wait_until="networkidle")
        await page.wait_for_timeout(5000)

        # Click the station row to expand details — this triggers detail API calls
        print("Station list...", flush=True)
        # Clear cache to force fresh API calls
        await context.clear_cookies()

        # Navigate to station list via link click
        await page.goto(f"{URL}/#/operations/station/list", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Try to click on the station name to open detail
        print("Station detail...", flush=True)
        try:
            station_link = page.locator('text=schuurPlant')
            if await station_link.count() > 0:
                await station_link.first.click()
                await page.wait_for_timeout(5000)
        except Exception:
            pass

        # Try View link
        try:
            view_btn = page.locator('a:has-text("View"), button:has-text("View")')
            if await view_btn.count() > 0:
                await view_btn.first.click()
                await page.wait_for_timeout(6000)
        except Exception:
            pass

        # Navigate to the device detail page to capture battery telemetry
        print("Device detail (battery telemetry)...", flush=True)
        await page.goto(DEVICE_DETAIL_URL, wait_until="networkidle")
        await page.wait_for_timeout(8000)

        # Click the Battery tab if present to trigger battery-specific API calls
        try:
            battery_tab = page.get_by_text("Battery")
            if await battery_tab.count() > 0 and await battery_tab.first.is_visible(timeout=3000):
                await battery_tab.first.click(timeout=5000)
                await page.wait_for_timeout(5000)
                print("Clicked Battery tab", flush=True)
        except Exception:
            pass

        # Wait for any late API calls
        await page.wait_for_timeout(5000)
        page.remove_listener("response", cap.on_response)

        all_data = cap.get_data()

        # Build structured result
        result = {
            "timestamp": datetime.now().isoformat(),
            "scrape_source": "playwright_intercept_v7",
            "overview": {},
            "station": {},
            "daily_power_curve": [],
            "devices": [],
            "battery": {},
            "device_state": {},
            "api_raw": all_data,
        }

        def _get_field(fields, key):
            if isinstance(fields, dict) and key in fields:
                return fields[key].get("value")
            return None

        def _get_field_display(fields, key):
            if isinstance(fields, dict) and key in fields:
                return fields[key].get("valueDisplay")
            return None

        # Parse data
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
                    "carbon_saved_kg": d.get("savingStandardCarbon"),
                    "co2_reduction_kg": d.get("co2EmissionReduction"),
                    "so2_reduction_kg": d.get("so2EmissionReduction"),
                    "nox_reduction_kg": d.get("noxEmissionReduction"),
                }

            if path.endswith("/station/list") and "list" in d:
                for st in d.get("list", []):
                    if isinstance(st, dict) and "summaryProperty" in st:
                        sp = st.get("summaryProperty", {})
                        result["station"] = {
                            "id": st.get("id"),
                            "name": st.get("name"),
                            "status": st.get("stateDict"),
                            "type": st.get("stationTypeDict"),
                            "grid_type": st.get("connectedGridTypeDict"),
                            "installed_capacity_kwp": st.get("installedCapacity"),
                            "production_power_kw": st.get("producingPower"),
                            "daily_kwh": st.get("dailyProducedQuantity"),
                            "monthly_kwh": st.get("monthlyProducedQuantity"),
                            "yearly_kwh": st.get("yearlyProducedQuantity"),
                            "total_kwh": st.get("totalProducedQuantity"),
                            "co2_reduction_kg": st.get("co2EmissionReduction"),
                            "carbon_saved_kg": st.get("savingStandardCarbon"),
                            "so2_reduction_kg": st.get("so2EmissionReduction"),
                            "generation_efficiency_pct": st.get("generationEfficiency"),
                            "peak_hours_today": st.get("dailyProducedTime"),
                            "timezone": st.get("timezone"),
                            "longitude": st.get("longitude"),
                            "latitude": st.get("latitude"),
                            "total_earnings_eur": st.get("totalEarnings"),
                            "currency": st.get("currencyDisplay"),
                        }

            # Daily power curve
            if "stateAttributeSummary" in path and "daily" in path:
                for prop in d.get("properties", []):
                    if isinstance(prop, dict) and prop.get("property", {}).get("key") == "generationPower":
                        result["daily_power_curve"] = [
                            {"time": tp["timeDisplay"], "power_kw": tp["value"]}
                            for tp in prop.get("timePoints", [])
                        ]

            # Device list
            if "/device/list" in path and isinstance(d, dict) and "list" in d:
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

            # Device realtime state (battery + inverter telemetry)
            if "deviceState/simple/state/latest" in path and isinstance(d, dict) and "fields" in d:
                fields = d.get("fields", {})
                result["device_state"] = {
                    "time": d.get("time"),
                    "fields": fields,
                }

                # Calculate battery charge/discharge power (W)
                bat_voltage = _get_field(fields, "batteryVoltage") or 0
                charge_current = _get_field(fields, "batteryChargingCurrent") or 0
                discharge_current = _get_field(fields, "batteryDischargeCurrent") or 0
                charge_power_w = bat_voltage * charge_current if bat_voltage and charge_current else 0
                discharge_power_w = bat_voltage * discharge_current if bat_voltage and discharge_current else 0

                result["power"] = {
                    "generation_kw": _get_field(fields, "generationPower"),
                    "load_kw": _get_field(fields, "acOutputActivePower"),
                    "feed_in_w": _get_field(fields, "feedInPower"),
                    "pv_input_w": _get_field(fields, "pvInputPower"),
                    "output_apparent_power_va": _get_field(fields, "outputApparentPower"),
                    "battery_charge_power_w": charge_power_w,
                    "battery_discharge_power_w": discharge_power_w,
                }

                result["battery"] = {
                    "voltage_v": _get_field(fields, "batteryVoltage"),
                    "capacity_pct": _get_field(fields, "batteryCapacity"),
                    "soc_pct": _get_field(fields, "batteryCapacity"),
                    "charging_current_a": _get_field(fields, "batteryChargingCurrent"),
                    "discharge_current_a": _get_field(fields, "batteryDischargeCurrent"),
                    "charge_power_w": charge_power_w,
                    "discharge_power_w": discharge_power_w,
                    "state_code": _get_field(fields, "batState"),
                    "state_text": _get_field_display(fields, "batState"),
                    "type_code": _get_field(fields, "batteryType"),
                    "type_text": _get_field_display(fields, "batteryType"),
                    "rated_voltage_v": _get_field(fields, "ratedBatteryVoltage"),
                    "low_cutoff_voltage_v": _get_field(fields, "lowBatteryCutOffVoltage"),
                    "bulk_charging_voltage_v": _get_field(fields, "bulkChargingVoltage"),
                    "float_charging_voltage_v": _get_field(fields, "floatChargingVoltage"),
                    "equalization_voltage_v": _get_field(fields, "batteryEqualizationVoltage"),
                    "max_charge_current_a": _get_field(fields, "maxTotalChargeCurrent"),
                    "utility_charge_current_a": _get_field(fields, "maxUtilityChargeCurrent1"),
                    "charge_priority_code": _get_field(fields, "chargerSourcePriority"),
                    "charge_priority_text": _get_field_display(fields, "chargerSourcePriority"),
                }

        # If we didn't get station data from list, check if it was included in
        # the overview page (sometimes the Siseli API includes station data inline)
        if not result["station"]:
            for path, data in all_data.items():
                if isinstance(data, dict) and isinstance(data.get("data"), dict):
                    d = data["data"]
                    if "list" in d:
                        for st in d.get("list", []):
                            if isinstance(st, dict) and "summaryProperty" in st:
                                sp = st.get("summaryProperty", {})
                                result["station"] = {
                                    "id": st.get("id"),
                                    "name": st.get("name"),
                                    "status": st.get("stateDict"),
                                    "type": st.get("stationTypeDict"),
                                    "grid_type": st.get("connectedGridTypeDict"),
                                    "installed_capacity_kwp": st.get("installedCapacity"),
                                    "production_power_kw": st.get("producingPower"),
                                    "daily_kwh": st.get("dailyProducedQuantity"),
                                    "monthly_kwh": st.get("monthlyProducedQuantity"),
                                    "yearly_kwh": st.get("yearlyProducedQuantity"),
                                    "total_kwh": st.get("totalProducedQuantity"),
                                    "total_earnings_eur": st.get("totalEarnings"),
                                }
                                break

        # Print summary
        st = result["station"]
        ov = result["overview"]
        print(f"\n=== SISELI SOLAR — {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
        if st:
            print(f"  Station: {st.get('name', '?')} ({st.get('type', '?')})")
            print(f"  Status: {st.get('status', '?')}")
            print(f"  Capacity: {st.get('installed_capacity_kwp', '?')} kWp")
            print(f"  Power: {st.get('production_power_kw', '?')} kW")
            print(f"  Today: {st.get('daily_kwh', '?')} kWh")
            print(f"  Month: {st.get('monthly_kwh', '?')} kWh")
            print(f"  Year: {st.get('yearly_kwh', '?')} kWh")
            print(f"  Total: {st.get('total_kwh', '?')} kWh")
        elif ov:
            print(f"  Overview (aggregated):")
            print(f"    Power now: {ov.get('total_power_kw', '?')} kW")
            print(f"    Today: {ov.get('daily_kwh', '?')} kWh")
            print(f"    Month: {ov.get('monthly_kwh', '?')} kWh")
            print(f"    Year: {ov.get('yearly_kwh', '?')} kWh")
            print(f"    Total: {ov.get('total_kwh', '?')} kWh")
            print(f"    Capacity: {ov.get('installed_capacity_kwp', '?')} kWp")
            print(f"    CO2 saved: {ov.get('co2_reduction_kg', '?')} kg")

        if result["daily_power_curve"]:
            nonzero = [p for p in result["daily_power_curve"] if p["power_kw"] > 0]
            if nonzero:
                peak = max(nonzero, key=lambda x: x["power_kw"])
                print(f"  Peak: {peak['power_kw']} kW at {peak['time']}")

        if result["devices"]:
            print(f"  Devices ({len(result['devices'])}):")
            for dev in result["devices"]:
                print(f"    {dev.get('name', '?')}: {dev.get('type', '?')}")

        bat = result["battery"]
        if bat and bat.get("voltage_v") is not None:
            print(f"\n  Battery:")
            print(f"    Voltage: {bat.get('voltage_v', '?')} V")
            print(f"    SOC: {bat.get('capacity_pct', '?')} %")
            print(f"    Charge current: {bat.get('charging_current_a', '?')} A")
            print(f"    Discharge current: {bat.get('discharge_current_a', '?')} A")
            print(f"    Charge power: {bat.get('charge_power_w', '?')} W")
            print(f"    Discharge power: {bat.get('discharge_power_w', '?')} W")
            print(f"    State: {bat.get('state_text', '?')} ({bat.get('state_code', '?')})")
            print(f"    Type: {bat.get('type_text', '?')}")

        print(f"\n  Endpoints: {len(all_data)}")
        print(f"  Power points: {len(result['daily_power_curve'])}")

        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"  Saved to {output_file}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())