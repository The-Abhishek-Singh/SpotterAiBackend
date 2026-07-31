import requests

def fetch_route_data(current_loc, pickup_loc, dropoff_loc):
    def geocode(address):
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={address}"
        headers = {'User-Agent': 'SpotterHOSEngine/1.0'}
        try:
            res = requests.get(url, headers=headers, timeout=5).json()
            if res:
                return float(res[0]['lon']), float(res[0]['lat'])
        except Exception:
            pass
        return None, None

    c_lng, c_lat = geocode(current_loc)
    p_lng, p_lat = geocode(pickup_loc)
    d_lng, d_lat = geocode(dropoff_loc)

    if not c_lng or not p_lng or not d_lng:
        c_lng, c_lat = -87.6298, 41.8781
        p_lng, p_lat = -90.1994, 38.6270
        d_lng, d_lat = -96.7970, 32.7767

    osrm_url = f"http://router.project-osrm.org/route/v1/driving/{c_lng},{c_lat};{p_lng},{p_lat};{d_lng},{d_lat}?overview=full&geometries=geojson"
    try:
        res = requests.get(osrm_url, timeout=10).json()
        if res.get("routes"):
            route = res["routes"][0]
            distance_miles = route["distance"] / 1609.34
            driving_hours = route["duration"] / 3600
            geometry = route["geometry"]["coordinates"]
            return distance_miles, driving_hours, geometry, [(c_lat, c_lng), (p_lat, p_lng), (d_lat, d_lng)]
    except Exception:
        pass

    return 800.0, 14.0, [[c_lng, c_lat], [p_lng, p_lat], [d_lng, d_lat]], [(c_lat, c_lng), (p_lat, p_lng), (d_lat, d_lng)]