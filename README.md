# AppDaemon script to track demand tarrifs


Example Configuration
```
energy_tracker:
  module: demand_calculator
  class: EnergyTracker
  import_sensor: sensor.energy_node_iotawatt_import_kwh # This is expected to be total increasing, althugh it shouldnt matter as the app resets to 0 each day
  export_sensor: sensor.energy_node_iotawatt_export_kwh # This is also expected ot be total increasing, as above
  solar_sensor: sensor.energy_node_iotawatt_solar_kwh # This is just today, but total increasing would also work.
  supply_charge: 0.87  # Daily supply charge in $
  usage_rate_peak: 0.299  # Peak usage rate in $/kWh
  usage_rate_shoulder: 0.299  # Shoulder usage rate in $/kWh
  usage_rate_off_peak: 0.299  # Off-peak usage rate in $/kWh
  demand_rate_high_season: 0.12  # High-season demand rate in $/kW
  demand_rate_low_season: 0.07 # Low-season demand rate in $/kW
  demand_rate_temperate_season: 0.154
  feed_in_tariff: 0.05 # Feed-in tariff rate in $/kWh
  peak_start_time: "14:00" # These are the configured defaults. If these match your plan, theres no need to change them.
  peak_end_time: "20:00"
  shoulder_start_time: "07:00"
  shoulder_end_time: "22:00"
  high_season_start_date: "11-01"
  high_season_end_date: "03-31"
  temperate_season_start_date: "04-01"
  temperate_season_end_date: "05-31"
  winter_season_start_date: "06-01"
  winter_season_end_date: "08-31"
```

All rates are expected, so just make them all the same if thats the case



A number of sensors are created by this:<br/>
<ul>
  <li><b>sensor.monthly_peak_usage</b>: The highest demand import for the current month, in kwh. Ie the highest half our period of import during the configured peak period.</li>
  <li><b>sensor.daily_solar_generated</b>: Todays solar generation, in kwh</li>
  <li><b>sensor.daily_usage_charge</b>: Todays import cost, NOT daily surcharge or demand, in $</li>
  <li><b>sensor.daily_solar_savings</b>: How much FIT was earnt today, in $</li>
  <li><b>sensor.daily_demand_charge</b>: Todays demand fee, in $</li>
  <li><b>sensor.daily_total_bill</b>: The energy cost for today. This includes surcharge, demand, FIT offset, and all configured tarrifs, in $</li>
  <li><b>sensor.daily_import_charge</b>: Today import charge, including the daily surchange and demand, in $</li>
</ul>


<b>sensor.daily_import_charge</b> is most likely what you want to configure for your energy dashboard, using `Use an entity tracking the total costs`


Key values are written back to a json file as cache to ensure they persist when the script restarts.
  
