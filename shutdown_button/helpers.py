import RPi.GPIO as GPIO
import time
from common.constants import (
    PIN_SHUTDOWN_BUTTON,
    PIN_POWER_FOR_SHUTDOWN_BUTTON,
    PARAMS
)
from common.params import Params
from common.logger import loggerINFO

params = Params(db=PARAMS)

# Define GPIO pins
pin_shutdown_button = PIN_SHUTDOWN_BUTTON  
pin_power_for_shutdown_button = PIN_POWER_FOR_SHUTDOWN_BUTTON

def setup_GPIO_shutdown_button():
    # Setup GPIO
    GPIO.setmode(GPIO.BOARD) # GPIOs Nr by physical location
    GPIO.setup(pin_shutdown_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    ### GPIO.setup(pin_power_for_shutdown_button, GPIO.OUT)
    # Provide power to the switch
    ### GPIO.output(pin_power_for_shutdown_button, GPIO.HIGH)

def is_shutdown_button_pressed():
    input_state = GPIO.input(pin_shutdown_button)
    print(input_state)
    if input_state == GPIO.LOW:
        print("Button Pressed")
        time.sleep(0.2)  # Add a small delay to debounce the button
        return True
    return False

def cleanup_GPIO():
    # Cleanup GPIO
    ### GPIO.output(pin_power_for_shutdown_button, GPIO.LOW)  # Turn off power to the switch
    GPIO.cleanup()

def set_for_shutdown():
    loggerINFO(f"shutdown Terminal FLAG set to 1 - device should shutdown shortly")
    params.put("shutdownTerminal","1")
