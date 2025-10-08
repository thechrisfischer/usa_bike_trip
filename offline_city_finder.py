#!/usr/bin/env python3
"""
Offline City Finder - Uses minimal API calls by leveraging geographic databases
"""

import gpxpy
import json
import os
import math
from collections import defaultdict
import csv
from typing import List, Tuple, Set, Dict
import requests
import time

class OfflineCityFinder:
    def __init__(self):
        self.city_cache = {}
        self.load_offline_data()
    
    def load_offline_data(self):
        """Load offline geographic data for major US cities."""
        # Major US cities with approximate coordinates
        self.major_cities = {
            # California
            (34.0522, -118.2437): "Los Angeles",
            (37.7749, -122.4194): "San Francisco", 
            (34.0522, -118.2437): "Santa Monica",
            (34.1478, -118.1445): "Pasadena",
            (33.6846, -117.8265): "Irvine",
            (33.7701, -118.1937): "Long Beach",
            (34.1808, -118.3090): "Burbank",
            (34.0736, -117.3137): "Fontana",
            (34.1064, -117.5931): "Rancho Cucamonga",
            (34.1064, -117.5931): "Pomona",
            (34.1064, -117.5931): "Victorville",
            
            # Arizona
            (33.4484, -112.0740): "Phoenix",
            (32.2226, -110.9747): "Tucson",
            (35.1983, -111.6513): "Flagstaff",
            (35.1859, -111.6643): "Flagstaff",
            (35.1859, -111.6643): "Kingman",
            (35.1859, -111.6643): "Bullhead City",
            
            # New Mexico
            (35.0844, -106.6504): "Albuquerque",
            (35.6869, -105.9378): "Santa Fe",
            (36.4072, -105.5731): "Taos",
            (35.5281, -108.7426): "Gallup",
            
            # Oklahoma
            (36.1540, -95.9928): "Tulsa",
            (35.4676, -97.5164): "Oklahoma City",
            (35.7478, -95.3697): "Tahlequah",
            
            # Arkansas
            (35.2010, -91.8318): "St. Francisville",
            
            # Tennessee
            (36.1627, -86.7816): "Nashville",
            (35.0456, -85.3097): "Chattanooga",
            
            # Ohio
            (39.9612, -82.9988): "Columbus",
            (39.7589, -84.1916): "Dayton",
            (39.1031, -84.5120): "Cincinnati",
            (39.9612, -82.9988): "Xenia",
            (39.9612, -82.9988): "Zanesville",
            
            # Pennsylvania
            (40.7128, -74.0060): "New York",  # Close to PA border
            (40.2732, -76.8847): "Harrisburg",
            (40.2732, -76.8847): "Allentown",
            (40.2732, -76.8847): "Bethlehem",
            (40.2732, -76.8847): "Easton",
        }
    
    def find_nearest_city(self, lat: float, lon: float, max_distance_km: float = 50.0) -> str:
        """Find the nearest major city within max_distance_km."""
        min_distance = float('inf')
        nearest_city = None
        
        for city_lat, city_lon in self.major_cities:
            distance = self.calculate_distance((lat, lon), (city_lat, city_lon))
            if distance < min_distance and distance <= max_distance_km:
                min_distance = distance
                nearest_city = self.major_cities[(city_lat, city_lon)]
        
        return nearest_city
    
    def calculate_distance(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """Calculate distance between two coordinates in kilometers."""
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        
        R = 6371  # Earth's radius in kilometers
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2) * math.sin(dlon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    def extract_coordinates_from_gpx(self, gpx_file_path: str) -> List[Tuple[float, float]]:
        """Extract coordinates from GPX file."""
        coordinates = []
        with open(gpx_file_path, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        coordinates.append((point.latitude, point.longitude))
        return coordinates
    
    def process_gpx_files_offline(self, gpx_directory: str = 'gpx') -> Set[str]:
        """Process GPX files using offline city detection."""
        all_coordinates = []
        gpx_files = [f for f in os.listdir(gpx_directory) if f.endswith('.gpx')]
        
        print(f"Processing {len(gpx_files)} GPX files...")
        
        for gpx_file in gpx_files:
            file_path = os.path.join(gpx_directory, gpx_file)
            coordinates = self.extract_coordinates_from_gpx(file_path)
            all_coordinates.extend(coordinates)
            print(f"Extracted {len(coordinates)} points from {gpx_file}")
        
        # Sample coordinates to reduce processing
        if len(all_coordinates) > 1000:
            step = len(all_coordinates) // 1000
            all_coordinates = all_coordinates[::step]
            print(f"Sampled to {len(all_coordinates)} coordinates")
        
        cities = set()
        for lat, lon in all_coordinates:
            city = self.find_nearest_city(lat, lon)
            if city:
                cities.add(city)
                print(f"Found: {city}")
        
        return cities

def main():
    finder = OfflineCityFinder()
    cities = finder.process_gpx_files_offline('gpx')
    
    print(f"\nFound {len(cities)} cities using offline method:")
    for city in sorted(cities):
        print(f"  - {city}")
    
    # Save results
    with open('cities_offline.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['City'])
        for city in sorted(cities):
            writer.writerow([city])

if __name__ == "__main__":
    main()
