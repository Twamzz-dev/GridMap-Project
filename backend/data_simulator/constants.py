# Constants for simulating solar panel energy generation in Kenya

# Kenya solar radiation data (kWh/m²/day)
SOLAR_CONSTANTS = {
    'NAIROBI': {
        'latitude': -1.286389,
        'avg_peak_sun_hours': 5.5,  # Annual average
        'seasonal_variation': 0.15,  # ±15% seasonal change
    },
    'MOMBASA': {
        'latitude': -4.043477,
        'avg_peak_sun_hours': 5.8,
        'seasonal_variation': 0.12,
    },
    'KISUMU': {
        'latitude': -0.091702,
        'avg_peak_sun_hours': 5.3,
        'seasonal_variation': 0.18,
    },
    'NAKURU': {
        'latitude': -0.303099,
        'avg_peak_sun_hours': 5.6,
        'seasonal_variation': 0.14,
    }
}

# System efficiency factors
SYSTEM_EFFICIENCY = 0.85  # 85% - accounts for inverter losses, wiring, etc.
PANEL_DEGRADATION_ANNUAL = 0.005  # 0.5% per year

# Weather impact probabilities
WEATHER_PATTERNS = {
    'sunny': {'probability': 0.70, 'efficiency': 1.0},
    'partly_cloudy': {'probability': 0.20, 'efficiency': 0.6},
    'cloudy': {'probability': 0.08, 'efficiency': 0.3},
    'rainy': {'probability': 0.02, 'efficiency': 0.1},
}