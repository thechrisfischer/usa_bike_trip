import gpxpy
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
import random
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor

# Add these at the top with other imports
MAX_WORKERS = 5  # Configure number of simultaneous threads

def extract_coordinates(gpx_file_path):
    with open(gpx_file_path, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)
        coordinates = []
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    coordinates.append((point.latitude, point.longitude))
    return coordinates


def process_coordinate(lat, lon, geolocator, cities_set, lock):
    try:
        location = geolocator.reverse((lat, lon), language='en')
        if location and 'city' in location.raw['address']:
            city = location.raw['address']['city']
            with lock:
                cities_set.add(city)
                print(city)
        time.sleep(random.randint(1, 3))  # Reduced sleep time since we're parallel
    except Exception as e:
        print(f"Error processing {lat}, {lon}: {e}")



def get_city_names(coordinates):
    geolocator = Nominatim(user_agent="gpx_city_extractor")
    cities = set()
    lock = threading.Lock()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(
                process_coordinate, 
                lat, 
                lon, 
                geolocator, 
                cities, 
                lock
            ) for lat, lon in coordinates
        ]
        # Wait for all threads to complete
        for future in futures:
            future.result()
    
    return sorted(cities)



gpx_file_path = 'usa_ride.gpx'
coordinates = extract_coordinates(gpx_file_path)
print(coordinates)

# Sample the coordinates to reduce the number of requests
sampled_coordinates = coordinates[::100]
print(len(sampled_coordinates))

cities = get_city_names(sampled_coordinates)
print("Cities along the route:", cities)