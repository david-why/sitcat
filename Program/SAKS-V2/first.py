#!/usr/bin/python

import time
import RPi.GPIO as GPIO
from sakshat import SAKSHAT
from sakspins import SAKSPins as PINS

SAKS = SAKSHAT()
GPIO_TRIGGER = PINS.UART_TXD
GPIO_ECHO = PINS.UART_RXD
GPIO.setup(GPIO_TRIGGER, GPIO.OUT, initial = GPIO.LOW) # Ultrasonic Trigger
GPIO.setup(GPIO_ECHO, GPIO.IN)                         # Ultrasonic Echo

def get_distance():
  '''
  Get distance from HC-SR04 Ultrasonic Sensor
  :return: int, distance in cm
  '''
  GPIO.output(GPIO_TRIGGER, GPIO.HIGH)
  time.sleep(0.00001)
  GPIO.output(GPIO_TRIGGER, GPIO.LOW)
  stop = start = time.time()
  while GPIO.input(GPIO_ECHO) == GPIO.LOW and stop - start < 0.01:
    stop = time.time()
  stop = start = time.time()
  while GPIO.input(GPIO_ECHO) == GPIO.HIGH and stop - start < 0.01:
    stop = time.time()
  return int((stop - start) * 34300 / 2) # sound speed is 34300 cm/s

while True:
  d = get_distance()
  if d < 50:
    SAKS.buzzer.beep(0.01)
  print d, 'cm'
  time.sleep(0.5)

