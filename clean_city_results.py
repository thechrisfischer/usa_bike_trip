#!/usr/bin/env python3
"""
Clean up city results by filtering out highways, road numbers, and other non-city entries
"""

import csv
import re
from typing import Set, List

def is_likely_city(name: str) -> bool:
    """Determine if a name is likely a city/town rather than a highway or road."""
    
    # Filter out obvious non-cities
    non_city_patterns = [
        r'^\d+$',  # Pure numbers
        r'^\d+\s*$',  # Numbers with spaces
        r'Highway',  # Highway names
        r'Road',  # Road names
        r'Trail',  # Trail names
        r'Expressway',  # Expressway names
        r'Division',  # Division names
        r'^US\s+\d+',  # US Highway numbers
        r'^SR\s+\d+',  # State Route numbers
        r'^FM\s+\d+',  # Farm to Market roads
        r'^I\s+\d+',  # Interstate numbers
        r'^NM\s+\d+',  # New Mexico route numbers
        r'^AR\s+\d+',  # Arkansas route numbers
        r'^MO\s+\d+',  # Missouri route numbers
        r'Frontage Road',  # Frontage roads
        r'Memorial Highway',  # Memorial highways
        r'Veterans Highway',  # Veterans highways
        r'Jim Thorpe Memorial Highway',  # Specific memorial highways
        r'Purple Heart Trail',  # Purple Heart Trail
        r'42nd.*Division.*Highway',  # Division highways
        r'Prescott.*Flagstaff Highway',  # Intercity highways
        r'Bullhead City.*Kingman Highway',  # Intercity highways
        r'Old Woman Springs Road',  # Road names
        r'Petrified Forest Road',  # Road names
        r'Kelbaker Road',  # Road names
        r'Crookton Road',  # Road names
        r'Rabbit Road',  # Road names
        r'Prairie Grass Trail',  # Trail names
        r'Springer Highway',  # Highway names
        r'Hualapai Veterans Highway',  # Veterans highways
        r'Jim Thorpe Memorial Highway',  # Memorial highways
        r'Mannford Expressway',  # Expressway names
        r'Marques Haynes Highway',  # Highway names
        r'Jack Choate Highway',  # Highway names
        r'US Highway 64',  # US Highway names
        r'US 412;AR 21',  # Route combinations
        r'US 60;US 62;MO 77',  # Route combinations
        r'US 83',  # US routes
        r'US 87',  # US routes
        r'US 64',  # US routes
        r'SR 59',  # State routes
        r'FM 1573',  # Farm to Market
        r'FM 281',  # Farm to Market
        r'FM 520',  # Farm to Market
        r'NM 68',  # New Mexico routes
        r'I 40',  # Interstate
        r'Frontage Road',  # Frontage roads
        r'Continental Divide',  # Geographic features
        r'Fort Defiance Agency',  # Government agencies
        r'Church Rock',  # Geographic features
        r'Chief Rancho',  # Geographic features
        r'Antares',  # Geographic features
        r'Crozier',  # Geographic features
        r'Peach Springs',  # Geographic features
        r'Mesita',  # Geographic features
        r'Cedar Crest',  # Geographic features
        r'Ware',  # Geographic features
        r'Hitt',  # Geographic features
        r'McKibben',  # Geographic features
        r'Capps',  # Geographic features
        r'Coburn',  # Geographic features
        r'Thompson Corner',  # Geographic features
        r'Strawberry Spring',  # Geographic features
        r'Sand Barrens',  # Geographic features
        r'Sandia Haven',  # Geographic features
        r'Rabbit Road',  # Road names
        r'Rally Hill',  # Geographic features
        r'Eros',  # Geographic features
        r'Freedom',  # Geographic features
        r'Paragon',  # Geographic features
        r'Bud',  # Geographic features
        r'Glenwood',  # Geographic features
        r'Kirkersville',  # Geographic features
        r'Jacksontown',  # Geographic features
        r'New Concord',  # Geographic features
        r'Lore City',  # Geographic features
        r'Quaker City',  # Geographic features
        r'Lilly Chapel',  # Geographic features
        r'Tuttle',  # Geographic features
        r'Huntsville',  # Geographic features
        r'New Grand Chain',  # Geographic features
        r'Vienna',  # Geographic features
        r'New Burnside',  # Geographic features
        r'Carrier Mills',  # Geographic features
        r'Eldorado',  # Geographic features
        r'Norris City',  # Geographic features
        r'Crossville',  # Geographic features
        r'Poplar Bluff',  # Geographic features
        r'Dexter',  # Geographic features
        r'Grayridge',  # Geographic features
        r'Sapulpa',  # Geographic features
        r'Broken Arrow',  # Geographic features
        r'Mound City',  # Geographic features
        r'New Grand Chain',  # Geographic features
        r'Vienna',  # Geographic features
        r'New Burnside',  # Geographic features
        r'Carrier Mills',  # Geographic features
        r'Eldorado',  # Geographic features
        r'Norris City',  # Geographic features
        r'Crossville',  # Geographic features
        r'Poplar Bluff',  # Geographic features
        r'Dexter',  # Geographic features
        r'Grayridge',  # Geographic features
        r'Sapulpa',  # Geographic features
        r'Broken Arrow',  # Geographic features
        r'Mound City',  # Geographic features
    ]
    
    # Check against patterns
    for pattern in non_city_patterns:
        if re.search(pattern, name, re.IGNORECASE):
            return False
    
    # Must have at least 2 characters and not be all numbers
    if len(name) < 2 or name.isdigit():
        return False
    
    # Must not be just numbers with spaces
    if re.match(r'^\d+\s*$', name):
        return False
    
    return True

def clean_city_list(cities: List[str]) -> List[str]:
    """Clean and deduplicate city list."""
    
    # Filter out non-cities
    likely_cities = [city for city in cities if is_likely_city(city)]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_cities = []
    for city in likely_cities:
        if city not in seen:
            seen.add(city)
            unique_cities.append(city)
    
    return unique_cities

def main():
    # Read the comprehensive results
    cities = []
    with open('cities_comprehensive.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if row:  # Skip empty rows
                cities.append(row[0])
    
    print(f"Original list: {len(cities)} entries")
    
    # Clean the list
    clean_cities = clean_city_list(cities)
    
    print(f"Cleaned list: {len(clean_cities)} actual cities/towns")
    print("\nCleaned cities list:")
    print("=" * 50)
    
    for i, city in enumerate(clean_cities, 1):
        print(f"{i:2d}. {city}")
    
    # Save cleaned results
    with open('cities_cleaned.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['City'])
        for city in clean_cities:
            writer.writerow([city])
    
    with open('cities_cleaned.txt', 'w') as f:
        f.write("Cleaned cities visited during cross-country bike trip:\n\n")
        for i, city in enumerate(clean_cities, 1):
            f.write(f"{i:2d}. {city}\n")
    
    print(f"\nCleaned results saved to:")
    print(f"  - cities_cleaned.csv")
    print(f"  - cities_cleaned.txt")

if __name__ == "__main__":
    main()
