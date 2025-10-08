#!/usr/bin/env python3
"""
Order cities by the actual route taken during the cross-country bike trip
"""

import gpxpy
import os
import csv
from typing import List, Tuple, Dict
from geopy.geocoders import Nominatim
import time
import random

class RouteOrderer:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="route_orderer")
        self.city_cache = {}
        
    def load_city_cache(self):
        """Load cached city data from previous runs."""
        try:
            with open('comprehensive_city_cache.json', 'r') as f:
                import json
                cache = json.load(f)
                # Convert cache to coordinate -> city mapping
                for coord_key, city in cache.items():
                    if city:  # Only include successful lookups
                        lat, lon = map(float, coord_key.split(','))
                        self.city_cache[(lat, lon)] = city
        except:
            pass
    
    def extract_route_coordinates(self, gpx_directory: str = 'gpx') -> List[Tuple[float, float, str]]:
        """Extract coordinates with timestamps from all GPX files in chronological order."""
        all_coordinates = []
        gpx_files = sorted([f for f in os.listdir(gpx_directory) if f.endswith('.gpx')])
        
        print(f"Processing {len(gpx_files)} GPX files in order...")
        
        for gpx_file in gpx_files:
            file_path = os.path.join(gpx_directory, gpx_file)
            with open(file_path, 'r') as f:
                gpx = gpxpy.parse(f)
                for track in gpx.tracks:
                    for segment in track.segments:
                        for point in segment.points:
                            if point.time:
                                all_coordinates.append((point.latitude, point.longitude, point.time, gpx_file))
        
        # Sort by timestamp
        all_coordinates.sort(key=lambda x: x[2])
        print(f"Total coordinates with timestamps: {len(all_coordinates)}")
        
        return all_coordinates
    
    def get_city_for_coordinate(self, lat: float, lon: float) -> str:
        """Get city for coordinate, using cache when possible."""
        # Check cache first
        if (lat, lon) in self.city_cache:
            return self.city_cache[(lat, lon)]
        
        # Round to 6 decimal places for cache key
        lat_rounded = round(lat, 6)
        lon_rounded = round(lon, 6)
        
        if (lat_rounded, lon_rounded) in self.city_cache:
            return self.city_cache[(lat_rounded, lon_rounded)]
        
        return None
    
    def find_cities_in_route_order(self, coordinates: List[Tuple[float, float, str, str]]) -> List[Tuple[str, str, str]]:
        """Find cities in the order they appear in the route."""
        cities_found = []
        seen_cities = set()
        
        # Sample coordinates to avoid too many API calls
        step = max(1, len(coordinates) // 500)  # Sample every nth coordinate
        sampled_coords = coordinates[::step]
        
        print(f"Sampling {len(sampled_coords)} coordinates from {len(coordinates)} total")
        
        for i, (lat, lon, timestamp, gpx_file) in enumerate(sampled_coords):
            city = self.get_city_for_coordinate(lat, lon)
            
            if city and city not in seen_cities:
                cities_found.append((city, timestamp.strftime('%Y-%m-%d %H:%M:%S'), gpx_file))
                seen_cities.add(city)
                print(f"Found: {city} at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Progress update
            if i % 50 == 0:
                print(f"Progress: {i}/{len(sampled_coords)} coordinates processed, {len(cities_found)} cities found")
        
        return cities_found
    
    def process_route(self, gpx_directory: str = 'gpx') -> List[Tuple[str, str, str]]:
        """Process the route and return cities in order."""
        self.load_city_cache()
        
        coordinates = self.extract_route_coordinates(gpx_directory)
        cities_in_order = self.find_cities_in_route_order(coordinates)
        
        return cities_in_order

def main():
    orderer = RouteOrderer()
    
    print("=== Ordering Cities by Route ===")
    print("Analyzing GPX files to determine chronological order...")
    print()
    
    cities_in_order = orderer.process_route('gpx')
    
    print(f"\n=== ROUTE ORDERED CITIES ===")
    print(f"Found {len(cities_in_order)} cities in route order:")
    print()
    
    for i, (city, timestamp, gpx_file) in enumerate(cities_in_order, 1):
        print(f"{i:2d}. {city} ({timestamp})")
    
    # Save ordered results
    with open('cities_route_order.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Order', 'City', 'Timestamp', 'GPX_File'])
        for i, (city, timestamp, gpx_file) in enumerate(cities_in_order, 1):
            writer.writerow([i, city, timestamp, gpx_file])
    
    with open('cities_route_order.txt', 'w') as f:
        f.write("Cities visited during cross-country bike trip (in route order):\n\n")
        for i, (city, timestamp, gpx_file) in enumerate(cities_in_order, 1):
            f.write(f"{i:2d}. {city} ({timestamp})\n")
    
    print(f"\nResults saved to:")
    print(f"  - cities_route_order.csv")
    print(f"  - cities_route_order.txt")

if __name__ == "__main__":
    main()
