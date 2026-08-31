#include "secrets.h"
#include <WiFi.h>
#include <HTTPClient.h>



const int TRIG_PIN = 5;
const int ECHO_PIN = 18;
const int PIR_PIN = 19;

const int MEAL_BUTTON_PIN = 25;
const int DOOR_BUTTON_PIN = 26;
const int BATH_BUTTON_PIN = 27;

unsigned long lastBedSend = 0;
unsigned long lastPirSend = 0;
unsigned long lastButtonSend = 0;

const unsigned long SENSOR_INTERVAL = 10000;
const unsigned long BUTTON_DEBOUNCE = 700;

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 60000);

  if (duration == 0) return -1;

  return duration * 0.0343 / 2;
}

void sendSensorEvent(String sensorId, String zone, String eventType, float value) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected");
    return;
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");

  String body = "{";
  body += "\"sensorId\":\"" + sensorId + "\",";
  body += "\"zone\":\"" + zone + "\",";
  body += "\"eventType\":\"" + eventType + "\",";
  body += "\"value\":" + String(value);
  body += "}";

  int code = http.POST(body);

  Serial.print("POST ");
  Serial.print(body);
  Serial.print(" -> ");
  Serial.println(code);

  http.end();
}

void setup() {
  Serial.begin(115200);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(PIR_PIN, INPUT);

  pinMode(MEAL_BUTTON_PIN, INPUT_PULLUP);
  pinMode(DOOR_BUTTON_PIN, INPUT_PULLUP);
  pinMode(BATH_BUTTON_PIN, INPUT_PULLUP);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  unsigned long now = millis();

  if (now - lastBedSend > SENSOR_INTERVAL) {
    float distance = readDistanceCm();

    Serial.print("Distance: ");
    Serial.println(distance);

   if (distance > 0 && distance < 60) {
      sendSensorEvent("ULTRA_BED_01", "bedroom", "presence", distance);
    } else {
      sendSensorEvent("ULTRA_BED_01", "bedroom", "presence", 999);
    }

    lastBedSend = now;
  }

  if (now - lastPirSend > SENSOR_INTERVAL) {
    int motion = digitalRead(PIR_PIN);

    Serial.print("PIR: ");
    Serial.println(motion);

    if (motion == HIGH) {
      sendSensorEvent("PIR_ACTIVITY_01", "livingRoom", "motion", 1);
    }

    lastPirSend = now;
  }

  if (now - lastButtonSend > BUTTON_DEBOUNCE) {
    if (digitalRead(MEAL_BUTTON_PIN) == LOW) {
      sendSensorEvent("BUTTON_MEAL", "kitchen", "meal", 1);
      lastButtonSend = now;
    }

    if (digitalRead(DOOR_BUTTON_PIN) == LOW) {
      sendSensorEvent("BUTTON_DOOR", "frontDoor", "door", 1);
      lastButtonSend = now;
    }

    if (digitalRead(BATH_BUTTON_PIN) == LOW) {
      sendSensorEvent("BUTTON_BATH", "bathroom", "bathroom", 1);
      lastButtonSend = now;
    }
  }

  delay(100);
}