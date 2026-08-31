"""Insert synthetic example events only; never represents a participant study."""
from datetime import date
from main import add_sensor_event

demo_events = [
    {
        "sensor_type": "bed_pressure",
        "value": False,
        "timestamp": f"{date.today().isoformat()}T08:40:00"
    },
    {
        "sensor_type": "kitchen_light",
        "value": True,
        "timestamp": f"{date.today().isoformat()}T09:05:00"
    },
    {
        "sensor_type": "front_door",
        "value": True,
        "timestamp": f"{date.today().isoformat()}T10:30:00"
    },
    {
        "sensor_type": "living_light",
        "value": True,
        "timestamp": f"{date.today().isoformat()}T19:20:00"
    },
    {
        "sensor_type": "bed_pressure",
        "value": True,
        "timestamp": f"{date.today().isoformat()}T23:10:00"
    }
]

for event in demo_events:
    saved = add_sensor_event(
        sensor_type=event["sensor_type"],
        value=event["value"],
        timestamp=event["timestamp"]
    )
    print("saved:", saved)

print("Demo data inserted.")