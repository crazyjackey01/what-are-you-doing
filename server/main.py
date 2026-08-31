from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, date, timedelta
import json
import os
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "exaone3.5:7.8b")

DATA_FILE = os.environ.get("DATA_FILE", os.path.join(os.path.dirname(__file__), "sensor_events.json"))


class SensorEvent(BaseModel):
    sensor_type: str
    value: bool
    timestamp: str | None = None


def load_events():
    if not os.path.exists(DATA_FILE):
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_events(events):
    # 최근 7일 데이터만 유지
    today = date.today()

    filtered_events = []
    for e in events:
        event_date = datetime.fromisoformat(e["timestamp"]).date()
        days_diff = (today - event_date).days

        if 0 <= days_diff <= 6:
            filtered_events.append(e)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(filtered_events, f, ensure_ascii=False, indent=2)


def add_sensor_event(sensor_type: str, value: bool, timestamp: str | None = None):
    events = load_events()

    event_time = timestamp or datetime.now().isoformat(timespec="seconds")

    new_event = {
        "sensor_type": sensor_type,
        "value": value,
        "timestamp": event_time
    }

    events.append(new_event)
    save_events(events)

    return new_event


@app.post("/sensor-event")
def sensor_event(event: SensorEvent):
    saved_event = add_sensor_event(
        sensor_type=event.sensor_type,
        value=event.value,
        timestamp=event.timestamp
    )

    return {
        "status": "saved",
        "event": saved_event
    }


def time_to_minutes(time_str):
    h, m = map(int, time_str.split(":"))
    return h * 60 + m


def analyze_today(events):
    today = date.today().isoformat()

    today_events = [
        e for e in events
        if e["timestamp"].startswith(today)
    ]

    wake_time = None
    first_out_time = None
    kitchen_count = 0
    living_count = 0
    bed_count = 0

    bed_true_count = 0
    bed_false_count = 0

    for e in today_events:
        sensor = e["sensor_type"]
        value = e["value"]
        timestamp = datetime.fromisoformat(e["timestamp"])
        time_text = timestamp.strftime("%H:%M")

        # 침대 센서
        if sensor == "bed_pressure":
            bed_count += 1

            if value is True:
                bed_true_count += 1

            if value is False:
                bed_false_count += 1

                # 기존 방식: 침대 감지가 false가 된 첫 시간 = 일어난 시간 추정
                if wake_time is None:
                    wake_time = time_text

        # 현관문
        if sensor == "front_door" and value is True:
            if first_out_time is None:
                first_out_time = time_text

        # 주방
        if sensor == "kitchen_light" and value is True:
            kitchen_count += 1

        # 거실
        if sensor == "living_light" and value is True:
            living_count += 1

    return {
        "wake_time": wake_time,
        "first_out_time": first_out_time,
        "kitchen_count": kitchen_count,
        "living_count": living_count,
        "bed_count": bed_count,
        "bed_true_count": bed_true_count,
        "bed_false_count": bed_false_count,
        "total_events": len(today_events),
    }


def get_day_data(events, target_date):
    day_events = [
        e for e in events
        if e["timestamp"].startswith(target_date)
    ]

    wake_time = None
    first_out_time = None
    kitchen_count = 0
    living_count = 0
    bed_count = 0

    for e in day_events:
        sensor = e["sensor_type"]
        value = e["value"]
        timestamp = datetime.fromisoformat(e["timestamp"])
        time_text = timestamp.strftime("%H:%M")

        if sensor == "bed_pressure" and value is False and wake_time is None:
            wake_time = time_text

        if sensor == "front_door" and value is True and first_out_time is None:
            first_out_time = time_text

        if sensor == "kitchen_light" and value is True:
            kitchen_count += 1

        if sensor == "living_light" and value is True:
            living_count += 1

        if sensor == "bed_pressure" and value is True:
            bed_count += 1

    return {
        "wake_time": wake_time,
        "first_out_time": first_out_time,
        "kitchen_count": kitchen_count,
        "living_count": living_count,
        "bed_count": bed_count,
    }


def average_minutes(time_list):
    valid_times = [t for t in time_list if t is not None]

    if not valid_times:
        return None

    total = sum(time_to_minutes(t) for t in valid_times)
    avg = total // len(valid_times)

    return f"{avg // 60:02d}:{avg % 60:02d}"


def calculate_average_from_events(events):
    today_str = date.today().isoformat()

    daily_data_list = []

    for i in range(1, 7):
        target_date = (date.today().replace() - timedelta(days=i)).isoformat()
        day_data = get_day_data(events, target_date)

        has_data = (
            day_data["wake_time"]
            or day_data["first_out_time"]
            or day_data["kitchen_count"] > 0
            or day_data["living_count"] > 0
            or day_data["bed_count"] > 0
        )

        if has_data:
            daily_data_list.append(day_data)

    # 과거 데이터가 없으면 오늘 데이터로 임시 평균 생성
    if not daily_data_list:
        today_data = get_day_data(events, today_str)
        daily_data_list.append(today_data)

    wake_times = [d["wake_time"] for d in daily_data_list]
    out_times = [d["first_out_time"] for d in daily_data_list]

    avg_kitchen = sum(d["kitchen_count"] for d in daily_data_list) / len(daily_data_list)
    avg_living = sum(d["living_count"] for d in daily_data_list) / len(daily_data_list)
    avg_bed = sum(d["bed_count"] for d in daily_data_list) / len(daily_data_list)

    return {
        "wake_time": average_minutes(wake_times),
        "first_out_time": average_minutes(out_times),
        "kitchen_count": avg_kitchen,
        "living_count": avg_living,
        "bed_count": avg_bed,
        "days_used": len(daily_data_list),
    }


def compare_with_average(today_data, average):
    notes = []

    if average["days_used"] <= 1:
        notes.append("아직 평균 데이터가 충분하지 않아 현재 측정된 데이터를 기준으로 하루를 정리합니다.")

    if today_data["wake_time"] and average["wake_time"]:
        diff = time_to_minutes(today_data["wake_time"]) - time_to_minutes(average["wake_time"])

        if diff >= 60:
            notes.append(f"오늘은 평균보다 약 {diff}분 늦게 일어난 것으로 보입니다.")
        elif diff <= -60:
            notes.append(f"오늘은 평균보다 약 {abs(diff)}분 일찍 일어난 것으로 보입니다.")
        else:
            notes.append("기상 시간은 평소와 크게 다르지 않습니다.")
    elif today_data["wake_time"]:
        notes.append(f"오늘은 {today_data['wake_time']}쯤 기상한 것으로 보입니다.")
    else:
        notes.append("오늘은 기상 시간이 아직 뚜렷하게 감지되지 않았습니다.")

    if today_data["first_out_time"] and average["first_out_time"]:
        diff = time_to_minutes(today_data["first_out_time"]) - time_to_minutes(average["first_out_time"])

        if diff >= 120:
            notes.append("오늘은 평소보다 외출 시간이 늦어진 것 같습니다.")
        else:
            notes.append("오늘은 외출 또는 출입 흔적이 감지되었습니다.")
    elif today_data["first_out_time"]:
        notes.append(f"오늘은 {today_data['first_out_time']}쯤 외출 또는 출입 흔적이 있었습니다.")
    else:
        notes.append("오늘은 아직 외출 흔적이 거의 없습니다.")

    if average["kitchen_count"] > 0:
        if today_data["kitchen_count"] < average["kitchen_count"] / 2:
            notes.append("주방 사용이 평소보다 적은 편입니다.")
        else:
            notes.append("주방 사용은 평소와 비슷한 편입니다.")
    else:
        notes.append(f"오늘 주방 사용은 {today_data['kitchen_count']}회 감지되었습니다.")

    if average["living_count"] > 0:
        if today_data["living_count"] < average["living_count"] / 2:
            notes.append("거실 활동이 평소보다 적은 편입니다.")
        else:
            notes.append("거실에서 평소와 비슷하게 시간을 보내신 것 같습니다.")
    else:
        notes.append(f"오늘 거실 활동은 {today_data['living_count']}회 감지되었습니다.")

    if today_data["bed_count"] > 0:
        notes.append(
            f"침대 센서는 오늘 {today_data['bed_count']}회 감지되었고, "
            f"휴식 또는 침대 주변 활동 흔적이 있습니다."
    )
    else:
        notes.append("오늘은 침대 사용 흔적이 아직 감지되지 않았습니다.")

    return "\n".join(notes)


def call_ollama(analysis_text):
    prompt = f"""
    
너는 자녀에게 부모님의 하루를 부드럽게 전달하는 앱 메시지 작성자야.

목표:
자녀가 부모님께 자연스럽게 연락하도록 돕는 짧은 안부 메시지를 만든다.

규칙:
- 자녀에게 보내는 알림 문장으로 작성해.
- 부모님에게 직접 말하지 마.
- 챗봇처럼 "궁금한 점이 있으면 말씀해 주세요"라고 쓰지 마.
- "언제든지 말씀해 주세요", "도와드릴게요" 같은 표현 금지.
- 감시 느낌이 들지 않게 써.
- 불안을 과하게 만들지 마.
- 센서 데이터는 확정하지 말고 "~인 것 같아요"로 표현해.
- 마지막 문장은 반드시 "가볍게 “뭐해요?” 하고 안부를 물어보면 좋을 것 같아요." 로 끝내.
- 전체는 2문장으로 작성해.
- 따옴표는 붙이지 마.

오늘 분석:
{analysis_text}

출력 예시:
오늘은 외출 흔적이 있고, 거실에서도 시간을 보내신 것 같아요. 가볍게 “뭐해요?” 하고 안부를 물어보면 좋을 것 같아요.
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            },
            timeout=60
        )

        response.raise_for_status()

        result = response.json()
        message = result["message"]["content"].strip()
        message = message.strip('"').strip("'")

        return message

    except Exception as e:
        return f"오늘 부모님의 하루 기록을 정리해보니 평소와 비교해 확인해볼 만한 변화가 있어요. 가볍게 “뭐해요?” 하고 안부를 물어보면 좋을 것 같아요. 오류: {e}"


@app.get("/today-message")
def today_message():
    events = load_events()
    today_data = analyze_today(events)
    average = calculate_average_from_events(events)
    analysis_text = compare_with_average(today_data, average)
    message = call_ollama(analysis_text)

    return {
        "today_data": today_data,
        "average": average,
        "analysis": analysis_text,
        "message": message
    }


@app.get("/events")
def get_events():
    return {
        "events": load_events()
    }


@app.delete("/events")
def clear_events():
    save_events([])
    return {
        "status": "cleared"
    }


@app.get("/")
def root():
    return {"status": "running"}

@app.post("/sensor-event/bulk")
def bulk_sensor_events(events: list[SensorEvent]):

    saved_events = []

    for event in events:
        saved = add_sensor_event(
            sensor_type=event.sensor_type,
            value=event.value,
            timestamp=event.timestamp
        )

        saved_events.append(saved)

    return {
        "status": "saved",
        "count": len(saved_events),
        "events": saved_events
    }

class HardwareSensorEvent(BaseModel):
    sensorId: str
    zone: str
    eventType: str
    value: float
    timestamp: str | None = None


@app.post("/sensor")
def hardware_sensor_event(event: HardwareSensorEvent):
    sensor_type = None
    sensor_value = True

    if event.sensorId == "ULTRA_BED_01":
        sensor_type = "bed_pressure"
        sensor_value = event.value > 0 and event.value < 60

    elif event.sensorId == "PIR_ACTIVITY_01":
        sensor_type = "living_light"
        sensor_value = True

    elif event.sensorId == "BUTTON_MEAL":
        sensor_type = "kitchen_light"
        sensor_value = True

    elif event.sensorId == "BUTTON_DOOR":
        sensor_type = "front_door"
        sensor_value = True

    elif event.sensorId == "BUTTON_BATH":
        return {
            "status": "ignored",
            "reason": "bathroom sensor is not used in this MVP",
            "raw": event.dict()
        }

    else:
        return {
            "status": "ignored",
            "reason": "unknown sensorId",
            "raw": event.dict()
        }

    saved_event = add_sensor_event(
        sensor_type=sensor_type,
        value=sensor_value,
        timestamp=event.timestamp
    )

    return {
        "status": "saved",
        "mapped_sensor": sensor_type,
        "event": saved_event
    }