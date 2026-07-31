def calculate_hos_timeline(total_distance, total_drive_time, cycle_used):
    timeline = []
    current_day = 1
    day_time = 8.0

    driving_remaining = total_drive_time
    distance_remaining = total_distance
    distance_since_fuel = 0.0

    shift_driving = 0.0
    shift_duty = 0.0
    continuous_driving_since_break = 0.0

    def add_event(status, duration, remark=""):
        nonlocal day_time, current_day
        start = day_time
        end = start + duration

        if end > 24.0:
            part1 = 24.0 - start
            timeline.append({
                "day": current_day,
                "status": status,
                "start_time": round(start, 2),
                "end_time": 24.0,
                "remark": remark
            })
            current_day += 1
            day_time = 0.0
            part2 = duration - part1
            if part2 > 0:
                timeline.append({
                    "day": current_day,
                    "status": status,
                    "start_time": 0.0,
                    "end_time": round(part2, 2),
                    "remark": remark
                })
                day_time = part2
        else:
            timeline.append({
                "day": current_day,
                "status": status,
                "start_time": round(start, 2),
                "end_time": round(end, 2),
                "remark": remark
            })
            day_time = end

    # Pickup On Duty (1 Hr)
    add_event("on_duty", 1.0, "Pickup Location - Loading")
    shift_duty += 1.0

    avg_speed = total_distance / total_drive_time if total_drive_time > 0 else 55.0

    while driving_remaining > 0:
        if shift_driving >= 11.0 or shift_duty >= 14.0:
            add_event("off_duty", 10.0, "10-Hour Mandatory Rest")
            shift_driving = 0.0
            shift_duty = 0.0
            continuous_driving_since_break = 0.0
            continue

        if continuous_driving_since_break >= 8.0:
            add_event("off_duty", 0.5, "30-Min Rest Break")
            shift_duty += 0.5
            continuous_driving_since_break = 0.0
            continue

        if distance_since_fuel >= 1000.0:
            add_event("on_duty", 0.5, "Fueling Stop")
            shift_duty += 0.5
            distance_since_fuel = 0.0
            continue

        max_drive_chunk = min(
            11.0 - shift_driving,
            14.0 - shift_duty,
            8.0 - continuous_driving_since_break,
            driving_remaining
        )

        if max_drive_chunk <= 0:
            add_event("off_duty", 10.0, "10-Hour Mandatory Rest")
            shift_driving = 0.0
            shift_duty = 0.0
            continuous_driving_since_break = 0.0
            continue

        add_event("driving", max_drive_chunk, "Driving")
        shift_driving += max_drive_chunk
        shift_duty += max_drive_chunk
        continuous_driving_since_break += max_drive_chunk
        driving_remaining -= max_drive_chunk

        chunk_distance = max_drive_chunk * avg_speed
        distance_remaining -= chunk_distance
        distance_since_fuel += chunk_distance

    # Dropoff On Duty (1 Hr)
    add_event("on_duty", 1.0, "Dropoff Location - Unloading")

    if day_time < 24.0:
        add_event("off_duty", 24.0 - day_time, "Off Duty - Post Trip")

    return timeline