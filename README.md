# AppDaemon script to track demand tarrifs


Example Configuration
```
energy_tracker:
  module: demand_calculator
  class: EnergyTracker
  import_sensor: sensor.energy_node_iotawatt_import_kwh # This is expected to be total increasing
  export_sensor: sensor.energy_node_iotawatt_export_kwh # This is also expected ot be total increasing
  solar_sensor: sensor.energy_node_iotawatt_solar_kwh # This is just today.
  supply_charge: 0.87  # Daily supply charge in $
  usage_rate_peak: 0.299  # Peak usage rate in $/kWh
  usage_rate_shoulder: 0.299  # Shoulder usage rate in $/kWh
  usage_rate_off_peak: 0.299  # Off-peak usage rate in $/kWh
  demand_rate_high_season: 0.12  # High-season demand rate in $/kW
  demand_rate_low_season: 0.07 # Low-season demand rate in $/kW
  demand_rate_temperate_season: 0.154
  feed_in_tariff: 0.05 # Feed-in tariff rate in $/kWh
```
