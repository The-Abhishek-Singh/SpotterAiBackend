from .services import point_at_distance

def calculate_hos_timeline(leg1_dist, leg1_dur, leg2_dist, leg2_dur, cycle_used, route_coords=None, cum_miles=None):
    timeline = []
    current_day = 1
    day_time = 0.0  # Start of Day 1 (Midnight)

    # State variables
    odometer_miles = 0.0
    distance_since_fuel = 0.0
    shift_driving = 0.0
    shift_duty = 0.0
    continuous_driving_since_break = 0.0
    cycle_hours_used = float(cycle_used)

    fuel_stops_data = []
    rest_stops_data = []

    def add_event(status, duration, remark="", speed=0.0):
        nonlocal day_time, current_day, odometer_miles
        
        # Determine coordinates if route info is provided
        coord = None
        if route_coords and cum_miles:
            coord = point_at_distance(route_coords, cum_miles, odometer_miles)

        if "Fueling Stop" in remark and coord:
            fuel_stops_data.append({
                "coordinates": coord,
                "label": remark
            })
        elif ("Mandatory Rest" in remark or "Cycle Reset" in remark) and coord:
            rest_stops_data.append({
                "coordinates": coord,
                "label": remark
            })

        start = day_time
        remaining_duration = duration

        while remaining_duration > 0:
            end = start + remaining_duration
            if end > 24.0:
                part1_dur = 24.0 - start
                part_miles = part1_dur * speed
                timeline.append({
                    "day": current_day,
                    "status": status,
                    "start_time": start,
                    "end_time": 24.0,
                    "duration_hours": part1_dur,
                    "remark": remark,
                    "miles": part_miles
                })
                odometer_miles += part_miles
                current_day += 1
                start = 0.0
                remaining_duration -= part1_dur
            else:
                part_miles = remaining_duration * speed
                timeline.append({
                    "day": current_day,
                    "status": status,
                    "start_time": start,
                    "end_time": end,
                    "duration_hours": remaining_duration,
                    "remark": remark,
                    "miles": part_miles
                })
                odometer_miles += part_miles
                day_time = end
                remaining_duration = 0.0

            if day_time >= 24.0:
                current_day += 1
                day_time = 0.0

    # 1. Day 1 padding: Off duty from 00:00 to 08:00 (8 hours)
    add_event("OFF", 8.0, "Pre-Trip Rest (Off Duty)")
    shift_duty = 0.0
    shift_driving = 0.0
    continuous_driving_since_break = 0.0

    # Driving leg simulator
    def simulate_leg(leg_distance, leg_duration, leg_name):
        nonlocal odometer_miles, distance_since_fuel, shift_driving, shift_duty, continuous_driving_since_break, cycle_hours_used
        
        speed = leg_distance / leg_duration if leg_duration > 0 else 55.0
        leg_driving_remaining = leg_duration

        while leg_driving_remaining > 0:
            # A. 70-Hour Rule Check
            if cycle_hours_used >= 70.0:
                add_event("OFF", 34.0, "34-Hour Cycle Reset Restart")
                cycle_hours_used = 0.0
                shift_driving = 0.0
                shift_duty = 0.0
                continuous_driving_since_break = 0.0
                continue

            # B. 14-Hour Shift Duty Check
            if shift_duty >= 14.0:
                add_event("SB", 10.0, "10-Hour Mandatory Rest")
                shift_driving = 0.0
                shift_duty = 0.0
                continuous_driving_since_break = 0.0
                continue

            # C. 11-Hour Shift Driving Check
            if shift_driving >= 11.0:
                add_event("SB", 10.0, "10-Hour Mandatory Rest")
                shift_driving = 0.0
                shift_duty = 0.0
                continuous_driving_since_break = 0.0
                continue

            # D. 8-Hour Consecutive Drive Check (30-Min Rest)
            if continuous_driving_since_break >= 8.0:
                add_event("OFF", 0.5, "30-Min Rest Break")
                shift_duty += 0.5
                continuous_driving_since_break = 0.0
                continue

            # E. 1000-Mile Fueling Check
            if distance_since_fuel >= 1000.0:
                add_event("ON", 0.5, f"Fueling Stop - Odometer {int(odometer_miles)} mi")
                shift_duty += 0.5
                cycle_hours_used += 0.5
                distance_since_fuel = 0.0
                continue

            # Calculate driving segment limits
            hours_to_fuel = (1000.0 - distance_since_fuel) / speed if speed > 0 else 999.0

            drive_chunk = min(
                11.0 - shift_driving,
                14.0 - shift_duty,
                8.0 - continuous_driving_since_break,
                70.0 - cycle_hours_used,
                hours_to_fuel,
                leg_driving_remaining
            )

            if drive_chunk <= 0:
                if cycle_hours_used >= 70.0:
                    add_event("OFF", 34.0, "34-Hour Cycle Reset Restart")
                    cycle_hours_used = 0.0
                else:
                    add_event("SB", 10.0, "10-Hour Mandatory Rest")
                shift_driving = 0.0
                shift_duty = 0.0
                continuous_driving_since_break = 0.0
                continue

            add_event("D", drive_chunk, f"Driving - {leg_name}", speed)
            shift_driving += drive_chunk
            shift_duty += drive_chunk
            continuous_driving_since_break += drive_chunk
            cycle_hours_used += drive_chunk
            leg_driving_remaining -= drive_chunk

            chunk_miles = drive_chunk * speed
            distance_since_fuel += chunk_miles

    def add_on_duty_activity(duration, remark):
        nonlocal shift_duty, cycle_hours_used, shift_driving, continuous_driving_since_break
        
        while True:
            if cycle_hours_used + duration > 70.0:
                add_event("OFF", 34.0, "34-Hour Cycle Reset Restart")
                cycle_hours_used = 0.0
                shift_driving = 0.0
                shift_duty = 0.0
                continuous_driving_since_break = 0.0
                continue
            if shift_duty + duration > 14.0:
                add_event("SB", 10.0, "10-Hour Mandatory Rest")
                shift_driving = 0.0
                shift_duty = 0.0
                continuous_driving_since_break = 0.0
                continue
            break
            
        add_event("ON", duration, remark)
        shift_duty += duration
        cycle_hours_used += duration

    # 2. Simulate Leg 1: Current Loc -> Pickup Loc
    simulate_leg(leg1_dist, leg1_dur, "Leg 1 (Current to Pickup)")

    # 3. Pickup Loading
    add_on_duty_activity(1.0, "Loading - Pickup Location")

    # 4. Simulate Leg 2: Pickup Loc -> Dropoff Loc
    simulate_leg(leg2_dist, leg2_dur, "Leg 2 (Pickup to Dropoff)")

    # 5. Dropoff Unloading
    add_on_duty_activity(1.0, "Unloading - Dropoff Location")

    # 6. Post-Trip padding to fill the final day to midnight (24:00)
    if day_time < 24.0:
        add_event("OFF", 24.0 - day_time, "Post-Trip Rest (Off Duty)")

    return timeline, fuel_stops_data, rest_stops_data