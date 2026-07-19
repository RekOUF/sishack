"""Constants for the Siseli Solar integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "siseli_solar"
DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=5)

CONF_ACCOUNT: Final = "account"
CONF_SISELI_PASSWORD: Final = "siseli_password"
CONF_BASE_URL: Final = "base_url"
DEFAULT_BASE_URL: Final = "https://solar.siseli.com"

# Sensor definitions: (key, name, unit, icon, device_class, state_class)
SENSORS = {
    "solar_daily_kwh": ("Daily Energy", "kWh", "mdi:solar-power", "energy", "total_increasing"),
    "solar_monthly_kwh": ("Monthly Energy", "kWh", "mdi:solar-power", "energy", "total_increasing"),
    "solar_yearly_kwh": ("Yearly Energy", "kWh", "mdi:solar-power", "energy", "total_increasing"),
    "solar_total_kwh": ("Total Energy", "kWh", "mdi:solar-power", "energy", "total_increasing"),
    "solar_production_kw": ("Production Power", "kW", "mdi:solar-power-variant", "power", "measurement"),
    "solar_installed_kwp": ("Installed Capacity", "kWp", "mdi:solar-panel", None, None),
    "solar_co2_saved_kg": ("CO2 Saved", "kg", "mdi:leaf", None, None),
    "solar_station_status": ("Station Status", None, "mdi:solar-panel-large", None, None),
    "battery_voltage": ("Battery Voltage", "V", "mdi:lightning-bolt", "voltage", "measurement"),
    "battery_soc": ("Battery SOC", "%", "mdi:battery", "battery", "measurement"),
    "battery_charge_current": ("Battery Charge Current", "A", "mdi:current-dc", "current", "measurement"),
    "battery_discharge_current": ("Battery Discharge Current", "A", "mdi:current-dc", "current", "measurement"),
    "battery_state": ("Battery State", None, "mdi:information-outline", None, None),
    "battery_rated_voltage": ("Battery Rated Voltage", "V", "mdi:lightning-bolt-outline", "voltage", "measurement"),
    "battery_low_cutoff_voltage": ("Battery Low Cutoff Voltage", "V", "mdi:alert-outline", "voltage", "measurement"),
    "battery_bulk_voltage": ("Battery Bulk Voltage", "V", "mdi:lightning-bolt", "voltage", "measurement"),
    "battery_float_voltage": ("Battery Float Voltage", "V", "mdi:lightning-bolt", "voltage", "measurement"),
    "battery_max_charge_current": ("Battery Max Charge Current", "A", "mdi:current-dc", "current", "measurement"),
    "battery_utility_charge_current": ("Utility Charge Current", "A", "mdi:current-dc", "current", "measurement"),
    "battery_charge_priority": ("Charge Priority", None, "mdi:priority-high", None, None),
    "solar_generation_power": ("Generation Power", "kW", "mdi:solar-power-variant", "power", "measurement"),
    "solar_load_power": ("Load Power", "kW", "mdi:home-lightning-bolt", "power", "measurement"),
    "solar_feed_in_power": ("Feed In Power", "W", "mdi:transmission-tower-export", "power", "measurement"),
    "pv_input_power": ("PV Input Power", "W", "mdi:solar-panel", "power", "measurement"),
    "battery_charge_power": ("Battery Charge Power", "W", "mdi:battery-charging", "power", "measurement"),
    "battery_discharge_power": ("Battery Discharge Power", "W", "mdi:battery-minus", "power", "measurement"),
}
