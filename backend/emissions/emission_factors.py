import math

FUEL_FACTORS = {
    'diesel':       (2.68, 'kg CO2e/L',  'Scope 1', 'IPCC 2006 AR5 GWP100, diesel combustion'),
    'hsd':          (2.68, 'kg CO2e/L',  'Scope 1', 'IPCC 2006 AR5 GWP100, HSD diesel'),
    'furnace oil':  (3.21, 'kg CO2e/L',  'Scope 1', 'IPCC 2006 AR5, furnace/heavy fuel oil'),
    'natural gas':  (2.02, 'kg CO2e/m3', 'Scope 1', 'IPCC 2006 AR5, natural gas combustion'),
    'erdgas':       (2.02, 'kg CO2e/m3', 'Scope 1', 'IPCC 2006 AR5, Erdgas (natural gas)'),
    'lpg':          (1.51, 'kg CO2e/kg', 'Scope 1', 'IPCC 2006 AR5, LPG combustion'),
    'petrol':       (2.31, 'kg CO2e/L',  'Scope 1', 'IPCC 2006 AR5, petrol/gasoline'),
}

ELECTRICITY_FACTOR = (0.716, 'kg CO2e/kWh', 'Scope 2', 'CEA India Grid Emission Factor 2022-23')

TRAVEL_FACTORS = {
    'economy_flight':  (0.151, 'kg CO2e/pkm',        'Scope 3', 'DEFRA 2023 economy class with radiative forcing'),
    'business_flight': (0.429, 'kg CO2e/pkm',        'Scope 3', 'DEFRA 2023 business class with radiative forcing'),
    'first_flight':    (0.604, 'kg CO2e/pkm',        'Scope 3', 'DEFRA 2023 first class with radiative forcing'),
    'hotel':           (31.4,  'kg CO2e/room-night',  'Scope 3', 'Cornell Hotel Sustainability Benchmarking Index 2023'),
    'car_rental':      (0.171, 'kg CO2e/km',          'Scope 3', 'DEFRA 2023 average car'),
    'taxi':            (0.149, 'kg CO2e/km',          'Scope 3', 'DEFRA 2023 taxi'),
}

AIRPORT_COORDS = {
    'DEL': (28.5562,   77.1000),
    'BOM': (19.0896,   72.8656),
    'BLR': (13.1986,   77.7066),
    'HYD': (17.2403,   78.4294),
    'MAA': (12.9941,   80.1709),
    'CCU': (22.6527,   88.4467),
    'PNQ': (18.5822,   73.9197),
    'AMD': (23.0731,   72.6347),
    'COK': (10.1520,   76.4019),
    'SIN': ( 1.3644,  103.9915),
    'DXB': (25.2532,   55.3657),
    'LHR': (51.4775,   -0.4614),
    'JFK': (40.6413,  -73.7781),
    'CDG': (49.0097,    2.5479),
    'SFO': (37.6213, -122.3790),
    'NRT': (35.7720,  140.3929),
    'SYD': (-33.9399, 151.1753),
}


def haversine_km(iata1: str, iata2: str):
    """Great-circle distance between two IATA airport codes. Returns None if unknown."""
    c1 = AIRPORT_COORDS.get(iata1.upper())
    c2 = AIRPORT_COORDS.get(iata2.upper())
    if not c1 or not c2:
        return None
    R = 6371.0
    lat1, lon1 = math.radians(c1[0]), math.radians(c1[1])
    lat2, lon2 = math.radians(c2[0]), math.radians(c2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def get_fuel_factor(material_description: str):
    """Case-insensitive substring match. Returns (factor, unit, scope, citation) or None."""
    if not material_description:
        return None
    desc = material_description.lower()
    for keyword, value in FUEL_FACTORS.items():
        if keyword in desc:
            return value
    return None
