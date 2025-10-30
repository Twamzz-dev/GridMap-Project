# solar_generator.py
import random
from datetime import datetime, timedelta
from typing import List, Dict
import os
import sys
from .constants import *
from .utils import *

# Add the parent directory to Python path to make imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)


class SolarDataSimulator:
    """
    Advanced solar simulator: supports region/seasonal weather, temperature, soiling, degradation, faults,
    grid curtailment, partial-string loss, maintenance, and research-grade noise controls.
    """
    def __init__(self, region_seed=None):
        self.locations = SOLAR_CONSTANTS
        # Optionally, seed by date or region for reproducibility
        self.region_seed = region_seed

    def clear_sky_irradiance(self, lat, date, hour):
        # (7) Basic clear-sky PV formula for Kenya: output in kW/kWp
        # For demo, use cos-rule: max(0, cos((hour-12)*pi/12)) * avg_peak
        from math import cos, pi
        sun_angle = cos((hour-12) * pi / 12)
        avg = 1.0  # normalized peak
        return max(0, sun_angle * avg)

    def simulate_weather(self, location, date, hour, region_seed=None):
        # Points 1, 5: weather by location and region (partial correlation seed per day)
        # For advanced R&D: fetch from API or statistical model at this stub.
        if region_seed is not None:
            random.seed(region_seed + int(date.strftime('%Y%m%d')))
        base_weather = get_weather_condition(date + timedelta(hours=hour))
        # TODO: Add rainy/seasonal periods clusters (clouds front)
        return base_weather

    def simulate_temperature(self, location, date, hour):
        # Point 2: cell temperature day pattern (20C at night to 45C peak)
        base_temp = 20 + 15 * max(0, (1 - abs(hour - 13) / 7))  # simple bell
        return base_temp

    def apply_temperature_loss(self, power_watt, cell_temp):
        # -0.4% per degree C above 25
        loss = 1 - max(0, (cell_temp - 25) * 0.004)
        return power_watt * loss

    def apply_soiling(self, power, days_since_clean):
        # Point 10: -1%/day since maintenance, reset every 20 days (simulated event)
        factor = max(0.8, 1 - 0.01 * min(days_since_clean, 20))
        return power * factor

    def panel_degradation(self, original, years_in_service):
        # Nonlinear degradation—add random step increases, then smooth
        extra = 1 - 0.005 * years_in_service - random.uniform(0, 0.01 * max(0, years_in_service - 4))
        return original * extra

    def panel_faults(self, power, hour_idx):
        # Point 6, 11: string or full faults (mix)
        # Full outage 0.5%/hr, partial string 2%/hr, up to -50%
        roll = random.random()
        if roll < 0.005:
            return 0  # total fault
        elif roll < 0.025:
            return power * random.uniform(0.5, 0.8)  # string derate
        return power

    def behavioral_grid_event(self, power, hour_idx):
        # Point 9: curtailment, battery, external grid events
        # For demo/stub: every 60th hour, grid curtails 30%
        if hour_idx % 60 == 0:
            return power * 0.7
        return power

    def inject_noise(self, power, season, weather):
        # Point 12: improved noise
        base_noise = random.gauss(1, 0.01)
        if weather['condition'] == 'cloudy':
            base_noise *= random.uniform(0.92, 1.02)
        if season in ['long rains', 'short rains']:
            base_noise *= random.uniform(0.97, 1.04)
        return power * base_noise

    def simulate_maintenance_event(self, hour_idx):
        # Every 120 hours do maintenance.
        return hour_idx % 120 == 0

    def generate_hourly_production(
        self,
        system_capacity_kw: float,
        location: str,
        date: datetime,
        installation_year: int = 2023
    ) -> List[Dict]:
        if location not in self.locations:
            raise ValueError(f"Location {location} not supported")
        loc_data = self.locations[location]
        hourly_data = []
        years_in_operation = date.year - installation_year
        days_since_clean = random.randint(0, 25)  # start random soiling phase
        for hour in range(24):
            timestamp = date.replace(hour=hour, minute=0, second=0)
            # 1. Clear sky max (theoretical)
            cs_factor = self.clear_sky_irradiance(loc_data['latitude'], date, hour)
            # 2. Weather (region-season)
            weather = self.simulate_weather(location, date, hour, region_seed=self.region_seed)
            # 3. Cell temperature affects output
            cell_temp = self.simulate_temperature(location, date, hour)
            # 4. Start with max possible
            actual_power = system_capacity_kw * cs_factor
            # 5. Weather effect
            actual_power *= weather['efficiency']
            # 6. Temp derate
            actual_power = self.apply_temperature_loss(actual_power, cell_temp)
            # 7. Soiling loss
            actual_power = self.apply_soiling(actual_power, days_since_clean)
            # 8. Panel degradation
            actual_power = self.panel_degradation(actual_power, years_in_operation)
            # 9. Partial-string/random faults
            actual_power = self.panel_faults(actual_power, hour)
            # 10. Behavioral/grid events
            actual_power = self.behavioral_grid_event(actual_power, hour)
            # 11. Advanced noise
            # (season from seasonal variation stub, could pass as arg)
            actual_power = self.inject_noise(actual_power, season='long rains' if date.month in [3,4,5,10,11,12] else 'dry', weather=weather)
            # 12. Clamp negatives, capacity
            actual_power = max(0, min(actual_power, system_capacity_kw))
            # 13. Random faults: quick sim outage
            if random.random() < 0.003:
                actual_power = 0
            # 14. Simulate maintenance events
            if self.simulate_maintenance_event(hour):
                days_since_clean = 0
            else:
                days_since_clean += 1
            hourly_data.append({
                'timestamp': timestamp,
                'power_kw': round(actual_power, 2),
                'weather': weather['condition'],
                'cell_temp_c': round(cell_temp,2),
                'soiling_days': days_since_clean,
            })
        return hourly_data

    
    def generate_daily_total(
        self,
        system_capacity_kw: float,
        location: str,
        date: datetime
    ) -> float:
        """
        Calculate total energy production for a day (in kWh).
        """
        hourly_data = self.generate_hourly_production(
            system_capacity_kw,
            location,
            date
        )
        
        total_kwh = sum(hour['power_kw'] for hour in hourly_data)
        return round(total_kwh, 2)
    
    
    def generate_date_range(
        self,
        system_capacity_kw: float,
        location: str,
        start_date: datetime,
        days: int = 7
    ) -> List[Dict]:
        """
        Generate production data for multiple days.
        
        Returns flattened list of all hourly readings.
        """
        all_data = []
        
        for day in range(days):
            current_date = start_date + timedelta(days=day)
            daily_data = self.generate_hourly_production(
                system_capacity_kw,
                location,
                current_date
            )
            all_data.extend(daily_data)
        
        return all_data