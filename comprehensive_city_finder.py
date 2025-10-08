#!/usr/bin/env python3
"""
Comprehensive City Finder - Finds many more cities for cross-country trips
Uses better sampling and geographic segmentation
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

class ComprehensiveCityFinder:
    def __init__(self, cache_file='comprehensive_city_cache.json'):
        self.cache_file = cache_file
        self.cache = self.load_cache()
        self.geolocator = Nominatim(user_agent="comprehensive_city_finder")
        
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
    
    def segment_route_geographically(self, coordinates: List[Tuple[float, float]], 
                                   num_segments: int = 20) -> List[List[Tuple[float, float]]]:
        """
        Divide the route into geographic segments to ensure we sample from the entire journey.
        This ensures we don't miss cities in the middle of the trip.
        """
        if len(coordinates) <= num_segments:
            return [[coord] for coord in coordinates]
        
        segments = []
        segment_size = len(coordinates) // num_segments
        
        for i in range(num_segments):
            start_idx = i * segment_size
            if i == num_segments - 1:  # Last segment gets remaining coordinates
                end_idx = len(coordinates)
            else:
                end_idx = (i + 1) * segment_size
            
            segment = coordinates[start_idx:end_idx]
            if segment:  # Only add non-empty segments
                segments.append(segment)
        
        print(f"Divided route into {len(segments)} geographic segments")
        return segments
    
    def sample_from_segments(self, segments: List[List[Tuple[float, float]]], 
                           samples_per_segment: int = 5) -> List[Tuple[float, float]]:
        """
        Sample coordinates from each geographic segment to ensure coverage of entire route.
        """
        sampled_coords = []
        
        for i, segment in enumerate(segments):
            if len(segment) <= samples_per_segment:
                # If segment is small, take all coordinates
                sampled_coords.extend(segment)
            else:
                # Sample evenly from this segment
                step = len(segment) // samples_per_segment
                segment_sample = segment[::max(1, step)]
                sampled_coords.extend(segment_sample)
            
            print(f"Segment {i+1}: sampled {min(len(segment), samples_per_segment)} points from {len(segment)} total")
        
        print(f"Total sampled coordinates: {len(sampled_coords)}")
        return sampled_coords
    
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
                return city
            else:
                # Try alternative address components
                address = location.raw['address'] if location else {}
                for key in ['town', 'village', 'hamlet', 'municipality', 'suburb']:
                    if key in address:
                        city = address[key]
                        self.cache[coord_key] = city
                        return city
                
                # If no city found, try to extract from display name
                if location:
                    display_name = location.raw.get('display_name', '')
                    # Extract first part before comma
                    city = display_name.split(',')[0].strip()
                    self.cache[coord_key] = city
                    return city
                    
        except Exception as e:
            print(f"Error getting city for {lat}, {lon}: {e}")
        
        # Cache the failure to avoid retrying
        self.cache[coord_key] = None
        return None
    
    def find_cities_comprehensive(self, coordinates: List[Tuple[float, float]]) -> Set[str]:
        """Find cities using comprehensive geographic sampling."""
        print(f"Processing {len(coordinates)} coordinates...")
        
        # Divide route into geographic segments
        segments = self.segment_route_geographically(coordinates, num_segments=25)
        
        # Sample from each segment
        sampled_coords = self.sample_from_segments(segments, samples_per_segment=8)
        
        cities = set()
        api_calls = 0
        
        print(f"\nStarting city detection with {len(sampled_coords)} sampled coordinates...")
        
        for i, (lat, lon) in enumerate(sampled_coords):
            city = self.get_city_from_coordinate(lat, lon)
            if city:
                cities.add(city)
                print(f"Found: {city}")
            
            api_calls += 1
            
            # Save cache periodically
            if api_calls % 20 == 0:
                self.save_cache()
                print(f"Progress: {api_calls}/{len(sampled_coords)} API calls made, {len(cities)} cities found so far")
            
            # Rate limiting
            time.sleep(random.uniform(0.3, 0.8))
        
        # Final cache save
        self.save_cache()
        print(f"\nTotal API calls made: {api_calls}")
        
        return cities
    
    def process_gpx_files(self, gpx_directory: str = 'gpx') -> Set[str]:
        """Process all GPX files and return unique cities."""
        coordinates = self.extract_coordinates_from_all_gpx(gpx_directory)
        cities = self.find_cities_comprehensive(coordinates)
        return cities
    
    def save_cities_to_csv(self, cities: Set[str], filename: str = 'cities_comprehensive.csv'):
        """Save cities to CSV file."""
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['City'])
            for city in sorted(cities):
                writer.writerow([city])
        print(f"Saved {len(cities)} cities to {filename}")

def main():
    finder = ComprehensiveCityFinder()
    
    print("=== Comprehensive Cross-Country City Finder ===")
    print("Using geographic segmentation for better coverage")
    print()
    
    cities = finder.process_gpx_files('gpx')
    
    print(f"\n=== RESULTS ===")
    print(f"Found {len(cities)} unique cities:")
    print()
    
    for i, city in enumerate(sorted(cities), 1):
        print(f"{i:2d}. {city}")
    
    # Save results
    finder.save_cities_to_csv(cities)
    
    # Also save as simple text file
    with open('cities_comprehensive.txt', 'w') as f:
        f.write("Cities visited during cross-country bike trip:\n\n")
        for i, city in enumerate(sorted(cities), 1):
            f.write(f"{i:2d}. {city}\n")
    
    print(f"\nResults saved to:")
    print(f"  - cities_comprehensive.csv")
    print(f"  - cities_comprehensive.txt")
    print(f"  - comprehensive_city_cache.json (for future runs)")

if __name__ == "__main__":
    main()
