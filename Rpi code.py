import time
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import board
import busio
from adafruit_ssd1306 import SSD1306_I2C
from PIL import Image, ImageDraw, ImageFont
import requests
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import logging
import atexit
from threading import Thread

# Flask setup
app = Flask(_name_)
CORS(app)  # Enable CORS for all routes
logging.basicConfig(level=logging.DEBUG)

# GPIO setup
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)  # or GPIO.BOARD depending on your setup

# RFID setup
reader = SimpleMFRC522()

# Servo motor setup
SERVO_PINS = {1: 22, 2: 23}
pwms = {}
for servo_id, pin in SERVO_PINS.items():
    GPIO.setup(pin, GPIO.OUT)
    pwms[servo_id] = GPIO.PWM(pin, 50)  # 50Hz for servos
    pwms[servo_id].start(0)

# Buzzer setup
BUZZER_PIN = 19
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# OLED display setup
i2c = busio.I2C(board.SCL, board.SDA)
oled = SSD1306_I2C(128, 64, i2c)
oled.fill(0)
oled.show()

# Font for OLED display
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 14)

# Function to display messages on the OLED
def display(message):
    image = Image.new("1", (oled.width, oled.height))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, oled.width, oled.height), outline=225, fill=0)
    draw.text((10, 30), message, font=font, fill=225)
    oled.image(image)
    oled.show()

# Function to move a servo
def move_servo(servo_id, angle):
    if servo_id in pwms:
        pwm = pwms[servo_id]
        duty_cycle = angle / 18 + 2
        pwm.ChangeDutyCycle(duty_cycle)
        time.sleep(1)
        pwm.ChangeDutyCycle(0)
    else:
        logging.error(f"Invalid servo ID: {servo_id}")

# Function to buzz the buzzer
def buzz():
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    time.sleep(1)
    GPIO.output(BUZZER_PIN, GPIO.LOW)

# Flask route to handle RFID scan
@app.route('/rfid-scan', methods=['POST'])
def rfid_scan():
    logging.debug("Received RFID scan request")
    id, text = reader.read()  # Simulate RFID scan
    display(f"RFID ID:\n{id}")
    buzz()  # Activate buzzer
    return jsonify({"rfid": id})

# Flask route to handle servo movement
@app.route('/run_servo', methods=['POST'])
def run_servo_route():
    logging.debug("Received move_servo request")
    data = request.get_json()
    servo_id = data.get("servo_id")

    if servo_id not in [1, 2]:
        logging.error(f"Invalid servo ID: {servo_id}")
        return jsonify({"status": "error", "message": "Invalid servo ID"}), 400

    logging.info(f"Moving servo {servo_id}")
    move_servo(servo_id, 90)  # Example angle
    return jsonify({"message": f"Servo {servo_id} moved successfully"})

# Flask route to buzz the buzzer
@app.route('/buzz', methods=['POST'])
def buzz_route():
    logging.debug("Received buzz request")
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    time.sleep(1)
    GPIO.output(BUZZER_PIN, GPIO.LOW)

    return jsonify({"message": "Buzzer beeped!"})

# Main loop for RFID scanning and servo interaction
def main_loop():
    display("Welcome to Medelite")
    
    while True:
        logging.info("Hold card to RFID reader...")
        id, text = reader.read()
        display(f"RFID ID:\n{id}")
        
        requests.post("http://172.16.42.207:5001/rfid-scan", data={"rfid_id": id})
        requests.post("http://172.16.42.207:5001/run_servo")
        # Simulate servo interaction
        display("Enter number from 1 to 2 for servo")
        servo_input = input("Enter servo number (1 or 2): ")
        if servo_input.isdigit():
            servo_id = int(servo_input)
            if 1 <= servo_id <= 2:
                move_servo(servo_id, 90)
                buzz()
                display("Thank you!")
            else:
                logging.error("Invalid servo ID!")
        else:
            logging.error("Invalid input!")

        display("Welcome to Medelite")
        time.sleep(2)

# Clean up GPIO on exit
atexit.register(GPIO.cleanup)

if _name_ == '_main_':
    # Run Flask server in one thread
    flask_thread = Thread(target=lambda: app.run(host='172.16.42.207', port=5001,threaded=True, debug=True, use_reloader=False))
    flask_thread.start()

    # Run RFID and servo interaction in the main loop
    main_loop()