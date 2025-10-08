
import csv

cities = ['Albuquerque', 'Allegheny Township', 'Allentown', 'Bedford Township', 'Bethel Township', 'Bethlehem', 'Bethlehem Township', 'Brush Creek Township', 'Buffalo Township', 'Bullhead City', 'Bullskin Township', 'Canton Township', 'Carroll Township', 'Columbus', 'Dayton', 'Donegal Township', 'Dublin Township', 'East Hanover Township', 'East Huntingdon Township', 'East Providence Township', 'Easton', 'Elizabeth Township', 'Fallowfield Township', 'Fannett Township', 'Fayetteville', 'Flagstaff', 'Fontana', 'Gallup', 'Greenwich Township', 'Hampden Township', 'Harrisburg', 'Hopewell Township', 'Jefferson Township', 'Juniata Township', 'Kingman', 'Letterkenny Township', 'Los Angeles', 'Lower Paxton Township', 'Lurgan Township', 'Mansfield Township', 'Middlesex Township', 'Miner', 'Monroe Township', 'Mount Pleasant Township', 'Napier Township', 'New York', 'North Franklin Township', 'North Middleton Township', 'North Newton Township', 'North Strabane Township', 'Nottingham Township', 'Palmer Township', 'Pomona', 'Rancho Cucamonga', 'Rostraver Township', 'Santa Fe', 'Santa Monica', 'Shade Township', 'Silver Spring Township', 'Snake Spring Township', 'Somerset Township', 'South Huntingdon Township', 'South Middleton Township', 'South Strabane Township', 'South Whitehall Township', 'St. Francisville', 'Stillwater', 'Stonycreek Township', 'Susquehanna Township', 'Swatara Township', 'Tahlequah', 'Taos', 'Taylor Township', 'Tilden Township', 'Tulpehocken Township', 'Tulsa', 'Union Township', 'Upper Bern Township', 'Upper Macungie Township', 'Upper Tulpehocken Township', 'Victorville', 'Washington Township', 'Weisenberg Township', 'Wells Township', 'West Hanover Township', 'West Pennsboro Township', 'West Providence Township', 'Wheeling', 'Windsor Township', 'Xenia', 'Zanesville']
def write_cities_to_csv(cities, filename='cities.csv'):
    """
    Write the cities list to a CSV file.
    
    Args:
        cities (list): List of city names
        filename (str): Name of the output CSV file (default: 'cities.csv')
    """
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['City'])  # Write header
        for city in cities:
            writer.writerow([city])  # Write each city as a row

write_cities_to_csv(cities)