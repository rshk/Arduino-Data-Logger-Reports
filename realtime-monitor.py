#!/usr/bin/env python

'''
Realtime monitor for Arduino Data Logger.

@todo: avoid overflows: draw on a separate surface that gets blit exactly in place
@todo: support resizing
'''

import sys,os
import datetime
from random import choice, randint
import pygame

class LimitedSizeList(list):
    max_size = 10
    def append(self, object):
        list.append(self, object)
        if self.max_size and (len(self) > self.max_size):
            self.pop(0)

class AnalogSensorBase:
    """Base class for analog sensor objects.
    """
    
    label = ""
    color = None
    values_history = None
    value_generator = None
    
    def __init__(self, label=None, color=None, history_size=500, value_generator=None):
        self.label = label or ""
        self.color = color
        self.values_history = LimitedSizeList()
        self.values_history.max_size = history_size
        self.value_generator = value_generator
    
    def read_current_value(self):
        """To be overwritten by subclasses: read and return 
        the current sensor value.
        """
        return self.value_generator.next()
    
    def read(self):
        """Read value from the sensor"""
        value = self.read_current_value()
        self.values_history.append((datetime.datetime.now(), value))
        return value
    
    def next(self):
        """Used to support iteration"""
        return self.read()
    
    def get_history(self, size=0):
        """Get the last ``size`` history items.
        Each history item is a ``(datetime, value)`` tuple.
        """
        return self.values_history[-size:] # Returns a copy of the history

def slrgen(start=None,mindelta=0,maxdelta=5,minval=0,maxval=1000):
    """Generator of slightly random numbers.
    Distance between numbers is +- a random number between
    `mindelta` and `maxdelta`.
    """
    s = int(start) if start is not None else randint(minval,maxval)
    while True:
        yield s
        s += choice([1,-1]) * randint(mindelta,maxdelta)
        if maxval is not None: s=min(maxval,s)
        if minval is not None: s=max(minval,s)


def analog_sensor_color(val):
    _hue_cold = 300/360.0 ## For low values
    _hue_hot = 0/360.0 ## For high values
    
    _delta = _hue_hot - _hue_cold
    _d2 = _delta * val
    hue = _hue_cold + _d2
    
    import colorsys
    h,s,v = hue, 1.0, 1.0
    rgb = colorsys.hsv_to_rgb(h, s, v)
    h,l,s = colorsys.rgb_to_hls(*rgb)
    greyscale_rgb = colorsys.hls_to_rgb(h, l, 0)
    #return '#%02X%02X%02X' % tuple(c*255 for c in rgb)
    return tuple(c*255 for c in colorsys.hls_to_rgb(h, l*1.5, 1))

def loop_const_gen(vals=None):
    if vals is None:
        vals = [randint(0,100) for i in range(15)]
    while True:
        for v in vals:
            yield v

def loop_sin(steps):
    import math
    while True:
        for s in xrange(steps):
            yield 50 + (math.sin(math.pi * 2 * (s*1.0/steps)) * 50)

def loop_randint(min,max):
    while True:
        yield randint(min, max)

pygame.init()
pygame.display.set_caption("Arduino Sensor Monitor")
size = width, height = 1024, 800
screen = pygame.display.set_mode(size, pygame.RESIZABLE|pygame.DOUBLEBUF)
clock = pygame.time.Clock()
max_fps = 50
show_fps_label = True
FONTS_DIR = os.path.join(os.path.dirname(__file__), 'fonts')

font_sensor_value_large = pygame.font.Font(os.path.join(FONTS_DIR, 'orbitron-bold.ttf'), 40)
font_sensor_label = pygame.font.Font(os.path.join(FONTS_DIR, 'orbitron-light.ttf'), 14)
font_small = pygame.font.Font(os.path.join(FONTS_DIR, 'orbitron-light.ttf'), 12)

ANALOG_SENSORS = {
    's1' : AnalogSensorBase(label='Sensor ONE', color=[0xff,0x00,0x00],
                value_generator=slrgen(start=None, maxdelta=5, minval=0, maxval=100)),
    's2' : AnalogSensorBase(label='Sensor TWO', color=[0xff,0xff,0x00],
                value_generator=loop_const_gen()),
    's3' : AnalogSensorBase(label='Sensor THREE', color=[0x00,0xff,0x00],
                value_generator=loop_sin(20)),
    's4' : AnalogSensorBase(label='Sensor FOUR', color=[0x88,0x88,0xff],
                value_generator=loop_const_gen([5,10,12,20,50,80,70,30,20,15,10,9,8,4])),
    's5' : AnalogSensorBase(label='Sensor FIVE', color=[0xff,0x00,0xff],
                value_generator=loop_randint(0,100)),
}

#SENSORS = {
#    's1': slrgen(start=None, maxdelta=3, minval=0, maxval=100),
#    's2': slrgen(start=None, maxdelta=5, minval=0, maxval=100),
#    's3': loop_sin(20),
#    's4': loop_const_gen([5,10,12,20,50,80,70,30,20,15,10,9,8,4]),
#    's5': slrgen(start=None, maxdelta=5, minval=0, maxval=100),
#}
#SENSOR_COLORS = {
#    's1' : [0xff,0x00,0x00],
#    's2' : [0xff,0xff,0x00],
#    's3' : [0x00,0xff,0x00],
#    's4' : [0x88,0x88,0xff],
#    's5' : [0xff,0x00,0xff],
#}
PREV_VAL = {}

_last_refresh = 0
_refresh_time = 100 #milliseconds

_chart_row_height = 120
_sensor_value_box_width = 180
_padding = 15

screen.fill((0,0,0))

_force_refresh = False
_refresh_count = 0
_horizontal_unit_length = 10

keep_running = True

while keep_running:
    ## Process events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            #sys.exit()
            keep_running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                #sys.exit()
                keep_running = False
            elif event.key == pygame.K_F5:
                ## Should flash
                _force_refresh = True
                screen.fill([0xff,0xff,0xff])
                pygame.time.delay(10)
    
    ## Draw/update charts
    #screen.fill((0,0,0))
    
    screen_width, screen_height = screen.get_width(), screen.get_height()
    _chart_row_height = int((screen_height - _padding) * 1.0 / len(ANALOG_SENSORS) - _padding)
    
    _now = pygame.time.get_ticks()
    
    if _force_refresh or not _last_refresh or (_last_refresh + _refresh_time < _now):
        if _force_refresh:
            _refresh_count = 0 # Restart drawing
            screen.fill([0x00,0x00,0x00])
            _force_refresh = False # Set off
        
        for sensor_count, (sensor_id, sensor) in enumerate(sorted(ANALOG_SENSORS.items())):
            #_sensor_value = SENSORS[sensor_id].next()
            _sensor_value = sensor.read()
            
            ## Rectangle containing the numeric sensor value
            _sensor_rectangle = [
                screen_width - _sensor_value_box_width - (2*_padding),
                _padding + (sensor_count * (_chart_row_height + _padding)),
                _sensor_value_box_width + _padding,
                _chart_row_height,
                ]
            textContainer = pygame.draw.rect(screen, [0x00,0x00,0x00], _sensor_rectangle, 0)
            textContainer = pygame.draw.rect(screen, sensor.color, _sensor_rectangle, 1)
            
            ## Text color may change if some limit reached, ..
            _text_color = [0xff,0xff,0xff]
            
            text = font_sensor_value_large.render("%.1f%%" % _sensor_value, True, _text_color)
            textRect = text.get_rect()
            textRect.bottom = textContainer.bottom
            textRect.right = textContainer.right - 10
            screen.blit(text, textRect)
            
            labelText = font_sensor_label.render(sensor.label, True, sensor.color)
            labelTextRect = labelText.get_rect()
            labelTextRect.top = textContainer.top + 10
            labelTextRect.centerx = textContainer.centerx
            screen.blit(labelText, labelTextRect)
            
            ## Chart rectangle
            _chart_rectangle = [
                _padding,
                _padding + (sensor_count * (_chart_row_height+_padding)),
                screen_width - _sensor_value_box_width - (4 * _padding),
                _chart_row_height,
                ]
            #chartContainer = pygame.draw.rect(screen, [0x00,0x00,0x00], _chart_rectangle, 0)
            chartContainer = pygame.draw.rect(screen, sensor.color, _chart_rectangle, 1)
            
            _hpadding = 2
            _vpadding = 5
            
            _chart_width = chartContainer.width - 2*_hpadding
            _chart_height = chartContainer.height - 2*_vpadding
            
            if _refresh_count > 0:
                ## This is not the first refresh
                _prev_dot_deltax = (((_refresh_count - 1) * _horizontal_unit_length) % _chart_width)
            else:
                ## This is the first refresh
                _prev_dot_deltax = 0
            _prev_dot_deltay = _chart_height * PREV_VAL.get(sensor_id, 0) / 100.0
            
            _dot_deltax = (_refresh_count * _horizontal_unit_length) % _chart_width
            _dot_deltay = _chart_height * _sensor_value / 100.0
            
            if _prev_dot_deltax > _dot_deltax:
                _prev_dot_deltax = 0
            
            
            
            _prev_dot_pos = [chartContainer.left + _prev_dot_deltax + _hpadding,
                chartContainer.bottom - _prev_dot_deltay - _vpadding]
            _dot_pos = [chartContainer.left + _dot_deltax + _hpadding,
                chartContainer.bottom - _dot_deltay - _vpadding]
            
            if PREV_VAL.get(sensor_id, None) is None:
                _prev_dot_pos = _dot_pos
            elif _prev_dot_pos[0] > _dot_pos[0]:
                _prev_dot_pos[0] = 0
            
            ## Clean the surface to draw..
            pygame.draw.rect(screen, [0x00,0x00,0x00], [_dot_pos[0], chartContainer.top, _horizontal_unit_length, chartContainer.height], 0)
            
            #pygame.draw.rect(screen, [0x00,0x00,0x00], [_dot_pos[0]+_horizontal_unit_length, chartContainer.top, _horizontal_unit_length*2, chartContainer.height], 0)
            
            ## Draw cursor
            pygame.draw.rect(screen, [0xff,0xff,0xff], [_dot_pos[0]+_horizontal_unit_length, chartContainer.top, 2, chartContainer.height], 0)
            
            ## Draw line (trick to antialias)
            
            for _dd in [-2, -1, 0, 1, 2]:
                pygame.draw.aaline(screen, [0xff,0xff,0xff], [_prev_dot_pos[0]+_dd, _prev_dot_pos[1]], [_dot_pos[0]+_dd, _dot_pos[1]])
                pygame.draw.aaline(screen, [0xff,0xff,0xff], [_prev_dot_pos[0], _prev_dot_pos[1]+_dd], [_dot_pos[0], _dot_pos[1]+_dd])
            pygame.draw.circle(screen, [0xff,0xff,0xff], _dot_pos, 2)
            #pygame.draw.circle(screen, [0xff,0xff,0xff], _dot_pos, 4)
            #pygame.draw.circle(screen, [0,0,0], _dot_pos, 2)
            #pygame.draw.circle(screen, [0xff,0xff,0xff], _prev_dot_pos, 4)
            #pygame.draw.circle(screen, [0,0,0], _prev_dot_pos, 2)
            
            #pygame.draw.aaline(screen, [0xff,0xff,0xff], [_prev_dot_pos[0], _prev_dot_pos[1]-1.5], [_dot_pos[0], _dot_pos[1]-1.5])
            #pygame.draw.aaline(screen, [0xff,0xff,0xff], [_prev_dot_pos[0], _prev_dot_pos[1]-.5], [_dot_pos[0], _dot_pos[1]-.5])
            #pygame.draw.aaline(screen, [0xff,0xff,0xff], [_prev_dot_pos[0], _prev_dot_pos[1]+1.5], [_dot_pos[0], _dot_pos[1]+1.5])
            #pygame.draw.aaline(screen, [0xff,0xff,0xff], [_prev_dot_pos[0], _prev_dot_pos[1]+.5], [_dot_pos[0], _dot_pos[1]+.5])
            
            
            ## Redraw frame
            chartContainer = pygame.draw.rect(screen, sensor.color, _chart_rectangle, 1)
            
            ## Update previous sensor value
            PREV_VAL[sensor_id] = _sensor_value
            
        _refresh_count += 1
        
        ## Set last refresh time
        _last_refresh = _now
    
    #textRect.width = textRect.width+20
    #textRect.height = textRect.height+20
    #textRect.top -= 10
    #textRect.left -= 10
    
    ## FPS LABEL
    if show_fps_label:
        _fps = clock.get_fps()
        if _fps >= 40:
            _col = [0x00,0xff,0x00]
        elif _fps >= 25:
            _col = [0xff,0xff,0x00]
        else:
            _col = [0xff,0x00,0x00]
        text = font_small.render("%d FPS" % clock.get_fps(),True,_col)
        textRect = text.get_rect()
        textRect.bottomleft = 0,screen.get_height()
        textRect.width=max(40,textRect.width)
        screen.fill([0,0,0], textRect)
        screen.blit(text, textRect)
    
    
    pygame.display.flip()
    
    ## Wait a bit..
    clock.tick(max_fps)

pygame.quit()
