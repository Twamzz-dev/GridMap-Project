# utility functions for solar energy simulation

import math
import random
from datetime import datetime, timedelta

def calculate_solar_elevation(latitude: float, date: datetime, hour: int) -> float:
    """
    Calculate sun elevation angle for a given location, date, and hour.
    Returns angle in degrees (0-90).
    
    Simplified solar position algorithm.
    """
    # Day of year (1-365)
    day_of_year = date.timetuple().tm_yday
    
    # Declination angle (Earth's tilt effect)
    declination = 23.45 * math.sin(math.radians((360/365) * (day_of_year - 81)))
    
    # Hour angle (sun's position in sky)
    hour_angle = 15 * (hour - 12)  # 15° per hour, noon = 0°
    
    # Solar elevation formula
    elevation = math.asin(
        math.sin(math.radians(latitude)) * math.sin(math.radians(declination)) +
        math.cos(math.radians(latitude)) * math.cos(math.radians(declination)) * 
        math.cos(math.radians(hour_angle))
    )
    
    return max(0, math.degrees(elevation))  # Can't be negative


def get_solar_intensity_factor(elevation_angle: float) -> float:
    """
    Convert sun elevation angle to intensity factor (0-1).
    Uses air mass correction for atmospheric attenuation.
    """
    if elevation_angle <= 0:
        return 0
    
    # Air mass coefficient (atmospheric thickness the light travels through)
    air_mass = 1 / math.sin(math.radians(elevation_angle))
    
    # Simplified intensity calculation
    # At 90° (directly overhead): factor = 1.0
    # As angle decreases, intensity drops due to atmosphere
    intensity = math.pow(0.7, air_mass - 1)
    
    return intensity


def get_weather_condition(date: datetime) -> dict:
    """
    Randomly select weather condition based on probabilities.
    Returns weather type and efficiency multiplier.
    """
    from constants import WEATHER_PATTERNS
    
    rand = random.random()
    cumulative = 0
    
    for condition, details in WEATHER_PATTERNS.items():
        cumulative += details['probability']
        if rand <= cumulative:
            return {
                'condition': condition,
                'efficiency': details['efficiency']
            }
    
    return {'condition': 'sunny', 'efficiency': 1.0}


def apply_seasonal_variation(base_value: float, date: datetime, variation_factor: float) -> float:
    """
    Apply seasonal variation to base production value.
    Kenya has two rainy seasons: March-May and Oct-Dec
    """
    month = date.month
    
    # Seasonal multiplier (1.0 = average, >1 = better, <1 = worse)
    if month in [1, 2, 6, 7, 8, 9]:  # Dry seasons
        multiplier = 1 + (variation_factor * 0.5)
    elif month in [3, 4, 5, 10, 11, 12]:  # Rainy seasons
        multiplier = 1 - (variation_factor * 0.5)
    else:
        multiplier = 1.0
    
    return base_value * multiplier