# Cross-Country Bike Trip City Finder

This repository contains several approaches to find all the cities you passed through during your cross-country bike trip, with minimal API usage.

## Approaches Available

### 1. Hybrid City Finder (Recommended)
**File:** `hybrid_city_finder.py` or `run_city_finder.py`

**How it works:**
- Uses an offline database of major US cities for fast detection
- Only makes API calls for areas not covered by the offline database
- Implements smart sampling to reduce the number of coordinates processed
- Caches all API results to avoid duplicate calls

**Benefits:**
- Minimal API calls (typically 10-30 calls vs hundreds)
- Fast processing
- Accurate results for major cities
- Cached results for future runs

### 2. Efficient City Finder
**File:** `efficient_city_finder.py`

**How it works:**
- Uses coordinate clustering to group nearby points
- Smart sampling to ensure geographic distribution
- Comprehensive caching system
- Rate limiting and error handling

**Benefits:**
- Reduces API calls through clustering
- Good for detailed city detection
- Handles edge cases well

### 3. Offline City Finder
**File:** `offline_city_finder.py`

**How it works:**
- Uses only a pre-built database of major US cities
- No API calls required
- Fastest processing

**Benefits:**
- Zero API calls
- Very fast
- Good for major cities

**Limitations:**
- May miss smaller towns
- Less accurate for rural areas

## Usage

### Quick Start (Recommended)
```bash
python run_city_finder.py
```

### Manual Usage
```bash
# Hybrid approach (recommended)
python hybrid_city_finder.py

# Efficient approach
python efficient_city_finder.py

# Offline approach
python offline_city_finder.py
```

## Output Files

- `cities_hybrid.csv` - CSV file with all found cities
- `cities_final.txt` - Human-readable list of cities
- `hybrid_city_cache.json` - Cache file to avoid duplicate API calls

## API Usage Comparison

| Method | Typical API Calls | Speed | Accuracy |
|--------|------------------|--------|----------|
| Original (main.py) | 200-500+ | Slow | High |
| Hybrid | 10-30 | Fast | High |
| Efficient | 50-150 | Medium | High |
| Offline | 0 | Very Fast | Medium |

## Recommendations

1. **Start with the Hybrid approach** - Best balance of speed, accuracy, and minimal API usage
2. **Use Efficient approach** if you need more detailed results for smaller towns
3. **Use Offline approach** if you want zero API calls and are okay with missing some smaller cities

## Technical Details

### Smart Sampling
- Reduces coordinates from thousands to ~100 representative points
- Ensures geographic distribution across the entire route
- Prioritizes points that are far apart

### Caching
- All API results are cached locally
- Future runs use cached data
- Significantly reduces API calls on subsequent runs

### Coordinate Clustering
- Groups nearby coordinates together
- Uses representative points for each cluster
- Reduces redundant API calls for the same area

## Troubleshooting

If you encounter API rate limiting:
1. The scripts include automatic rate limiting
2. Cached results will be used on subsequent runs
3. You can run the offline version for zero API calls

For best results, run the hybrid approach first, then use the cached results for future analysis.
