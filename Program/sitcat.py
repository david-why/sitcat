#!/usr/bin/python
'''
sitcat.py, by Wangs, May~June 2017
  Written by David Wang, except ...
  Ultrasonic, DigitalDisplay, Temperature functions are written by Bob Wang
'''

import os, glob, time, pickle, signal, re, traceback
from threading import Thread
import RPi.GPIO as GPIO

class PINS(object):
    '''
    SAKS v1 Pins Code With BCM for Raspberry Pi.
    '''
    LED_YELLOW = 7
    LED_RED = 8
    BUZZER = 11
    TACT_RIGHT = 23
    TACT_LEFT = 18
    DIGITAL_DISPLAY_A = 21
    DIGITAL_DISPLAY_B = 16
    DIGITAL_DISPLAY_C = 19
    DIGITAL_DISPLAY_D = 6
    DIGITAL_DISPLAY_E = 5
    DIGITAL_DISPLAY_F = 20
    DIGITAL_DISPLAY_G = 26
    DIGITAL_DISPLAY_DP = 13
    DIGITAL_DISPLAY_SELECET_1 = 17
    DIGITAL_DISPLAY_SELECET_2 = 27
    DIGITAL_DISPLAY_SELECET_3 = 22
    DIGITAL_DISPLAY_SELECET_4 = 10
    DS18B20 = 4
    GPIO_ECHO = 14
    GPIO_TRIGGER = 15

    DIGITAL_DISPLAY = (
        DIGITAL_DISPLAY_A,
        DIGITAL_DISPLAY_B,
        DIGITAL_DISPLAY_C,
        DIGITAL_DISPLAY_D,
        DIGITAL_DISPLAY_E,
        DIGITAL_DISPLAY_F,
        DIGITAL_DISPLAY_G,
        DIGITAL_DISPLAY_DP
    )

    DIGITAL_DISPLAY_SELECT = (
        DIGITAL_DISPLAY_SELECET_1,
        DIGITAL_DISPLAY_SELECET_2,
        DIGITAL_DISPLAY_SELECET_3,
        DIGITAL_DISPLAY_SELECET_4,
    )

class DigitalDisplay(object):
    __pins = {'seg': PINS.DIGITAL_DISPLAY, 'sel': PINS.DIGITAL_DISPLAY_SELECT}
    __number_code = {'0':0x3f, '1':0x06, '2':0x5b, '3':0x4f, '4':0x66, '5':0x6d, '6':0x7d, 
                     '7':0x07, '8':0x7f, '9':0x6f, '-':0x40, '_':0x08, '=':0x48, ' ':0x00,
                     'A':0x77, 'B':0x7c, 'C':0x39, 'D':0x5e, 'E':0x79, 'F':0x71}
    __pin_stat = {}
    __numbers = ''

    def __init__(self):
        for p in self.__pins['seg'] + self.__pins['sel']:
            GPIO.setup(p, GPIO.OUT)
            self.__pin_stat[p] = True
            self.set_pin(p, False)
        self.__pattern = re.compile(r'[-_=A-F0-9 #]\.?')
        try:
            t1 = Thread(target = self.flush_4bit)
            t1.setDaemon(True)
            t1.start()
        except:
            print "Error: Unable to start thread by DigitalDisplay"

    def show(self, str):
        self.__numbers = str

    def set_pin(self, pin, v):
        if v != self.__pin_stat[pin]:
            self.__pin_stat[pin] = v
            GPIO.output(pin, GPIO.LOW if v else GPIO.HIGH)

    def flush_bit(self, sel, num, dp):
        sel_pin = self.__pins['sel'][sel]
        if not num in self.__number_code:
            self.set_pin(sel_pin, False)
            return
        n = self.__number_code[num] | (0x80 if dp else 0x00)
        j = True
        for i in range(8):
            pin = self.__pins['seg'][i]
            v = ((n & (1 << i)) != 0)
            if v != self.__pin_stat[pin]:
                if j:
                    for k in self.__pins['sel']:
                        self.set_pin(k, False)
                    j = False
                self.set_pin(pin, v)
        self.set_pin(sel_pin, True)

    def flush_4bit(self):
        numbers = ''
        digits = []
        try:
            while True:
                if numbers != self.__numbers:
                    numbers = self.__numbers
                    matches = self.__pattern.findall(numbers)
                    digits = []
                    for i in range(len(matches)):
                        digits.append((matches[i].replace('.',''), matches[i].count('.') > 0))
                if digits:
                    for i in range(min(4, len(digits))):
                        self.flush_bit(i, *digits[i])
                        time.sleep(0.005)
                else:
                    for pin in self.__pins['sel']:
                        self.set_pin(pin, False)
                    time.sleep(0.02)
        except:
            pass

def get_temperature():
  '''
  Receive data from DB18B20 1-Wire temperature sensor
  :return: float, Celsius temperature
  '''
  try:
    return int(file(glob.glob('/sys/bus/w1/devices/28-*/w1_slave')[0]).read()[-6 : -1]) / 1000.0 - 5
  except:
    return 27.0

def get_distance():
  '''
  Get distance from HC-SR04
  :return: int, distance in cm
  '''
  GPIO.output(PINS.GPIO_TRIGGER, GPIO.HIGH)
  time.sleep(0.00001)
  GPIO.output(PINS.GPIO_TRIGGER, GPIO.LOW)
  stop = start = time.time()
  while GPIO.input(PINS.GPIO_ECHO) == GPIO.LOW and stop - start < 0.01:
    stop = time.time()
  stop = start = time.time()
  while GPIO.input(PINS.GPIO_ECHO) == GPIO.HIGH and stop - start < 0.01:
    stop = time.time()
  return int((stop - start) * sound_speed / 2)

#----------------------------------------------------------


mode, beep, safe_dist, show_days = 0, False, 50, 0
counts = [ [0, 0] for _ in range(8) ]

def save():
  '''
  Save the settings
  '''
  global mode, beep, safe_dist, show_days, counts
  yday = time.localtime().tm_yday
  pickle.dump((mode, beep, safe_dist, show_days, yday, counts), file('sitcat.pickle', 'w'))
  print 'Save:', mode, beep, safe_dist, show_days, yday, counts[:4]

def load():
  '''
  Load the settings
  '''
  global mode, beep, safe_dist, show_days, counts
  yday = 0
  try:
    mode, beep, safe_dist, show_days, yday, c = pickle.load(file('sitcat.pickle'))
    if yday == time.localtime().tm_yday:
      counts = c
  except:
    pass
  print 'Load:', mode, beep, safe_dist, show_days, yday, counts[:4]

def buzz():
  '''
  Buzz for 0.01s
  '''
  GPIO.output(PINS.BUZZER, GPIO.LOW)
  time.sleep(0.01)
  GPIO.output(PINS.BUZZER, GPIO.HIGH)

def led(status):
  '''
  Light on/off or flashing the LED 
  :param status: 'on' or 'off' or 'flashing'
  '''
  if status == 'on':
    v = GPIO.LOW
  elif status == 'off':
    v = GPIO.HIGH
  else:
    v = int(time.time()) % 2
  GPIO.output(PINS.LED_RED, v)
  GPIO.output(PINS.LED_YELLOW, v)

def on_right_key(*args):
  '''
  Called while left key pressed
  '''
  global mode, show_safe
  buzz()
  mode = (mode + 1) % 3
  show_safe = 3
  save()

def on_left_key(*args):
  '''
  Called while right key pressed
  '''
  global beep, safe_dist, show_safe, show_days
  buzz()
  if mode == 0:
    beep = not beep
    if beep:
      buzz()
      time.sleep(0.01)
  elif mode == 1:
    safe_dist = get_distance()
    show_safe = 3
  else:
    show_days = {0:1, 1:3, 3:7, 7:0}[show_days]
  save()

def init():
  '''
  Initialize the program
  '''
  global display, sound_speed
  GPIO.setwarnings(False)
  GPIO.cleanup()
  GPIO.setmode(GPIO.BCM)
  GPIO.setup(PINS.GPIO_TRIGGER, GPIO.OUT, initial = GPIO.LOW)      # Ultrasonic Trigger
  GPIO.setup(PINS.GPIO_ECHO, GPIO.IN)                              # Ultrasonic Echo
  GPIO.setup(PINS.BUZZER, GPIO.OUT, initial = GPIO.HIGH)           # Buzzer 
  GPIO.setup(PINS.LED_RED, GPIO.OUT, initial = GPIO.HIGH)          # Red LED
  GPIO.setup(PINS.LED_YELLOW, GPIO.OUT, initial = GPIO.HIGH)       # Yellow LED
  GPIO.setup(PINS.TACT_LEFT, GPIO.IN, pull_up_down = GPIO.PUD_UP)  # Left key
  GPIO.add_event_detect(PINS.TACT_LEFT, GPIO.FALLING, callback = on_left_key, bouncetime = 500)
  GPIO.setup(PINS.TACT_RIGHT, GPIO.IN, pull_up_down = GPIO.PUD_UP) # Right Key
  GPIO.add_event_detect(PINS.TACT_RIGHT, GPIO.FALLING, callback = on_right_key, bouncetime = 500)
  display = DigitalDisplay()

  temperature = get_temperature()
  print 'Current temperature is', temperature, '*C.'
  sound_speed = 33100 + (60 * temperature)
  print 'Current speed of sound is', sound_speed, 'cm/s.'
  signal.signal(signal.SIGUSR1, on_left_key)
  signal.signal(signal.SIGUSR2, on_right_key)

def done():
  '''
  Stop the program
  '''
  display.show('')
  led('off')
  time.sleep(0.2)
  GPIO.cleanup()

def run():
  '''
  Main loop
  '''
  global mode, beep, safe_dist, show_safe, show_days, counts
  try:
    relax_time = time.time()
    yday = time.localtime().tm_yday
    show_safe = 3
    h = 0
    while True:
      t = time.time()
      if time.localtime(t).tm_yday != yday: # new day
        yday = time.localtime(t).tm_yday
        counts.insert(0, [0, 0])
        counts.pop()
        save()
      d = get_distance()
      if d <= safe_dist + 30:
        counts[0][1] += 1
        if d >= safe_dist:
          counts[0][0] += 1
          h = 0
        else:
          h += 1
          if beep and h > 1:
            buzz()
      else:
        relax_time += 2.5
        if relax_time > t:
          relax_time = t
      led('flashing' if t - relax_time >= 20 * 60 else 'off') # relax after 20 minutes studying ...
      if mode == 0:
        if h > 1:
          s = '%4d' % (d - safe_dist)
        else:
          s = ' .'
      elif mode == 1:
        if show_safe > 0:
          s = '=%3d' % safe_dist
          show_safe -= 1
        else:
          s = '%4d' % d
      else:
        if show_days == 0:
          score = counts[0][0] * 100 / (1 + counts[0][1])
          s = 'C%3d' % score
        else:
          c0, c1 = 0, 1
          for i, j in counts[1 : show_days + 1]:
            c0 += i
            c1 += j
          score = c0 * 100 / c1
          s = '%d%3d' % (show_days, score)
      display.show(s)
      print '    %s [%-4s] %3dcm %ds %s    \r' % (time.ctime(), s, d, t - relax_time, counts[0]),
      os.sys.stdout.flush()
      t += 0.5 - time.time()
      if t > 0:
        time.sleep(t)
  except KeyboardInterrupt:
    print
  except:
    traceback.print_exc()

init()
load()
run()
save()
done()


