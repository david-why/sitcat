#!/usr/bin/python
'''
sitcat.py, written by David Wang and Bob Wang, May 2017
'''

import os, time, pickle
import RPi.GPIO as GPIO
import sakshat

GPIO_TRIGGER = 15
GPIO_ECHO    = 14
GPIO_BUZZER  = 11
GPIO_LKEY    = 18
GPIO_RKEY    = 23
GPIO_LED0    = 8
GPIO_LED1    = 7
RELAX_AFTER  = 20 * 60

mode         = 0
beep         = False
safe_dist    = 50
show_days    = 0
relax_time   = time.time()
counts       = [ [0, 0] for _ in range(8) ]
SAKS         = sakshat.SAKSHAT()

def save():
  global mode, beep, safe_dist, show_days, counts
  yday = time.localtime().tm_yday
  pickle.dump((mode, beep, safe_dist, show_days, yday, counts), file('sitcat.pickle', 'w'))
  print 'Save:', mode, beep, safe_dist, show_days, yday, counts[:4]

def load():
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
  Active the buzzer on NXEZ board
  '''
  GPIO.output(GPIO_BUZZER, GPIO.LOW)
  time.sleep(0.01)
  GPIO.output(GPIO_BUZZER, GPIO.HIGH)

def show(s):
  '''
  Show numbers on NXEZ board.
  param s: str, four digitals or spaces with dots, e.g. '12.34', '1 23.'
  '''
  SAKS.digital_display.show(s)

def led(status):
  '''
  Light on/off/flashing the LED on NXEZ board
  param status: str, 'on' or 'off' or 'flashing'
  '''
  if status == 'on':
    v = GPIO.LOW
  elif status == 'off':
    v = GPIO.HIGH
  else:
    v = int(time.time()) % 2
  GPIO.output(GPIO_LED0, v)
  GPIO.output(GPIO_LED1, v)

def on_right_key():
  '''
  Called while left key pressed
  '''
  global mod
  if mode != 2:
    mode += 1
  else:
    mode = 0
  #print 'Current mode is', mode, '.'
  save()
  buzz()

def on_left_key():
  '''
  Called while right key pressed
  '''
  global beep, safe_dist, show_days
  if mode == 0:
    beep = not beep
    if beep:
      buzz()
      time.sleep(0.01)
  elif mode == 1:
    safe_dist = get_distance()
  else:
    show_days = {0:1, 1:3, 3:7, 7:0}[show_days]
  save()
  buzz()

def on_key_event(pin, status):
  '''
  Called while key pressed or released
  '''
  if pin == GPIO_LKEY and status: # left key pressed
    #print 'Left key pressed.'
    on_left_key()
  if pin == GPIO_RKEY and status: # left key pressed
    #print 'Right key pressed.'
    on_right_key()

def init():
  '''
  Initialize the program, include GPIO and SAKS
  '''
  global sound_speed
  GPIO.setup(GPIO_TRIGGER, GPIO.OUT, initial = GPIO.LOW) # Ultrasonic Trigger
  GPIO.setup(GPIO_ECHO,GPIO.IN)                          # Ultrasonic Echo
  GPIO.setup(GPIO_BUZZER, GPIO.OUT, initial = GPIO.HIGH) # Beeper 
  GPIO.setup(GPIO_LED0, GPIO.OUT, initial = GPIO.HIGH)   # Red LED
  GPIO.setup(GPIO_LED1, GPIO.OUT, initial = GPIO.HIGH)   # Yellow LED
  SAKS.tact_event_handler = on_key_event
  temperature = SAKS.ds18b20.temperature - 5
  if temperature < -100:
    temperature = 27
  print 'Current temperature is', temperature, '*C.'
  sound_speed = 33100 + (60 * temperature)
  print 'Current speed of sound is', sound_speed, 'cm/s.'

def done():
  '''
  Stop the program, reset GPIO and SAKS
  '''
  show('')
  led('off')
  time.sleep(0.2)
  GPIO.cleanup()

def get_distance():
  '''
  Get distance from HC-SR04
  rtype: int, distance in cm
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
  return int((stop - start) * sound_speed / 2)


init()
load()
print 'Running ...'
try:
  yday = time.localtime().tm_yday
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
      elif beep:
        buzz()
    else:
      relax_time += 2.5
      if relax_time > t:
        relax_time = t
    if t - relax_time >= RELAX_AFTER:
      led('flashing')
    else:
      led('off')
    if mode == 0:
      s = '%4d' % (d - safe_dist) if d < safe_dist else ''
    elif mode == 1:
      s = '%4d' % d
    else:
      c0, c1 = 0, 1
      for i, j in counts[1 : show_days + 1] if show_days > 0 else counts[:1]:
        c0 += i
        c1 += j
      score = c0 * 100 / c1
      s = '%d%3d' % (show_days, score)
    show(s)
    print '    %s [%04s] %3dcm %ds %s    \r' % (time.ctime(), s, d, t - relax_time, counts[0]),
    os.sys.stdout.flush()
    t += 0.5 - time.time()
    if t > 0:
      time.sleep(t)
except:
  print
save()
done()
print 'Stop. '
