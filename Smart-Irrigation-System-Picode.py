# -*- coding: utf-8 -*-

import RPi.GPIO as GPIO
import time
import threading
from flask import Flask, jsonify
from flask_cors import CORS

# ---------------- GPIO SETUP ---------------- #
RAINDROP_PIN = 13
AIR_MOISTURE_PIN = 24
GROUND_MOISTURE_PIN = 6
RELAY_PIN = 5

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(RAINDROP_PIN, GPIO.IN)
GPIO.setup(AIR_MOISTURE_PIN, GPIO.IN)
GPIO.setup(GROUND_MOISTURE_PIN, GPIO.IN)
GPIO.setup(RELAY_PIN, GPIO.OUT)

# Pump OFF initially (Relay HIGH)
GPIO.output(RELAY_PIN, GPIO.HIGH)

# ---------------- FLASK APP ---------------- #
app = Flask(__name__)
CORS(app)  # ✅ allows access from any frontend

# ---------------- GLOBAL STATES ---------------- #
manual_override = False
motor_state = False   # False = OFF, True = ON

# ---------------- SENSOR FUNCTION ---------------- #
def read_sensors():
    return {
        "rain": GPIO.input(RAINDROP_PIN),          # 0 = rain detected
        "air_moisture": GPIO.input(AIR_MOISTURE_PIN),
        "soil_moisture": GPIO.input(GROUND_MOISTURE_PIN)
    }

# ---------------- MOTOR CONTROL ---------------- #
def set_motor(state):
    global motor_state

    if state == "ON":
        GPIO.output(RELAY_PIN, GPIO.LOW)  # Relay LOW = ON
        motor_state = True
        print("[MOTOR] ON")
    else:
        GPIO.output(RELAY_PIN, GPIO.HIGH)  # Relay HIGH = OFF
        motor_state = False
        print("[MOTOR] OFF")

# ---------------- AUTO CONTROL LOGIC ---------------- #
def auto_control():
    global manual_override

    if not manual_override:
        sensors = read_sensors()

        # Logic:
        # If rain OR soil wet → motor OFF
        if sensors["rain"] == 0 or sensors["soil_moisture"] == 0:
            set_motor("OFF")
        else:
            set_motor("ON")

# ---------------- API ROUTES ---------------- #

# 📡 Get live data
@app.route('/data', methods=['GET'])
def get_data():
    sensors = read_sensors()

    return jsonify({
        "rain": sensors["rain"],
        "air_moisture": sensors["air_moisture"],
        "soil_moisture": sensors["soil_moisture"],
        "motor": motor_state,
        "mode": "MANUAL" if manual_override else "AUTO"
    })

# 🔘 Motor ON
@app.route('/motor/on', methods=['GET'])
def motor_on():
    global manual_override
    manual_override = True
    set_motor("ON")
    return jsonify({"status": "Motor ON (Manual Mode)"})

# 🔘 Motor OFF
@app.route('/motor/off', methods=['GET'])
def motor_off():
    global manual_override
    manual_override = True
    set_motor("OFF")
    return jsonify({"status": "Motor OFF (Manual Mode)"})

# 🔄 Switch to AUTO
@app.route('/motor/auto', methods=['GET'])
def motor_auto():
    global manual_override
    manual_override = False
    return jsonify({"status": "AUTO mode enabled"})

# ---------------- BACKGROUND THREAD ---------------- #
def auto_loop():
    while True:
        auto_control()
        time.sleep(2)

# ---------------- CLEAN EXIT ---------------- #
def cleanup():
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    GPIO.cleanup()
    print("GPIO cleaned up")

# ---------------- MAIN ---------------- #
if __name__ == '__main__':
    try:
        # Start background auto control
        thread = threading.Thread(target=auto_loop)
        thread.daemon = True
        thread.start()

        print("🌱 Smart Irrigation System Running...")
        app.run(host='0.0.0.0', port=5000)

    except KeyboardInterrupt:
        print("\nShutting down...")

    finally:
        cleanup()