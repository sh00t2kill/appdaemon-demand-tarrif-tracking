import pytest
from unittest.mock import MagicMock
from demand_calculator import EnergyTracker

@pytest.fixture
def energy_tracker(mocker):
    tracker = EnergyTracker()
    tracker.args = {
        "import_sensor": "sensor.energy_import",
        "export_sensor": "sensor.energy_export",
        "solar_sensor": "sensor.solar_generated",
        "supply_charge": 1.0,
        "usage_rate_peak": 0.3,
        "usage_rate_shoulder": 0.2,
        "usage_rate_off_peak": 0.1,
        "demand_rate_high_season": 0.15,
        "demand_rate_low_season": 0.10,
        "feed_in_tariff": 0.1,
        "demand_rate_temperate_season": 0.12
    }
    tracker.config_dir = "/path/to/config"
    tracker.get_state = MagicMock(return_value=0)
    tracker.set_state = MagicMock()
    tracker.log = MagicMock()
    tracker.run_daily = MagicMock()
    tracker.run_every = MagicMock()
    tracker.listen_state = MagicMock()
    tracker.save_cache = MagicMock()
    tracker.load_cache = MagicMock()
    return tracker

def test_initialize(energy_tracker):
    energy_tracker.initialize()
    energy_tracker.listen_state.assert_any_call(energy_tracker.track_energy_import, "sensor.energy_import")
    energy_tracker.listen_state.assert_any_call(energy_tracker.track_energy_export, "sensor.energy_export")
    energy_tracker.listen_state.assert_any_call(energy_tracker.track_solar, "sensor.solar_generated")
    energy_tracker.run_daily.assert_called()
    energy_tracker.run_every.assert_called()

def test_track_energy_import(energy_tracker):
    energy_tracker.previous_import = 100
    energy_tracker.track_energy_import("sensor.energy_import", None, 100, 150, {})
    assert energy_tracker.total_import == 50
    energy_tracker.save_cache.assert_called()
    energy_tracker.set_state.assert_any_call("sensor.monthly_peak_usage", state=50, attributes={
        "unit_of_measurement": "kWh",
        "device_class": "energy",
        "state_class": "measurement",
        "friendly_name": "Monthly Peak Usage",
        "icon": "mdi:flash"
    })

def test_track_energy_export(energy_tracker):
    energy_tracker.previous_export = 50
    energy_tracker.track_energy_export("sensor.energy_export", None, 50, 100, {})
    assert energy_tracker.total_export == 50
    energy_tracker.save_cache.assert_called()

def test_track_solar(energy_tracker):
    energy_tracker.previous_solar = 200
    energy_tracker.track_solar("sensor.solar_generated", None, 200, 250, {})
    assert energy_tracker.total_solar_generated == 50
    energy_tracker.save_cache.assert_called()
    energy_tracker.set_state.assert_any_call("sensor.daily_solar_generated", state=50, attributes={
        "unit_of_measurement": "kWh",
        "device_class": "energy",
        "friendly_name": "Daily Solar Generated",
        "icon": "mdi:solar-power"
    })

def test_reset_daily_totals(energy_tracker):
    energy_tracker.total_import = 100
    energy_tracker.total_export = 50
    energy_tracker.total_solar_generated = 30
    energy_tracker.reset_daily_totals({})
    assert energy_tracker.total_import == 0
    assert energy_tracker.total_export == 0
    assert energy_tracker.total_solar_generated == 0
    energy_tracker.save_cache.assert_called()
    energy_tracker.set_state.assert_any_call("sensor.daily_usage_charge", state=0)
    energy_tracker.set_state.assert_any_call("sensor.daily_solar_savings", state=0)
    energy_tracker.set_state.assert_any_call("sensor.daily_total_bill", state=0)
    energy_tracker.set_state.assert_any_call("sensor.daily_demand_charge", state=0)
    energy_tracker.set_state.assert_any_call("sensor.daily_import_charge", state=0)
    energy_tracker.set_state.assert_any_call("sensor.daily_solar_generated", state=0)
