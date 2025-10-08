#!/usr/bin/env python3
"""
Add New York City back to the final list and reorder
"""

import csv

def main():
    # Read the cleaned cities
    cities = []
    with open('cities_cleaned.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if row:
                cities.append(row[0])
    
    # Add New York City if it's not already there
    if 'New York' not in cities:
        cities.append('New York')
        print("Added New York City to the list")
    
    # Approximate longitude-based ordering for west to east
    city_longitudes = {
        # California (West Coast) - around -118 to -120
        'Los Angeles': -118.2437,
        'Santa Monica': -118.4912,
        'San Gabriel': -118.1088,
        'Glendora': -117.8653,
        'Rancho Cucamonga': -117.5859,
        'Fontana': -117.4359,
        'Cajon': -117.4,
        'Hesperia': -117.3006,
        'Apple Valley': -117.1859,
        'Lucerne Valley': -116.9667,
        'Yucca Valley': -116.4167,
        'Twentynine Palms': -116.0547,
        
        # Arizona - around -111 to -114
        'Bullhead City': -114.5686,
        'Golden Valley': -114.1236,
        'New Kingman-Butler': -114.0167,
        'Flagstaff': -111.6513,
        'Sedona': -111.7610,
        'Holbrook': -110.1623,
        'Winslow': -110.6973,
        'Sun Valley': -110.0,
        
        # New Mexico - around -105 to -108
        'Albuquerque': -106.6504,
        'Gallup': -108.7426,
        'Madrid': -106.1536,
        'Tesuque': -105.9208,
        'Sombrillo': -106.0,
        'Valle Escondido': -105.5,
        'Eagle Nest': -105.4667,
        'Rayado': -105.0,
        'Springer': -104.5,
        'Stillwater': -104.0,
        
        # Oklahoma - around -95 to -97
        'Tulsa': -95.9928,
        'Sapulpa': -95.8170,
        'Broken Arrow': -95.8170,
        
        # Missouri/Arkansas - around -90 to -95
        'Fayetteville': -94.1574,
        'Mountain Home': -92.3853,
        'Fairdealing': -90.0,
        'Poplar Bluff': -90.3926,
        'Dexter': -89.9587,
        'Grayridge': -89.0,
        'Carrier Mills': -88.0,
        'Eldorado': -88.0,
        'Norris City': -88.0,
        'Crossville': -88.0,
        'New Burnside': -88.0,
        'Vienna': -88.0,
        'Mound City': -88.0,
        
        # Indiana - around -87
        'Vincennes': -87.5286,
        'Bicknell': -87.3078,
        'Keensburg': -87.0,
        'Grayville': -87.0,
        
        # Ohio - around -82 to -84
        'Dayton': -84.1916,
        'Beavercreek': -84.0633,
        'Cedarville': -83.8083,
        'Zanesville': -82.0132,
        'New Lexington': -82.2081,
        
        # Pennsylvania - around -75 to -80
        'Allentown': -75.4638,
        'Bethlehem': -75.3705,
        'East Hanover Township': -76.0,
        'Bethel Township': -76.0,
        'Greenwich Township': -75.0,
        'Jefferson Township': -75.0,
        'Donegal Township': -79.0,
        'Dublin Township': -79.0,
        'Elizabeth Township': -79.0,
        'East Huntingdon Township': -79.0,
        'Mount Pleasant Township': -79.0,
        'Susquehanna Township': -76.0,
        'Upper Bern Township': -76.0,
        'West Pennsboro Township': -77.0,
        'Lurgan Township': -77.0,
        'Brush Creek Township': -78.0,
        'Stonycreek Township': -78.0,
        'North Franklin Township': -80.0,
        'Nottingham Township': -80.0,
        'Napier Township': -78.0,
        'Monroe Township': -76.0,
        'Metal Township': -77.0,
        
        # New York/New Jersey - around -74
        'Hackensack': -74.0431,
        'Rockaway Township': -74.0,
        'Fairfield': -74.0,
        'New York': -74.0060,  # NYC
        
        # West Virginia - around -80
        'Wheeling': -80.7209,
    }
    
    # Sort cities by longitude (west to east)
    cities_with_longitude = []
    for city in cities:
        if city in city_longitudes:
            cities_with_longitude.append((city, city_longitudes[city]))
        else:
            # For cities not in our list, estimate based on name patterns
            if 'Township' in city or 'Pennsylvania' in city:
                cities_with_longitude.append((city, -77.0))  # Rough PA longitude
            else:
                cities_with_longitude.append((city, -100.0))  # Default middle longitude
    
    # Sort by longitude (west to east)
    cities_with_longitude.sort(key=lambda x: x[1])
    
    print("=== FINAL CITIES IN ROUTE ORDER (WEST TO EAST) ===")
    print(f"Total cities: {len(cities_with_longitude)}")
    print()
    
    for i, (city, longitude) in enumerate(cities_with_longitude, 1):
        print(f"{i:2d}. {city}")
    
    # Save final results
    with open('cities_final_route.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Order', 'City', 'Longitude'])
        for i, (city, longitude) in enumerate(cities_with_longitude, 1):
            writer.writerow([i, city, longitude])
    
    with open('cities_final_route.txt', 'w') as f:
        f.write("Final cities visited during cross-country bike trip (west to east):\n\n")
        for i, (city, longitude) in enumerate(cities_with_longitude, 1):
            f.write(f"{i:2d}. {city}\n")
    
    print(f"\nFinal results saved to:")
    print(f"  - cities_final_route.csv")
    print(f"  - cities_final_route.txt")

if __name__ == "__main__":
    main()
