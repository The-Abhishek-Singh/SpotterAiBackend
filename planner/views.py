from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .services import fetch_route_data, build_cumulative_miles
from .hos_engine import calculate_hos_timeline

def format_time(hours_float, is_end=False):
    total_minutes = int(round(hours_float * 60))
    if total_minutes == 1440 and is_end:
        return "24:00"
    h = (total_minutes // 60) % 24
    m = total_minutes % 60
    return f"{h:02d}:{m:02d}"

@api_view(['POST'])
def plan_trip_view(request):
    data = request.data
    current_loc = data.get('current_location')
    pickup_loc = data.get('pickup_location')
    dropoff_loc = data.get('dropoff_location')
    cycle_used = float(data.get('current_cycle_used', 0))

    if not current_loc or not pickup_loc or not dropoff_loc:
        return Response(
            {'error': 'Missing required fields: current_location, pickup_location, dropoff_location'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    # 1. Fetch route legs from OSRM
    distance_miles, drive_hours, route_coords, waypoints, leg1_dist, leg1_dur, leg2_dist, leg2_dur = fetch_route_data(
        current_loc, pickup_loc, dropoff_loc
    )

    # 2. Build cumulative distance list
    cum_miles = build_cumulative_miles(route_coords)

    # 3. Compute HOS timeline
    timeline, fuel_stops, rest_stops = calculate_hos_timeline(
        leg1_dist, leg1_dur, leg2_dist, leg2_dur, cycle_used, route_coords, cum_miles
    )

    # 4. Group by day and compile log sheets
    days_dict = {}
    for event in timeline:
        d = event['day']
        if d not in days_dict:
            days_dict[d] = []
        days_dict[d].append(event)

    daily_logs = []
    for day_num in sorted(days_dict.keys()):
        events = days_dict[day_num]
        
        # Calculate daily status summaries
        total_driving = sum(e['duration_hours'] for e in events if e['status'] == 'D')
        total_on_duty = sum(e['duration_hours'] for e in events if e['status'] == 'ON')
        total_off_duty = sum(e['duration_hours'] for e in events if e['status'] == 'OFF')
        total_sleeper = sum(e['duration_hours'] for e in events if e['status'] == 'SB')
        total_miles = sum(e.get('miles', 0.0) for e in events if e['status'] == 'D')

        logs = []
        for event in events:
            logs.append({
                'status': event['status'],
                'start_time': format_time(event['start_time']),
                'end_time': format_time(event['end_time'], is_end=True),
                'duration_hours': round(event['duration_hours'], 2),
                'location_remark': event['remark']
            })

        daily_logs.append({
            'day_number': day_num,
            'date_label': f'Day {day_num} Logsheet',
            'total_driving_hours': round(total_driving, 2),
            'total_on_duty_hours': round(total_on_duty, 2),
            'total_off_duty_hours': round(total_off_duty, 2),
            'total_sleeper_berth_hours': round(total_sleeper, 2),
            'total_miles_today': round(total_miles, 1),
            'logs': logs
        })

    # Waypoints coordinates
    c_lat, c_lng = waypoints[0]
    p_lat, p_lng = waypoints[1]
    d_lat, d_lng = waypoints[2]

    # Gather query points for POIs
    poi_query_points = [(c_lat, c_lng), (p_lat, p_lng), (d_lat, d_lng)]
    for stop in fuel_stops:
        coords = stop.get('coordinates')
        if coords:
            poi_query_points.append((coords[1], coords[0])) # [lat, lng]
    for stop in rest_stops:
        coords = stop.get('coordinates')
        if coords:
            poi_query_points.append((coords[1], coords[0])) # [lat, lng]

    from .services import fetch_nearby_pois
    nearby_pois = fetch_nearby_pois(poi_query_points)

    return Response({
        'status': 'success',
        'trip_summary': {
            'total_distance_miles': round(distance_miles, 1),
            'total_driving_hours': round(drive_hours, 1),
            'total_days': len(daily_logs)
        },
        'route_coordinates': route_coords,
        'current_location_coordinates': [c_lng, c_lat],
        'pickup_coordinates': [p_lng, p_lat],
        'dropoff_coordinates': [d_lng, d_lat],
        'fuel_stops': fuel_stops,
        'rest_stops': rest_stops,
        'nearby_pois': nearby_pois,
        'daily_logs': daily_logs
    })