#!/usr/bin/python
'''
sitcat.py, by Wangs, May~Oct 2017
  Written by David Wang
'''

import os, time, pickle, signal
import RPi.GPIO as GPIO
from sakshat import SAKSHAT
from sakspins import SAKSPins as PINS

SAKS = SAKSHAT()

def get_distance_once():
  '''
  Get distance from HC-SR04
  :return: int, distance in cm
  '''
  GPIO.output(PINS.UART_TXD, GPIO.HIGH)
  time.sleep(0.1)
  GPIO.output(PINS.UART_TXD, GPIO.LOW)
  stop = start = time.time()
  while GPIO.input(PINS.UART_RXD) == GPIO.LOW and stop - start < 0.1:
    stop = time.time()
  stop = start = time.time()
  while GPIO.input(PINS.UART_RXD) == GPIO.HIGH and stop - start < 0.1:
    stop = time.time()
  return int((stop - start) * 34300 / 2) # sound speed is 34300 cm/s

def get_distance():
  d = 0
  while d < 8:
    d = get_distance_once()
  return d

def buzz():
  '''
  Buzz for 0.01s
  '''
  SAKS.buzzer.beep(0.01)

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
  if v:
    SAKS.ledrow.off()
  else:
    SAKS.ledrow.on()

#--------------------------------------------------------------------

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

def on_right_key(*args):
  '''
  Called while right key pressed
  '''
  global mode, show_safe
  buzz()
  mode = (mode + 1) % 3
  show_safe = 3
  save()

def on_left_key(*args):
  '''
  Called while left key pressed
  '''
  global beep, safe_dist, show_safe, show_days
  buzz()
  if mode == 0:
    beep = not beep
    if beep:
      for i in range(5):
        buzz()
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
  GPIO.setup(PINS.UART_TXD, GPIO.OUT, initial = GPIO.LOW)      # Ultrasonic Trigger
  GPIO.setup(PINS.UART_RXD, GPIO.IN)                              # Ultrasonic Echo
  GPIO.remove_event_detect(PINS.TACT_LEFT)
  GPIO.add_event_detect(PINS.TACT_LEFT, GPIO.FALLING, callback = on_left_key, bouncetime = 500)
  signal.signal(signal.SIGUSR1, on_left_key)                  # SIGUSR1 as left key
  GPIO.remove_event_detect(PINS.TACT_RIGHT)
  GPIO.add_event_detect(PINS.TACT_RIGHT, GPIO.FALLING, callback = on_right_key, bouncetime = 500)
  signal.signal(signal.SIGUSR2, on_right_key)                 # SIGUSR2 as right key

def done():
  '''
  Stop the program
  '''
  SAKS.digital_display.off()
  SAKS.ledrow.off()

def run():
  '''
  Main loop
  '''
  global show_safe
  try:
    relax_time = time.time()
    yday = time.localtime().tm_yday
    show_safe = 3
    far_away = 0
    h = 0
    while True:
      t = time.time()
      if time.localtime(t).tm_yday != yday: # new day
        yday = time.localtime(t).tm_yday
        counts.insert(0, [0, 0])
        counts.pop()
        save()
      d = get_distance()
      if d < 5:
        d = get_distance()
      if d <= safe_dist + 30:
        far_away /= 10
        counts[0][1] += 1
        if d >= safe_dist:
          counts[0][0] += 1
          h = 0
        else:
          h += 1
          if beep and h > 1:
            buzz()
      else:
        far_away += 1
        h = -1
        relax_time += 2.5
        if relax_time > t or t - relax_time >= 60 * 60:
          relax_time = t
      led('flashing' if t - relax_time >= 20 * 60 else 'off') # relax after 20 minutes studying ...
      if mode == 0:
        s = '%4d' % (d - safe_dist) if h > 1 else '    .' if h < 0 else ' .   '
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
      if far_away > 120:
        s = '    '
      SAKS.digital_display.show(s)
      print '    %s [%-4s] %3dcm %ds %s    \r' % (time.ctime(), s, d, t - relax_time, counts[0]),
      os.sys.stdout.flush()
      t += 0.5 - time.time()
      if t > 0:
        time.sleep(t)
  except KeyboardInterrupt:
    print

init()
load()
run()
save()
done()


