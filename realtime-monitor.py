#!/usr/bin/env python

'''
Realtime monitor for Arduino Data Logger.
'''

import sys,os
from random import choice, randint
import pygame

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

def loop_const_gen(vals):
    while True:
        for v in vals:
            yield v

def loop_sin(steps):
    import math
    while True:
        for s in xrange(steps):
            yield 50 + (math.sin(math.pi * 2 * (s*1.0/steps)) * 50)

pygame.init()
pygame.display.set_caption("Arduino Sensor Monitor")
size = width, height = 1024, 800
screen = pygame.display.set_mode(size)
clock = pygame.time.Clock()
max_fps = 50
FONTS_DIR = os.path.join(os.path.dirname(__file__), 'fonts')

font_sensor_value_large = pygame.font.Font(os.path.join(FONTS_DIR, 'orbitron-bold.ttf'), 40)
font_sensor_label = pygame.font.Font(os.path.join(FONTS_DIR, 'orbitron-light.ttf'), 14)

SENSORS = {
    's1': slrgen(start=None, maxdelta=3, minval=0, maxval=100),
    's2': slrgen(start=None, maxdelta=5, minval=0, maxval=100),
    's3': loop_sin(20),
    's4': loop_const_gen([5,10,12,20,50,80,70,30,20,15,10,9,8,4]),
    's5': slrgen(start=None, maxdelta=5, minval=0, maxval=100),
}
SENSOR_COLORS = {
    's1' : [0xff,0x00,0x00],
    's2' : [0xff,0xff,0x00],
    's3' : [0x00,0xff,0x00],
    's4' : [0x88,0x88,0xff],
    's5' : [0xff,0x00,0xff],
}
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

while 1:
    ## Process events
    for event in pygame.event.get():
        if event.type == pygame.QUIT: sys.exit()
    
    ## Draw/update charts
    #screen.fill((0,0,0))
    
    screen_width, screen_height = screen.get_width(), screen.get_height()
    _chart_row_height = int((screen_height - _padding) * 1.0 / len(SENSORS) - _padding)
    
    _now = pygame.time.get_ticks()
    
    if _force_refresh or not _last_refresh or (_last_refresh + _refresh_time < _now):
        for sensor_id, sensor in enumerate(sorted(SENSORS.keys())):
            _sensor_value = SENSORS[sensor].next()
            
            _sensor_rectangle = [
                screen_width - _sensor_value_box_width - (2*_padding),
                _padding + (sensor_id * (_chart_row_height + _padding)),
                _sensor_value_box_width + _padding,
                _chart_row_height,
                ]
            textContainer = pygame.draw.rect(screen, [0x00,0x00,0x00], _sensor_rectangle, 0)
            textContainer = pygame.draw.rect(screen, SENSOR_COLORS.get(sensor), _sensor_rectangle, 1)
            
            ## Text color may change if limit reached, ..
            _text_color = [0xff,0xff,0xff]
            
            text = font_sensor_value_large.render("%.1f%%" % _sensor_value,True,_text_color)
            textRect = text.get_rect()
            #textRect.topright = (screen.get_rect().width-20,20)
            #textRect.centerx = textContainer.centerx
            textRect.bottom = textContainer.bottom
            textRect.right = textContainer.right - 10
            screen.blit(text, textRect)
            
            labelText = font_sensor_label.render("Analog sensor %s" % sensor,True,SENSOR_COLORS.get(sensor))
            labelTextRect = labelText.get_rect()
            labelTextRect.top = textContainer.top + 10
            labelTextRect.centerx = textContainer.centerx
            screen.blit(labelText, labelTextRect)
            
            ## Chart rectangle
            _chart_rectangle = [
                _padding,
                _padding + (sensor_id * (_chart_row_height+_padding)),
                screen_width - _sensor_value_box_width - (4 * _padding),
                _chart_row_height,
                ]
            #chartContainer = pygame.draw.rect(screen, [0x00,0x00,0x00], _chart_rectangle, 0)
            chartContainer = pygame.draw.rect(screen, SENSOR_COLORS.get(sensor), _chart_rectangle, 1)
            
            _hpadding = 2
            _vpadding = 5
            
            _chart_width = chartContainer.width - 2*_hpadding
            _chart_height = chartContainer.height - 2*_vpadding
            
            _prev_dot_deltax = (((_refresh_count - 1) * _horizontal_unit_length) % _chart_width) if _refresh_count else 0
            _prev_dot_deltay = _chart_height * PREV_VAL.get(sensor, 0) / 100.0
            
            _dot_deltax = (_refresh_count * _horizontal_unit_length) % _chart_width
            _dot_deltay = _chart_height * _sensor_value / 100.0
            
            if _prev_dot_deltax > _dot_deltax:
                _prev_dot_deltax = 0
            
            
            
            _prev_dot_pos = [chartContainer.left + _prev_dot_deltax + _hpadding,
                chartContainer.bottom - _prev_dot_deltay - _vpadding]
            _dot_pos = [chartContainer.left + _dot_deltax + _hpadding,
                chartContainer.bottom - _dot_deltay - _vpadding]
            
            if PREV_VAL.get(sensor, None) is None:
                _prev_dot_pos = _dot_pos
            elif _prev_dot_pos[0] > _dot_pos[0]:
                _prev_dot_pos[0] = 0
            
            ## Clean the surface to draw..
            pygame.draw.rect(screen, [0x00,0x00,0x00], [_dot_pos[0], chartContainer.top, _horizontal_unit_length, chartContainer.height], 0)
            
            
            pygame.draw.line(screen, [0xff,0xff,0xff], _prev_dot_pos, _dot_pos, 2)
            pygame.draw.aaline(screen, [0xff,0xff,0xff], [_prev_dot_pos[0], _prev_dot_pos[1]-1], [_dot_pos[0], _dot_pos[1]-1])
            pygame.draw.aaline(screen, [0xff,0xff,0xff], [_prev_dot_pos[0], _prev_dot_pos[1]+1], [_dot_pos[0], _dot_pos[1]+1])
            
            
            ## Redraw frame
            chartContainer = pygame.draw.rect(screen, SENSOR_COLORS.get(sensor), _chart_rectangle, 1)
            
            ## Update previous sensor value
            PREV_VAL[sensor] = _sensor_value
            
        _refresh_count += 1
        
        ## Set last refresh time
        _last_refresh = _now
    
    #textRect.width = textRect.width+20
    #textRect.height = textRect.height+20
    #textRect.top -= 10
    #textRect.left -= 10
    
    
    
    
    pygame.display.flip()
    
    ## Wait a bit..
    clock.tick(max_fps)
