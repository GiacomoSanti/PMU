import time
import RPi.GPIO as gpio

gpio.setmode(gpio.BCM)
gpio.setup(18, gpio.IN, pull_up_down=gpio.PUD_DOWN)

gpio.add_event_detect(18, gpio.RISING)

def callback(arg):
    print(time.time()*1000)
    
gpio.add_event_callback(18, callback)

time.sleep(5)
