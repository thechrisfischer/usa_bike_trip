#!/usr/bin/env python3
"""
Efficient City Finder for Cross-Country Bike Trip
Minimizes API calls by using smart sampling, clustering, and caching.
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

class EfficientCityFinder:
    def __init__(self, cache_file='city_cache.json'):
        self.cache_file = cache_file
        self.cache = self.load_cache()
        self.geolocator = Nominatim(user_agent="cross_usa_city_finder")
        
    def load_cache(self) -> Dict:
        """Load cached city data to avoid duplicate API calls."""
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_cache(self):
        """Save city cache to file."""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def extract_coordinates_from_gpx(self, gpx_file_path: str) -> List[Tuple[float, float]]:
        """Extract all coordinates from a GPX file."""
        coordinates = []
        with open(gpx_file_path, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        coordinates.append((point.latitude, point.longitude))
        return coordinates
    
    def extract_coordinates_from_all_gpx(self, gpx_directory: str) -> List[Tuple[float, float]]:
        """Extract coordinates from all GPX files in a directory."""
        all_coordinates = []
        gpx_files = [f for f in os.listdir(gpx_directory) if f.endswith('.gpx')]
        
        print(f"Found {len(gpx_files)} GPX files")
        
        for gpx_file in gpx_files:
            file_path = os.path.join(gpx_directory, gpx_file)
            coordinates = self.extract_coordinates_from_gpx(file_path)
            all_coordinates.extend(coordinates)
            print(f"Extracted {len(coordinates)} points from {gpx_file}")
        
        return all_coordinates
    
    def calculate_distance(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """Calculate distance between two coordinates in kilometers."""
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        
        # Haversine formula
        R = 6371  # Earth's radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2) * math.sin(dlon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def cluster_coordinates(self, coordinates: List[Tuple[float, float]], 
                           cluster_radius_km: float = 5.0) -> List[Tuple[float, float]]:
        """
        Cluster nearby coordinates to reduce the number of API calls.
        Returns representative coordinates for each cluster.
        """
        if not coordinates:
            return []
        
        clusters = []
        used_indices = set()
        
        for i, coord in enumerate(coordinates):
            if i in used_indices:
                continue
                
            cluster = [coord]
            used_indices.add(i)
            
            # Find all coordinates within cluster_radius_km
            for j, other_coord in enumerate(coordinates[i+1:], i+1):
                if j in used_indices:
                    continue
                    
                distance = self.calculate_distance(coord, other_coord)
                if distance <= cluster_radius_km:
                    cluster.append(other_coord)
                    used_indices.add(j)
            
            # Use the first coordinate as the representative
            clusters.append(coord)
        
        print(f"Clustered {len(coordinates)} coordinates into {len(clusters)} clusters")
        return clusters
    
    def smart_sampling(self, coordinates: List[Tuple[float, float]], 
                      max_samples: int = 200) -> List[Tuple[float, float]]:
        """
        Smart sampling that ensures geographic distribution.
        Prioritizes coordinates that are far apart.
        """
        if len(coordinates) <= max_samples:
            return coordinates
        
        # First, cluster to reduce density
        clustered = self.cluster_coordinates(coordinates, cluster_radius_km=2.0)
        
        if len(clustered) <= max_samples:
            return clustered
        
        # Smart sampling: pick points that are geographically distributed
        sampled = []
        used_indices = set()
        
        # Always include first and last points
        sampled.append(clustered[0])
        sampled.append(clustered[-1])
        used_indices.add(0)
        used_indices.add(len(clustered) - 1)
        
        # Fill remaining slots with points that are far from already selected points
        while len(sampled) < max_samples and len(used_indices) < len(clustered):
            best_distance = 0
            best_index = None
            
            for i, coord in enumerate(clustered):
                if i in used_indices:
                    continue
                
                # Find minimum distance to already selected points
                min_distance = min(
                    self.calculate_distance(coord, selected) 
                    for selected in sampled
                )
                
                if min_distance > best_distance:
                    best_distance = min_distance
                    best_index = i
            
            if best_index is not None:
                sampled.append(clustered[best_index])
                used_indices.add(best_index)
            else:
                break
        
        print(f"Smart sampling: {len(coordinates)} -> {len(sampled)} coordinates")
        return sampled
    
    def get_city_from_coordinate(self, lat: float, lon: float) -> str:
        """Get city name for a coordinate, using cache when possible."""
        coord_key = f"{lat:.6f},{lon:.6f}"
        
        # Check cache first
        if coord_key in self.cache:
            return self.cache[coord_key]
        
        try:
            location = self.geolocator.reverse((lat, lon), language='en')
            if location and 'city' in location.raw['address']:
                city = location.raw['address']['city']
                self.cache[coord_key] = city
                print(f"Found city: {city}")
                return city
            else:
                # Try alternative address components
                address = location.raw['address'] if location else {}
                for key in ['town', 'village', 'hamlet', 'municipality']:
                    if key in address:
                        city = address[key]
                        self.cache[coord_key] = city
                        print(f"Found {key}: {city}")
                        return city
                
                # If no city found, try to extract from display name
                if location:
                    display_name = location.raw.get('display_name', '')
                    # Extract first part before comma
                    city = display_name.split(',')[0].strip()
                    self.cache[coord_key] = city
                    print(f"Extracted from display name: {city}")
                    return city
                    
        except Exception as e:
            print(f"Error getting city for {lat}, {lon}: {e}")
        
        # Cache the failure to avoid retrying
        self.cache[coord_key] = None
        return None
    
    def find_cities_efficiently(self, coordinates: List[Tuple[float, float]]) -> Set[str]:
        """Find cities using efficient sampling and caching."""
        print(f"Processing {len(coordinates)} coordinates...")
        
        # Smart sampling to reduce API calls
        sampled_coords = self.smart_sampling(coordinates, max_samples=150)
        
        cities = set()
        api_calls = 0
        
        for i, (lat, lon) in enumerate(sampled_coords):
            city = self.get_city_from_coordinate(lat, lon)
            if city:
                cities.add(city)
            
            api_calls += 1
            
            # Save cache periodically
            if api_calls % 10 == 0:
                self.save_cache()
                print(f"Progress: {api_calls}/{len(sampled_coords)} API calls made")
            
            # Rate limiting
            time.sleep(random.uniform(0.5, 1.5))
        
        # Final cache save
        self.save_cache()
        print(f"Total API calls made: {api_calls}")
        
        return cities
    
    def process_gpx_files(self, gpx_directory: str = 'gpx') -> Set[str]:
        """Process all GPX files and return unique cities."""
        coordinates = self.extract_coordinates_from_all_gpx(gpx_directory)
        cities = self.find_cities_efficiently(coordinates)
        return cities
    
    def save_cities_to_csv(self, cities: Set[str], filename: str = 'cities_found.csv'):
        """Save cities to CSV file."""
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['City'])  # Header
            for city in sorted(cities):
                writer.writerow([city])
        print(f"Saved {len(cities)} cities to {filename}")

def main():
    finder = EfficientCityFinder()
    
    print("Starting efficient city detection...")
    cities = finder.process_gpx_files('gpx')
    
    print(f"\nFound {len(cities)} unique cities:")
    for city in sorted(cities):
        print(f"  - {city}")
    
    # Save results
    finder.save_cities_to_csv(cities)
    
    # Also save as simple text file
    with open('cities_found.txt', 'w') as f:
        f.write(f"Cities found: {sorted(cities)}\n")
    
    print(f"\nResults saved to cities_found.csv and cities_found.txt")

if __name__ == "__main__":
    main()
