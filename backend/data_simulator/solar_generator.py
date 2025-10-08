# solar_generator.py
import random
from datetime import datetime, timedelta
from typing import List, Dict
from constants import *
from utils import *


class SolarDataSimulator:
    """
    Generates realistic solar production data for Kenyan installations.
    """
    
    def __init__(self):
        """Initialize the simulator."""
        self.locations = SOLAR_CONSTANTS
    
    
    def generate_hourly_production(
        self, 
        system_capacity_kw: float,
        location: str,
        date: datetime,
        installation_year: int = 2023
    ) -> List[Dict]:
        """
        Generate 24 hours of production data for a single day.
        
        Args:
            system_capacity_kw: System size in kilowatts
            location: City name (must be in SOLAR_CONSTANTS)
            date: Date to generate data for
            installation_year: Year system was installed (for degradation)
        
        Returns:
            List of 24 hourly readings with timestamp and power_kw
        """
        
        if location not in self.locations:
            raise ValueError(f"Location {location} not supported")
        
        loc_data = self.locations[location]
        hourly_data = []
        
        # Get weather for the day (stays consistent for 24 hours)
        weather = get_weather_condition(date)
        
        # Calculate system degradation
        years_in_operation = date.year - installation_year
        degradation = 1 - (PANEL_DEGRADATION_ANNUAL * years_in_operation)
        
        # Generate each hour
        for hour in range(24):
            timestamp = date.replace(hour=hour, minute=0, second=0)
            
            # Calculate solar geometry
            elevation = calculate_solar_elevation(
                loc_data['latitude'], 
                date, 
                hour
            )
            
            # Get intensity factor from sun position
            intensity = get_solar_intensity_factor(elevation)
            
            # Calculate theoretical maximum power for this hour
            theoretical_max = system_capacity_kw * intensity
            
            # Apply efficiency factors
            actual_power = theoretical_max * SYSTEM_EFFICIENCY
            actual_power *= weather['efficiency']
            actual_power *= degradation
            
            # Apply seasonal variation
            actual_power = apply_seasonal_variation(
                actual_power,
                date,
                loc_data['seasonal_variation']
            )
            
            # Add small random noise (±2%) for realism
            # noise = random.uniform(0.98, 1.02)
            # actual_power *= noise
            
            # Ensure non-negative and not exceeding capacity
            actual_power = max(0, min(actual_power, system_capacity_kw))
            
            hourly_data.append({
                'timestamp': timestamp,
                'power_kw': round(actual_power, 2),
                'weather': weather['condition'],
                'solar_elevation': round(elevation, 2)
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