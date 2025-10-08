#!/usr/bin/env python3
"""
Hybrid City Finder - Combines offline detection with minimal API calls
"""

import gpxpy
import json
import os
import math
from collections import defaultdict
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
import random
from typing import List, Tuple, Set, Dict
import csv

class HybridCityFinder:
    def __init__(self, cache_file='hybrid_city_cache.json'):
        self.cache_file = cache_file
        self.cache = self.load_cache()
        self.geolocator = Nominatim(user_agent="hybrid_city_finder")
        
        # Major cities database for offline detection
        self.major_cities = {
            # California
            (34.0522, -118.2437): "Los Angeles",
            (37.7749, -122.4194): "San Francisco", 
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
            
            # Ohio
            (39.9612, -82.9988): "Columbus",
            (39.7589, -84.1916): "Dayton",
            (39.1031, -84.5120): "Cincinnati",
            (39.9612, -82.9988): "Xenia",
            (39.9612, -82.9988): "Zanesville",
            
            # Pennsylvania
            (40.2732, -76.8847): "Harrisburg",
            (40.2732, -76.8847): "Allentown",
            (40.2732, -76.8847): "Bethlehem",
            (40.2732, -76.8847): "Easton",
        }
    
    def load_cache(self) -> Dict:
        """Load cached city data."""
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_cache(self):
        """Save city cache to file."""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
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
    
    def find_nearest_major_city(self, lat: float, lon: float, max_distance_km: float = 30.0) -> str:
        """Find nearest major city using offline database."""
        min_distance = float('inf')
        nearest_city = None
        
        for city_lat, city_lon in self.major_cities:
            distance = self.calculate_distance((lat, lon), (city_lat, city_lon))
            if distance < min_distance and distance <= max_distance_km:
                min_distance = distance
                nearest_city = self.major_cities[(city_lat, city_lon)]
        
        return nearest_city
    
    def get_city_from_api(self, lat: float, lon: float) -> str:
        """Get city from API with caching."""
        coord_key = f"{lat:.6f},{lon:.6f}"
        
        if coord_key in self.cache:
            return self.cache[coord_key]
        
        try:
            location = self.geolocator.reverse((lat, lon), language='en')
            if location and 'city' in location.raw['address']:
                city = location.raw['address']['city']
                self.cache[coord_key] = city
                return city
        except Exception as e:
            print(f"API error for {lat}, {lon}: {e}")
        
        self.cache[coord_key] = None
        return None
    
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
    
    def extract_coordinates_from_all_gpx(self, gpx_directory: str) -> List[Tuple[float, float]]:
        """Extract coordinates from all GPX files."""
        all_coordinates = []
        gpx_files = [f for f in os.listdir(gpx_directory) if f.endswith('.gpx')]
        
        print(f"Found {len(gpx_files)} GPX files")
        
        for gpx_file in gpx_files:
            file_path = os.path.join(gpx_directory, gpx_file)
            coordinates = self.extract_coordinates_from_gpx(file_path)
            all_coordinates.extend(coordinates)
            print(f"Extracted {len(coordinates)} points from {gpx_file}")
        
        return all_coordinates
    
    def smart_sample_coordinates(self, coordinates: List[Tuple[float, float]], 
                               max_samples: int = 100) -> List[Tuple[float, float]]:
        """Smart sampling that ensures geographic distribution."""
        if len(coordinates) <= max_samples:
            return coordinates
        
        # Take every nth coordinate to get a good sample
        step = len(coordinates) // max_samples
        sampled = coordinates[::max(1, step)]
        
        # Always include first and last
        if coordinates[0] not in sampled:
            sampled.insert(0, coordinates[0])
        if coordinates[-1] not in sampled:
            sampled.append(coordinates[-1])
        
        return sampled
    
    def find_cities_hybrid(self, coordinates: List[Tuple[float, float]]) -> Set[str]:
        """Find cities using hybrid approach: offline first, then API for gaps."""
        print(f"Processing {len(coordinates)} coordinates...")
        
        # Smart sampling
        sampled_coords = self.smart_sample_coordinates(coordinates, max_samples=80)
        print(f"Sampled to {len(sampled_coords)} coordinates")
        
        cities = set()
        api_calls = 0
        
        for i, (lat, lon) in enumerate(sampled_coords):
            # Try offline detection first
            city = self.find_nearest_major_city(lat, lon, max_distance_km=25.0)
            
            if city:
                cities.add(city)
                print(f"Offline: {city}")
            else:
                # Fall back to API for unknown areas
                city = self.get_city_from_api(lat, lon)
                if city:
                    cities.add(city)
                    print(f"API: {city}")
                api_calls += 1
                
                # Rate limiting for API calls
                if api_calls % 5 == 0:
                    self.save_cache()
                    time.sleep(random.uniform(1, 2))
        
        self.save_cache()
        print(f"Total API calls made: {api_calls}")
        
        return cities
    
    def process_gpx_files(self, gpx_directory: str = 'gpx') -> Set[str]:
        """Process all GPX files and return unique cities."""
        coordinates = self.extract_coordinates_from_all_gpx(gpx_directory)
        cities = self.find_cities_hybrid(coordinates)
        return cities
    
    def save_cities_to_csv(self, cities: Set[str], filename: str = 'cities_hybrid.csv'):
        """Save cities to CSV file."""
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['City'])
            for city in sorted(cities):
                writer.writerow([city])
        print(f"Saved {len(cities)} cities to {filename}")

def main():
    finder = HybridCityFinder()
    
    print("Starting hybrid city detection...")
    cities = finder.process_gpx_files('gpx')
    
    print(f"\nFound {len(cities)} unique cities:")
    for city in sorted(cities):
        print(f"  - {city}")
    
    # Save results
    finder.save_cities_to_csv(cities)
    
    # Also save as simple text file
    with open('cities_hybrid.txt', 'w') as f:
        f.write(f"Cities found: {sorted(cities)}\n")
    
    print(f"\nResults saved to cities_hybrid.csv and cities_hybrid.txt")

if __name__ == "__main__":
    main()
