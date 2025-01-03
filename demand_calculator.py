import appdaemon.plugins.hass.hassapi as hass
import datetime
import json
import os

class EnergyTracker(hass.Hass):

    def initialize(self):
        self.import_sensor = self.args.get("import_sensor", "sensor.energy_import")
        self.export_sensor = self.args.get("export_sensor", "sensor.energy_export")
        self.solar_sensor = self.args.get("solar_sensor")
        
        self.listen_state(self.track_energy_import, self.import_sensor)
        self.listen_state(self.track_energy_export, self.export_sensor)
        if self.solar_sensor:
            self.listen_state(self.track_solar, self.solar_sensor)
        
        self.peak_usage = 0
        self.monthly_peak_usage = float(self.get_state("sensor.monthly_peak_usage", default=0) or 0)
        self.total_import = 0
        self.total_export = 0
        self.total_solar_generated = 0
        self.total_demand = 0
        self.supply_charge = float(self.args.get("supply_charge", 1.0))  # Daily supply charge in $
        self.usage_rate_peak = float(self.args.get("usage_rate_peak", 0.3))  # Peak usage rate in $/kWh
        self.usage_rate_shoulder = float(self.args.get("usage_rate_shoulder", 0.2))  # Shoulder usage rate in $/kWh
        self.usage_rate_off_peak = float(self.args.get("usage_rate_off_peak", 0.1))  # Off-peak usage rate in $/kWh
        self.demand_rate_high_season = float(self.args.get("demand_rate_high_season", 0.15))  # High-season demand rate in $/kW
        self.demand_rate_low_season = float(self.args.get("demand_rate_low_season", 0.10))  # Low-season demand rate in $/kW
        self.feed_in_tariff = float(self.args.get("feed_in_tariff", 0.1)) if self.args.get("feed_in_tariff") else None  # Feed-in tariff rate in $/kWh
        self.demand_rate_temperate_season = float(self.args.get("demand_rate_temperate_season", 0.12))  # Temperate-season demand rate in $/kW

        self.peak_start_time = self.args.get("peak_start_time", "14:00")
        self.peak_end_time = self.args.get("peak_end_time", "20:00")
        self.shoulder_start_time = self.args.get("shoulder_start_time", "07:00")
        self.shoulder_end_time = self.args.get("shoulder_end_time", "22:00")
        self.high_season_start_date = self.args.get("high_season_start_date", "11-01")
        self.high_season_end_date = self.args.get("high_season_end_date", "03-31")
        self.temperate_season_start_date = self.args.get("temperate_season_start_date", "04-01")
        self.temperate_season_end_date = self.args.get("temperate_season_end_date", "05-31")
        self.winter_season_start_date = self.args.get("winter_season_start_date", "06-01")
        self.winter_season_end_date = self.args.get("winter_season_end_date", "08-31")

        self.cache_file = os.path.join(self.config_dir, "apps", "energy_tracker_cache.json")
        self.load_cache()

        self.reset_peak_usage()
        self.run_daily(self.reset_daily_totals, datetime.time(0, 0))
        self.run_every(self.reset_monthly_peak_usage, datetime.datetime.now().replace(day=1, hour=0, minute=0, second=0), 30 * 24 * 60 * 60)
        self.peak_usage_window = []
        self.run_every(self.calculate_peak_usage, datetime.datetime.now(), 30 * 60)

    def load_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as f:
                cache = json.load(f)
                self.previous_import = cache.get("previous_import", float(self.get_state(self.import_sensor) or 0))
                self.previous_export = cache.get("previous_export", float(self.get_state(self.export_sensor) or 0))
                self.total_import = cache.get("total_import", 0)
                self.total_export = cache.get("total_export", 0)
                self.total_solar_generated = cache.get("total_solar_generated", 0) if self.solar_sensor else 0
                self.peak_usage = cache.get("peak_usage", 0)
                self.monthly_peak_usage = cache.get("monthly_peak_usage", float(self.get_state("sensor.monthly_peak_usage", default=0) or 0))
                self.previous_solar = cache.get("previous_solar", float(self.get_state(self.solar_sensor) or 0)) if self.solar_sensor else 0
                self.total_demand = cache.get("total_demand", 0)
        else:
            self.previous_import = float(self.get_state(self.import_sensor) or 0)
            self.previous_export = float(self.get_state(self.export_sensor) or 0)
            self.total_import = 0
            self.total_export = 0
            self.total_solar_generated = 0
            self.peak_usage = 0
            self.monthly_peak_usage = float(self.get_state("sensor.monthly_peak_usage", default=0) or 0)
            self.previous_solar = float(self.get_state(self.solar_sensor) or 0) if self.solar_sensor else 0
            self.total_demand = 0

    def save_cache(self):
        cache = {
            "previous_import": self.previous_import,
            "previous_export": self.previous_export,
            "total_import": self.total_import,
            "total_export": self.total_export,
            "total_solar_generated": self.total_solar_generated if self.solar_sensor else 0,
            "peak_usage": self.peak_usage,
            "monthly_peak_usage": self.monthly_peak_usage,
            "previous_solar": self.previous_solar if self.solar_sensor else 0,
            "total_demand": self.total_demand
        }
        with open(self.cache_file, 'w') as f:
            json.dump(cache, f)

    def track_energy_import(self, entity, attribute, old, new, kwargs):
        current_time = datetime.datetime.now().time()
        usage = float(new) - self.previous_import
        self.previous_import = float(new)
        self.total_import += usage
        self.save_cache()
        if self.is_peak_period(current_time):
            self.peak_usage_window.append(usage)
            if len(self.peak_usage_window) > 30:
                self.peak_usage_window.pop(0)
            self.total_demand = max(self.peak_usage_window)
            if self.total_demand > self.monthly_peak_usage:
                self.monthly_peak_usage = self.total_demand
                self.set_state("sensor.monthly_peak_usage", state=self.monthly_peak_usage, attributes={
                    "unit_of_measurement": "kWh",
                    "device_class": "energy",
                    "state_class": "measurement",
                    "friendly_name": "Monthly Peak Demand Usage",
                    "icon": "mdi:flash"
                })
            self.set_state("sensor.today_peak_usage", state=self.total_demand, attributes={
                "unit_of_measurement": "kWh",
                "device_class": "energy",
                "state_class": "measurement",
                "friendly_name": "Today Peak Usage",
                "icon": "mdi:flash"
            })
        self.log(f"Current peak usage: {self.peak_usage} kW")
        self.log(f"Monthly peak Demand usage: {self.monthly_peak_usage} kW")
        self.log(f"Total import: {self.total_import} kWh")
        self.calculate_import_charge()

    def track_energy_export(self, entity, attribute, old, new, kwargs):
        export = float(new) - self.previous_export
        self.previous_export = float(new)
        self.total_export += export
        self.save_cache()
        self.log(f"Total export: {self.total_export} kWh")
        if self.feed_in_tariff:
            self.calculate_solar_savings()

    def track_solar(self, entity, attribute, old, new, kwargs):
        if self.solar_sensor:
            solar_generated = float(new) - self.previous_solar
            self.previous_solar = float(new)
            self.total_solar_generated += solar_generated
            self.save_cache()
            self.log(f"Total solar generated: {self.total_solar_generated} kWh")
            self.set_state("sensor.daily_solar_generated", state=self.total_solar_generated, attributes={
                "unit_of_measurement": "kWh",
                "device_class": "energy",
                "friendly_name": "Daily Solar Generated",
                "icon": "mdi:solar-power"
            })

    def reset_peak_usage(self):
        self.run_daily(self.reset_peak_usage_callback, datetime.time(0, 0))

    def reset_peak_usage_callback(self, kwargs):
        self.log(f"Resetting peak usage. Previous peak: {self.peak_usage} kW")
        self.peak_usage = 0

    def reset_monthly_peak_usage(self, kwargs):
        self.log(f"Resetting monthly peak usage. Previous monthly peak: {self.monthly_peak_usage} kW")
        self.monthly_peak_usage = 0
        self.set_state("sensor.monthly_peak_usage", state=self.monthly_peak_usage, attributes={
            "unit_of_measurement": "kWh",
            "device_class": "energy",
            "state_class": "measurement",
            "friendly_name": "Monthly Peak Demand Usage",
            "icon": "mdi:flash"
        })
        self.peak_usage_window = []

    def calculate_import_charge(self):
        usage_charge = round(self.calculate_usage_charge(), 2)
        self.set_state("sensor.daily_usage_charge", state=usage_charge, attributes={
            "unit_of_measurement": "$",
            "device_class": "monetary",
            "friendly_name": "Daily Usage Charge",
            "state_class": "total",
            "icon": "mdi:currency-usd"
        })
        self.calculate_total_bill()

    def calculate_solar_savings(self):
        if self.feed_in_tariff:
            solar_savings = round(self.total_export * self.feed_in_tariff, 2)
            self.set_state("sensor.daily_solar_savings", state=solar_savings, attributes={
                "unit_of_measurement": "$",
                "device_class": "monetary",
                "friendly_name": "Daily Solar Savings",
                "state_class": "total",
                "icon": "mdi:currency-usd"
            })
            self.calculate_total_bill()

    def calculate_import(self):
        demand_charge = round(self.monthly_peak_usage * self.get_demand_rate(), 2)
        usage_charge = round(float(self.get_state("sensor.daily_usage_charge") or 0), 2)
        # If its between midnight and 1am, only give the usage charge. This will help out on the energy dashboard
        if datetime.datetime.now().hour < 1 and datetime.datetime.now().minute < 1:
            import_charge = 0
        elif datetime.datetime.now().hour < 1:
            import_charge = usage_charge
        else:
            import_charge = round(self.supply_charge + usage_charge + demand_charge, 2)
        return import_charge

    def calculate_total_bill(self):
        demand_charge = round(self.monthly_peak_usage * self.get_demand_rate(), 2)
        usage_charge = round(float(self.get_state("sensor.daily_usage_charge") or 0), 2)
        solar_savings = round(float(self.get_state("sensor.daily_solar_savings") or 0), 2)
        #total_bill = round(self.supply_charge + usage_charge + demand_charge - solar_savings, 2)
        #import_charge = round(self.supply_charge + usage_charge + demand_charge, 2)
        import_charge = self.calculate_import()
        total_bill = import_charge - solar_savings
        self.set_state("sensor.daily_demand_charge", state=demand_charge, attributes={
            "unit_of_measurement": "$",
            "device_class": "monetary",
            "friendly_name": "Daily Demand Charge",
            "state_class": "total",
            "icon": "mdi:currency-usd"
        })
        self.set_state("sensor.daily_total_bill", state=total_bill, attributes={
            "unit_of_measurement": "$",
            "device_class": "monetary",
            "friendly_name": "Daily Total Bill",
            "state_class": "total",
            "icon": "mdi:currency-usd"
        })
        self.set_state("sensor.daily_import_charge", state=import_charge, attributes={
            "unit_of_measurement": "$",
            "device_class": "monetary",
            "friendly_name": "Daily Import Charge",
            "state_class": "total_increasing",
            "icon": "mdi:currency-usd"
        })
        self.log(f"Daily bill: Supply charge: ${self.supply_charge:.2f}, Usage charge: ${usage_charge:.2f}, Demand charge: ${demand_charge:.2f}, Solar savings: -${solar_savings:.2f}, Total: ${total_bill:.2f}")

    def calculate_usage_charge(self):
        current_time = datetime.datetime.now().time()
        if self.is_peak_period(current_time):
            return self.total_import * self.usage_rate_peak
        elif self.is_shoulder_period(current_time):
            return self.total_import * self.usage_rate_shoulder
        else:
            return self.total_import * self.usage_rate_off_peak

    def get_demand_rate(self):
        current_date = datetime.datetime.now().date()
        if self.is_high_season(current_date):
            return self.demand_rate_high_season
        elif self.is_temperate_season(current_date):
            return self.demand_rate_temperate_season
        else:
            return self.demand_rate_low_season

    def is_peak_period(self, current_time):
        peak_start = datetime.datetime.strptime(self.peak_start_time, "%H:%M").time()
        peak_end = datetime.datetime.strptime(self.peak_end_time, "%H:%M").time()
        return peak_start <= current_time <= peak_end and self.is_weekday()

    def is_shoulder_period(self, current_time):
        shoulder_start = datetime.datetime.strptime(self.shoulder_start_time, "%H:%M").time()
        shoulder_end = datetime.datetime.strptime(self.shoulder_end_time, "%H:%M").time()
        return (shoulder_start <= current_time < peak_start or peak_end <= current_time < shoulder_end and self.is_weekday()) or (shoulder_start <= current_time < shoulder_end and not self.is_weekday())

    def is_off_peak_period(self, current_time):
        return not (self.is_peak_period(current_time) or self.is_shoulder_period(current_time))

    def is_weekday(self):
        return datetime.datetime.now().weekday() < 5

    def is_high_season(self, current_date):
        high_season_start = datetime.datetime.strptime(self.high_season_start_date, "%m-%d").date().replace(year=current_date.year)
        high_season_end = datetime.datetime.strptime(self.high_season_end_date, "%m-%d").date().replace(year=current_date.year)
        return high_season_start <= current_date <= high_season_end and self.is_weekday() and self.is_peak_period(datetime.datetime.now().time())

    def is_temperate_season(self, current_date):
        temperate_season_start = datetime.datetime.strptime(self.temperate_season_start_date, "%m-%d").date().replace(year=current_date.year)
        temperate_season_end = datetime.datetime.strptime(self.temperate_season_end_date, "%m-%d").date().replace(year=current_date.year)
        return temperate_season_start <= current_date <= temperate_season_end

    def is_winter_season(self, current_date):
        winter_season_start = datetime.datetime.strptime(self.winter_season_start_date, "%m-%d").date().replace(year=current_date.year)
        winter_season_end = datetime.datetime.strptime(self.winter_season_end_date, "%m-%d").date().replace(year=current_date.year)
        return winter_season_start <= current_date <= winter_season_end

    def reset_daily_totals(self, kwargs):
        self.total_import = 0
        self.total_export = 0
        self.total_solar_generated = 0 if self.solar_sensor else 0
        self.total_demand = 0
        self.previous_import = float(self.get_state(self.import_sensor) or 0)
        self.previous_export = float(self.get_state(self.export_sensor) or 0)
        self.previous_solar = float(self.get_state(self.solar_sensor) or 0) if self.solar_sensor else 0
        self.set_state("sensor.daily_usage_charge", state=0)
        self.set_state("sensor.daily_solar_savings", state=0)
        self.set_state("sensor.daily_total_bill", state=0)
        self.set_state("sensor.daily_demand_charge", state=0)
        self.set_state("sensor.daily_import_charge", state=0, attributes={
                "last_reset": datetime.datetime.now().isoformat()
            })
        if self.solar_sensor:
            self.set_state("sensor.daily_solar_generated", state=0)
        self.peak_usage_window = []
        self.save_cache()

    def calculate_peak_usage(self, kwargs):
        if self.peak_usage_window:
            self.peak_usage = max(self.peak_usage_window)
            self.peak_usage_window = []
            self.log(f"Calculated peak usage for the last 30 minutes: {self.peak_usage} kW")
