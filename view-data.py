#!/usr/bin/env python

##------------------------------------------------------------------------------
## cgi script to be used to display data from the Arduino Data Logger.
## Copyright (C) 2011 Samuele Santi <redshadow@hackzine.org>
## Under GPLv3
##------------------------------------------------------------------------------

import time,datetime
from email.message import Message
from random import randint,choice

import cgitb
cgitb.enable()

def format_date(d):
    #return datetime.datetime.fromtimestamp(d).strftime("%F %T")
    return d.strftime("%F %T")

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
    _hue_cold = 240/360.0 ## For low values
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
    return '#%02X%02X%02X' % tuple(c*255 for c in colorsys.hls_to_rgb(h, l*1.5, 1))

##------------------------------------------------------------
## Parsed data for testing.
## This is completely random data.
# PARSED_DATA = sorted([
    
#     (
#     ## Timestamp
#     [randint(*[int(time.time())+x for x in (-10*24*3600,0)])]

#     ## Digital sensors
#     + [choice([True,False]) for x in range(5)]

#     ## Analog sensors
#     + [randint(0,1023) for x in range(5)]
#     )

#     ## We want 100 data records
#     for i in xrange(100)

# ], key=lambda t:t[0])

##------------------------------------------------------------
## New data generation
## Generate a record every 10 seconds, for a day

_now = datetime.datetime.now()

_data_logging_period = 5 * 3600 #seconds
_data_logging_tick = 30 #seconds
_analog_max = 1024.0 #float!

## Used to generate data
sensors_digital = [slrgen(minval=0,maxval=1) for x in range(5)]
sensors_analog = [slrgen(minval=0,maxval=_analog_max-1,maxdelta=20) for x in range(7)]

PARSED_DATA = sorted([
    
    (
    ## Timestamp
    #[randint(*[int(time.time())+x for x in (-10*24*3600,0)])]
    [_date]

    ## Digital sensors
    + [bool(x.next()) for x in sensors_digital]

    ## Analog sensors
    + [x.next() for x in sensors_analog]

    )

    ## For each reading time, read a random value from a fake sensor
    for _date in [_now - datetime.timedelta(seconds=delta*_data_logging_tick)
        for delta in range(_data_logging_period/_data_logging_tick)]

], key=lambda t:t[0])

## Register column types. This should be read from configuration
## or CSV table header.
data_columns = ['date']
for i in sensors_digital: data_columns.append('digital')
for i in sensors_analog: data_columns.append('analog')

### --- HTML data table
def _column_label(cid):
    if data_columns[cid] == 'date':
        return "Date"
    elif data_columns[cid] == 'digital':
        return "<span title='Digital Sensor' class='sensor-label-digital'>%d</span>" % cid
    elif data_columns[cid] == 'analog':
        return "<span title='Analog Sensor' class='sensor-label-analog'>%d</span>" % cid
    else:
        return "---"

def format_value(cid, value):
    if data_columns[cid] == 'date':
        return format_date(value)
    elif data_columns[cid] == 'digital':
        #return 'HIGH' if value else 'LOW'
        return '<img src="%s" alt="%s" />' % (('img/lightbulb.png', 'HIGH') if value else ('img/lightbulb_off.png', 'LOW'))
    elif data_columns[cid] == 'analog':
        return "<span title='%d' style='%s'>%s</span>" % (
            value,
            'background-color: %s;' % analog_sensor_color(value/_analog_max),
            "%.1f%%" % (value*100.0/_analog_max))
    else:
        return value

data_table_html = "<table class='data-table'>%s</table>" % "".join(
    [ ## Header
    "<thead><tr>%s</tr></thead>" % "".join(
        ["<th>ID</th>"] +
        ["<th>%s</th>" % _column_label(cid) for cid in range(len(PARSED_DATA[0]))])
    ] +
    
    ## Table content
    ['<tbody>'] +
    ["<tr class='%s'>%s</tr>" % (
        'odd' if rid%2 else 'even',
        "".join(
            ["<td>%d</td>" % rid] + 
            ["<td class='%s'>%s</td>" % (
                'field-%s-value' % data_columns[cid],
                format_value(cid, field))
             for cid,field in enumerate(record)]
        )
    )
    for rid,record in enumerate(PARSED_DATA)
    ] +
    ['</tbody>']
)



### --- Create chart using matplotlib
import os
os.environ['MPLCONFIGDIR'] = '/tmp'
import StringIO
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


fig = plt.gcf()
fig.set_size_inches(20,10)

ax = plt.subplot(111)
#ax.plot_date([datetime.datetime(2011,11,1)+datetime.timedelta(minutes=i) for i in range(20)], [randint(0,100) for i in range(20)], 'r-', color=(1,0.5,0,1))

## Filter by column
_analog_sensors_columns = map(lambda x:x[0], filter(lambda y:y[1] == 'analog', enumerate(data_columns)))
#for cid in xrange(1+len(sensors_digital), 1+len(sensors_digital)+len(sensors_analog)):
for cid in _analog_sensors_columns:
    ax.plot_date(
        [row[0] for row in PARSED_DATA],
        [row[cid] for row in PARSED_DATA],
        '-'
        )
ax.set_title("Arduino sensors log data: %s" % datetime.datetime.now().strftime("%F %T %Z"))
for label in ax.get_xticklabels():
    label.set_rotation(30) 

a=StringIO.StringIO()
plt.savefig(a,format='png',dpi=90)
a.seek(0)
data_plot_png_html = '<img src="data:image/png;base64,%s" alt="The Plot" />' % base64.encodestring(a.read())



### --- Generate response
response=Message()
response.set_type('text/html')
response.set_payload("""\
<!DOCTYPE html>
<html><head>
    <title>Arduino data logger</title>
<style type='text/css'>
.data-table{border-collapse:collapse;font-family:monospace;box-shadow:#888 2px 2px 2px;}
.data-table,.data-table td{border:solid 1px #888;padding:2px 5px;}
.data-table th {text-align:center;background:#ddd;}
.data-table td.field-analog-value {text-align:right;}
.sensor-label-analog {color:#f00;}
.sensor-label-digital {color:#00f;}
tr.even td {background:#fff;}
tr.odd td {background:#eee;}
</style>
</head><body>
    <h1>Arduino data logger</h1>
    %(data_plot_png_html)s
    %(data_table_html)s
</body></html>
""" % dict(
        data_table_html = data_table_html,
        data_plot_png_html = data_plot_png_html,
))

print response.as_string()
