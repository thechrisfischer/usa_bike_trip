#!/usr/bin/env python3
"""
Simple script to run the hybrid city finder
"""

from hybrid_city_finder import HybridCityFinder

def main():
    print("=== Cross-Country Bike Trip City Finder ===")
    print("Using hybrid approach: offline detection + minimal API calls")
    print()
    
    finder = HybridCityFinder()
    cities = finder.process_gpx_files('gpx')
    
    print(f"\n=== RESULTS ===")
    print(f"Found {len(cities)} unique cities:")
    print()
    
    for i, city in enumerate(sorted(cities), 1):
        print(f"{i:2d}. {city}")
    
    # Save results
    finder.save_cities_to_csv(cities)
    
    # Also save as simple text file
    with open('cities_final.txt', 'w') as f:
        f.write("Cities visited during cross-country bike trip:\n\n")
        for i, city in enumerate(sorted(cities), 1):
            f.write(f"{i:2d}. {city}\n")
    
    print(f"\nResults saved to:")
    print(f"  - cities_hybrid.csv")
    print(f"  - cities_final.txt")
    print(f"  - hybrid_city_cache.json (for future runs)")

if __name__ == "__main__":
    main()
