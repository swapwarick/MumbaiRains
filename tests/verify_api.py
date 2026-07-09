import urllib.request
import json
import sys

def verify_endpoint(url):
    print(f"Testing URL: {url}...")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            content = response.read().decode('utf-8')
            data = json.loads(content)
            print(f"  Result: Success (Status {status})")
            return data
    except Exception as e:
        print(f"  Result: Failed! Error: {e}")
        return None

def main():
    base_url = "http://127.0.0.1:8000"
    
    # 1. Test Root
    root_data = verify_endpoint(f"{base_url}/")
    if not root_data:
        print("Backend server is not running or accessible. Please ensure uvicorn is running.")
        sys.exit(1)
        
    # 2. Test Terrain
    terrain_data = verify_endpoint(f"{base_url}/api/terrain")
    if terrain_data:
        print(f"  Terrain shape: {terrain_data.get('width')}x{terrain_data.get('height')}")
        print(f"  Terrain contains keys: {list(terrain_data.keys())}")
        
    # 3. Test Roads
    roads_data = verify_endpoint(f"{base_url}/api/roads")
    if roads_data:
        print(f"  Roads type: {roads_data.get('type')}")
        print(f"  Roads count: {len(roads_data.get('features', []))}")
        
    # 4. Test Waterways
    waterways_data = verify_endpoint(f"{base_url}/api/waterways")
    if waterways_data:
        print(f"  Waterways type: {waterways_data.get('type')}")
        print(f"  Waterways count: {len(waterways_data.get('features', []))}")
        
    # 5. Test Buildings
    buildings_data = verify_endpoint(f"{base_url}/api/buildings")
    if buildings_data:
        print(f"  Buildings type: {buildings_data.get('type')}")
        print(f"  Buildings count: {len(buildings_data.get('features', []))}")

if __name__ == "__main__":
    main()
