#!/usr/bin/python

import time
import RPi.GPIO as GPIO

BUZZER       = 11
GPIO_ECHO    = 14
GPIO_TRIGGER = 15
SOUND_SPEED  = 34029
  
def get_distance():
  '''
  Get distance from HC-SR04 Ultrasonic Sensor
  :return: int, distance in cm
  '''
  GPIO.output(GPIO_TRIGGER, GPIO.HIGH)
  time.sleep(0.00001)
  GPIO.output(GPIO_TRIGGER, GPIO.LOW)
  stop = start = time.time()
  while GPIO.input(GPIO_ECHO) == GPIO.LOW and stop - start < 0.1:
    stop = time.time()
  stop = start = time.time()
  while GPIO.input(GPIO_ECHO) == GPIO.HIGH and stop - start < 0.1:
    stop = time.time()
  return int((stop - start) * SOUND_SPEED / 2)

def buzz():
  '''
  Buzz for 0.1 seconds
  '''
  GPIO.output(BUZZER, GPIO.LOW)
  time.sleep(0.1)
  GPIO.output(BUZZER, GPIO.HIGH)

GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_TRIGGER, GPIO.OUT, initial = GPIO.LOW)       # Ultrasonic Trigger
GPIO.setup(GPIO_ECHO, GPIO.IN, pull_up_down = GPIO.PUD_DOWN) # Ultrasonic Echo
GPIO.setup(BUZZER, GPIO.OUT, initial = GPIO.HIGH)            # Buzzer 

while True:
  d = get_distance()
  if d < 50:
    buzz()
  print d, 'cm'
  time.sleep(0.5)

