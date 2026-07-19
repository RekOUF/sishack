"""Sensor platform for Siseli Solar."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSORS
from .coordinator import SiseliSolarCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Siseli Solar sensors."""
    coordinator: SiseliSolarCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        SiseliSensor(coordinator, key, name, unit, icon, device_class, state_class)
        for key, (name, unit, icon, device_class, state_class) in SENSORS.items()
    )


class SiseliSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Siseli sensor."""

    def __init__(self, coordinator, key, name, unit, icon, device_class, state_class):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"Siseli {name}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": "Siseli Solar",
            "manufacturer": "Siseli",
        }

    @property
    def native_value(self):
        data = self.coordinator.data
        if not data:
            return None

        overview = data.get("overview", {})
        station = data.get("station", {})
        battery = data.get("battery", {})
        power = data.get("power", {})

        mapping = {
            "solar_daily_kwh": overview.get("daily_kwh"),
            "solar_monthly_kwh": overview.get("monthly_kwh"),
            "solar_yearly_kwh": overview.get("yearly_kwh"),
            "solar_total_kwh": overview.get("total_kwh"),
            "solar_production_kw": overview.get("total_power_kw"),
            "solar_installed_kwp": overview.get("installed_capacity_kwp"),
            "solar_co2_saved_kg": overview.get("co2_reduction_kg"),
            "solar_station_status": station.get("status"),
            "battery_voltage": battery.get("voltage_v"),
            "battery_soc": battery.get("soc_pct"),
            "battery_charge_current": battery.get("charging_current_a"),
            "battery_discharge_current": battery.get("discharge_current_a"),
            "battery_state": battery.get("state_text"),
            "battery_rated_voltage": battery.get("rated_voltage_v"),
            "battery_low_cutoff_voltage": battery.get("low_cutoff_voltage_v"),
            "battery_bulk_voltage": battery.get("bulk_charging_voltage_v"),
            "battery_float_voltage": battery.get("float_charging_voltage_v"),
            "battery_max_charge_current": battery.get("max_charge_current_a"),
            "battery_utility_charge_current": battery.get("utility_charge_current_a"),
            "battery_charge_priority": battery.get("charge_priority_text"),
            "solar_generation_power": power.get("generation_kw"),
            "solar_load_power": power.get("load_kw"),
            "solar_feed_in_power": power.get("feed_in_w"),
            "pv_input_power": power.get("pv_input_w"),
            "battery_charge_power": power.get("battery_charge_power_w"),
            "battery_discharge_power": power.get("battery_discharge_power_w"),
        }

        return mapping.get(self._key)
