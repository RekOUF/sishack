#!/usr/bin/env python3
"""Siseli Solar → Home Assistant sensor push.

Runs the Playwright scraper, then pushes all values to HA
via the REST API as custom sensors.

Usage:
  python3 siseli_ha_push.py              # scrape + push
  python3 siseli_ha_push.py --push-only  # push last cached data
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import requests

HA_URL = os.environ.get("HA_URL", "http://homeassistant.local:8123")
HA_TOKEN = os.environ.get("HA_TOKEN", "")
DATA_FILE = "/tmp/siseli_data.json"
ENERGY_STATE_FILE = "/tmp/siseli_energy_state.json"

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

# Sensor definitions: (entity_id, friendly_name, unit, icon, device_class, state_class)
SENSORS = {
    # Solar production (from portal)
    "solar_daily_kwh":        ("Siseli Solar Daily Energy",       "kWh",  "mdi:solar-power",             "energy",       "total_increasing"),
    "solar_monthly_kwh":      ("Siseli Solar Monthly Energy",     "kWh",  "mdi:solar-power",             "energy",       "total_increasing"),
    "solar_yearly_kwh":       ("Siseli Solar Yearly Energy",      "kWh",  "mdi:solar-power",             "energy",       "total_increasing"),
    "solar_total_kwh":        ("Siseli Solar Total Energy",       "kWh",  "mdi:solar-power",             "energy",       "total_increasing"),
    "solar_production_kw":    ("Siseli Solar Production Power",   "kW",   "mdi:solar-power-variant",     "power",        "measurement"),
    "solar_installed_kwp":    ("Siseli Solar Installed Capacity",  "kWp",  "mdi:solar-panel",             None,           None),
    "solar_co2_saved_kg":     ("Siseli Solar CO2 Saved",          "kg",   "mdi:leaf",                    None,           None),
    "solar_station_status":   ("Siseli Solar Station Status",     None,   "mdi:solar-panel-large",        None,           None),
    # Battery sensors
    "battery_voltage":        ("Siseli Battery Voltage",          "V",    "mdi:lightning-bolt",          "voltage",      "measurement"),
    "battery_soc":            ("Siseli Battery SOC",              "%",    "mdi:battery",                 "battery",      "measurement"),
    "battery_charge_current": ("Siseli Battery Charge Current",   "A",    "mdi:current-dc",              "current",      "measurement"),
    "battery_discharge_current": ("Siseli Battery Discharge Current", "A", "mdi:current-dc",             "current",      "measurement"),
    "battery_state":          ("Siseli Battery State",            None,   "mdi:information-outline",     None,           None),
    "battery_rated_voltage":  ("Siseli Battery Rated Voltage",    "V",    "mdi:lightning-bolt-outline",    "voltage",      "measurement"),
    "battery_low_cutoff_voltage": ("Siseli Battery Low Cutoff Voltage", "V", "mdi:alert-outline",         "voltage",      "measurement"),
    "battery_bulk_voltage":   ("Siseli Battery Bulk Voltage",     "V",    "mdi:lightning-bolt",          "voltage",      "measurement"),
    "battery_float_voltage":  ("Siseli Battery Float Voltage",    "V",    "mdi:lightning-bolt",          "voltage",      "measurement"),
    "battery_max_charge_current": ("Siseli Battery Max Charge Current", "A", "mdi:current-dc",          "current",      "measurement"),
    "battery_utility_charge_current": ("Siseli Utility Charge Current", "A", "mdi:current-dc",            "current",      "measurement"),
    "battery_charge_priority": ("Siseli Battery Charge Priority", None,   "mdi:priority-high",             None,           None),
    # Power sensors (instantaneous)
    "solar_generation_power":   ("Siseli Solar Generation Power",   "kW",   "mdi:solar-power-variant",     "power",        "measurement"),
    "solar_load_power":         ("Siseli Load Power",               "kW",   "mdi:home-lightning-bolt",     "power",        "measurement"),
    "solar_feed_in_power":      ("Siseli Feed In Power",          "W",    "mdi:transmission-tower-export", "power",        "measurement"),
    "pv_input_power":           ("Siseli PV Input Power",         "W",    "mdi:solar-panel",             "power",        "measurement"),
    "battery_charge_power":     ("Siseli Battery Charge Power",   "W",    "mdi:battery-charging",          "power",        "measurement"),
    "battery_discharge_power":  ("Siseli Battery Discharge Power","W",    "mdi:battery-minus",             "power",        "measurement"),
    # Energy sensors (accumulated by this script for the HA Energy Dashboard)
    "siseli_solar_production_energy":  ("Siseli Solar Production Energy",  "kWh",  "mdi:solar-power",             "energy",       "total_increasing"),
    "siseli_battery_charge_energy":    ("Siseli Battery Charge Energy",    "kWh",  "mdi:battery-charging",          "energy",       "total_increasing"),
    "siseli_battery_discharge_energy": ("Siseli Battery Discharge Energy", "kWh",  "mdi:battery-minus",             "energy",       "total_increasing"),
    "siseli_grid_import_energy":       ("Siseli Grid Import Energy",       "kWh",  "mdi:transmission-tower-import", "energy",       "total_increasing"),
    "siseli_grid_export_energy":       ("Siseli Grid Export Energy",       "kWh",  "mdi:transmission-tower-export", "energy",       "total_increasing"),
}


def scrape_data():
    """Run the Playwright scraper."""
    print(f"[{datetime.now():%H:%M:%S}] Running Siseli scraper...")
    result = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(__file__), "siseli_scraper.py"), DATA_FILE],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        print(f"Scraper failed (rc={result.returncode}): {result.stderr[-500:]}")
        return None
    print("Scraper done.")
    return None


def load_data():
    """Load scraped JSON data."""
    if not os.path.exists(DATA_FILE):
        print(f"No data file: {DATA_FILE}")
        return None
    with open(DATA_FILE) as f:
        return json.load(f)


def _to_float(value, default=0.0):
    """Safely convert a value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_energy_state():
    """Load persisted energy totals and timestamp."""
    if not os.path.exists(ENERGY_STATE_FILE):
        return {
            "last_update": None,
            "siseli_solar_production_energy": 0.0,
            "siseli_battery_charge_energy": 0.0,
            "siseli_battery_discharge_energy": 0.0,
            "siseli_grid_import_energy": 0.0,
            "siseli_grid_export_energy": 0.0,
        }
    try:
        with open(ENERGY_STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {
            "last_update": None,
            "siseli_solar_production_energy": 0.0,
            "siseli_battery_charge_energy": 0.0,
            "siseli_battery_discharge_energy": 0.0,
            "siseli_grid_import_energy": 0.0,
            "siseli_grid_export_energy": 0.0,
        }


def save_energy_state(state):
    """Persist energy totals and timestamp."""
    with open(ENERGY_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def accumulate_energy(values, power, now_iso):
    """Accumulate energy from instantaneous power readings."""
    state = load_energy_state()
    last_update = state.get("last_update")

    if last_update is None:
        # First run: seed totals and exit without adding energy
        state["last_update"] = now_iso
        save_energy_state(state)
        return {
            "siseli_solar_production_energy": 0.0,
            "siseli_battery_charge_energy": 0.0,
            "siseli_battery_discharge_energy": 0.0,
            "siseli_grid_import_energy": 0.0,
            "siseli_grid_export_energy": 0.0,
        }

    last_time = datetime.fromisoformat(last_update)
    now_time = datetime.fromisoformat(now_iso)
    delta_hours = (now_time - last_time).total_seconds() / 3600.0

    # Cap delta to avoid huge spikes after long downtime
    delta_hours = min(delta_hours, 1.0)

    if delta_hours <= 0:
        return {
            key: state.get(key, 0.0)
            for key in [
                "siseli_solar_production_energy",
                "siseli_battery_charge_energy",
                "siseli_battery_discharge_energy",
                "siseli_grid_import_energy",
                "siseli_grid_export_energy",
            ]
        }

    # Convert all powers to kW
    solar_gen_kw = _to_float(power.get("generation_kw"), 0.0)
    battery_charge_kw = _to_float(power.get("battery_charge_power_w"), 0.0) / 1000.0
    battery_discharge_kw = _to_float(power.get("battery_discharge_power_w"), 0.0) / 1000.0
    feed_in_w = _to_float(power.get("feed_in_w"), 0.0)

    # Feed-in positive = export, negative = import
    grid_export_kw = max(feed_in_w, 0.0) / 1000.0
    grid_import_kw = max(-feed_in_w, 0.0) / 1000.0

    # Accumulate using simple power * time (left Riemann sum)
    state["siseli_solar_production_energy"] += solar_gen_kw * delta_hours
    state["siseli_battery_charge_energy"] += battery_charge_kw * delta_hours
    state["siseli_battery_discharge_energy"] += battery_discharge_kw * delta_hours
    state["siseli_grid_import_energy"] += grid_import_kw * delta_hours
    state["siseli_grid_export_energy"] += grid_export_kw * delta_hours
    state["last_update"] = now_iso

    save_energy_state(state)

    return {
        key: state[key]
        for key in [
            "siseli_solar_production_energy",
            "siseli_battery_charge_energy",
            "siseli_battery_discharge_energy",
            "siseli_grid_import_energy",
            "siseli_grid_export_energy",
        ]
    }


def extract_values(data):
    """Pull sensor values from the scraped data structure."""
    values = {}
    overview = data.get("overview", {}) or {}
    station = data.get("station", {}) or {}
    battery = data.get("battery", {}) or {}
    power = data.get("power", {}) or {}
    now_iso = data.get("timestamp", datetime.now(timezone.utc).isoformat())

    values["solar_daily_kwh"] = overview.get("daily_kwh") or station.get("daily_kwh")
    values["solar_monthly_kwh"] = overview.get("monthly_kwh") or station.get("monthly_kwh")
    values["solar_yearly_kwh"] = overview.get("yearly_kwh") or station.get("yearly_kwh")
    values["solar_total_kwh"] = overview.get("total_kwh") or station.get("total_kwh")
    values["solar_production_kw"] = overview.get("production_power_kw") or station.get("production_power_kw")
    values["solar_installed_kwp"] = overview.get("installed_capacity_kwp") or station.get("installed_capacity_kwp")
    values["solar_co2_saved_kg"] = overview.get("co2_reduction_kg")
    values["solar_station_status"] = station.get("status") or "unknown"

    # Battery values (from device detail page)
    values["battery_voltage"] = battery.get("voltage_v")
    values["battery_soc"] = battery.get("soc_pct")
    values["battery_charge_current"] = battery.get("charging_current_a")
    values["battery_discharge_current"] = battery.get("discharge_current_a")
    values["battery_state"] = battery.get("state_text")
    values["battery_rated_voltage"] = battery.get("rated_voltage_v")
    values["battery_low_cutoff_voltage"] = battery.get("low_cutoff_voltage_v")
    values["battery_bulk_voltage"] = battery.get("bulk_charging_voltage_v")
    values["battery_float_voltage"] = battery.get("float_charging_voltage_v")
    values["battery_max_charge_current"] = battery.get("max_charge_current_a")
    values["battery_utility_charge_current"] = battery.get("utility_charge_current_a")
    values["battery_charge_priority"] = battery.get("charge_priority_text")

    # Power values (instantaneous)
    values["solar_generation_power"] = power.get("generation_kw")
    values["solar_load_power"] = power.get("load_kw")
    values["solar_feed_in_power"] = power.get("feed_in_w")
    values["pv_input_power"] = power.get("pv_input_w")
    values["battery_charge_power"] = power.get("battery_charge_power_w")
    values["battery_discharge_power"] = power.get("battery_discharge_power_w")

    # Accumulated energy for the Energy Dashboard
    energy_values = accumulate_energy(values, power, now_iso)
    values.update(energy_values)

    return values


def push_to_ha(values):
    """Set sensor states in Home Assistant via REST API."""
    ok = 0
    fail = 0
    for key, (friendly, unit, icon, device_class, state_class) in SENSORS.items():
        val = values.get(key)
        if val is None:
            continue
        entity_id = f"sensor.{key}"
        attrs = {
            "friendly_name": friendly,
            "icon": icon,
        }
        if unit:
            attrs["unit_of_measurement"] = unit
        if device_class:
            attrs["device_class"] = device_class
        if state_class:
            attrs["state_class"] = state_class

        payload = {
            "state": str(val),
            "attributes": attrs,
        }
        try:
            r = requests.post(
                f"{HA_URL}/api/states/{entity_id}",
                headers=HEADERS,
                json=payload,
                timeout=10,
            )
            if r.status_code in (200, 201):
                ok += 1
            else:
                print(f"  FAIL {entity_id}: HTTP {r.status_code} — {r.text[:120]}")
                fail += 1
        except Exception as e:
            print(f"  ERR {entity_id}: {e}")
            fail += 1

    print(f"Pushed {ok} sensors OK, {fail} failed.")
    return fail == 0


def main():
    push_only = "--push-only" in sys.argv
    if not push_only:
        scrape_data()

    data = load_data()
    if not data:
        print("No data to push.")
        sys.exit(1)

    values = extract_values(data)
    print(f"Values: {json.dumps(values, indent=2)}")
    push_to_ha(values)


if __name__ == "__main__":
    main()
