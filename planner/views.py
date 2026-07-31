from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .services import fetch_route_data
from .hos_engine import calculate_hos_timeline

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

    distance_miles, drive_hours, route_coords, waypoints = fetch_route_data(current_loc, pickup_loc, dropoff_loc)
    timeline = calculate_hos_timeline(distance_miles, drive_hours, cycle_used)

    days_dict = {}
    for event in timeline:
        d = event['day']
        if d not in days_dict:
            days_dict[d] = []
        days_dict[d].append(event)

    daily_logs = []
    for day_num, events in days_dict.items():
        daily_logs.append({
            'day': day_num,
            'date_label': f'Day {day_num} Logsheet',
            'events': events
        })

    return Response({
        'status': 'success',
        'trip_summary': {
            'total_distance_miles': round(distance_miles, 1),
            'total_driving_hours': round(drive_hours, 1),
            'total_days': len(daily_logs)
        },
        'route_coordinates': route_coords,
        'daily_logs': daily_logs
    })