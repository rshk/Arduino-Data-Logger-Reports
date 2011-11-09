#!/usr/bin/env python

#from datetime import datetime
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

sensors_analog = [slrgen(minval=0,maxval=1023,maxdelta=20) for x in range(5)]
sensors_digital = [slrgen(minval=0,maxval=1) for x in range(5)]

PARSED_DATA = sorted([
    
    (
    ## Timestamp
    #[randint(*[int(time.time())+x for x in (-10*24*3600,0)])]
    [_date]

    ## Digital sensors
    #+ [choice([True,False]) for x in range(5)]
    + [bool(x.next()) for x in sensors_digital]

    ## Analog sensors
    #+ [randint(0,1023) for x in range(5)]
    + [x.next() for x in sensors_analog]

    )

    ## Recordings for one day
    #for d in xrange(*[int(time.time())+x for x in (-24*3600,0)]+[10])

    for _date in [_now + datetime.timedelta(seconds=delta*30) for delta in range(5*3600/30)]

], key=lambda t:t[0])


### --- HTML data table
def _column_label(cid):
    if cid==0:
        return "Date"
    elif cid -1 < len(sensors_digital):
        return "S%03d (D)" % cid
    elif cid -1 -len(sensors_digital) < len(sensors_analog):
        return "S%03d (A)" % cid
    else:
        return "---"

data_table_html = "<table class='data-table'>%s</table>" % "".join([
    "<tr>%s</tr>" % "".join([
           "<th></th>"
    ] + [
           "<th>%s</th>" % _column_label(cid)
           for cid in range(len(PARSED_DATA[0]))
    ])
] + [
    "<tr>%s</tr>" % "".join([
           "<td>%d</td>" % rid
    ] + [
           "<td>%s</td>" % (field if cid!=0 else format_date(field))
           for cid,field in enumerate(record)
    ])
    for rid,record in enumerate(PARSED_DATA)
])

### --- matplotlib plot
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
for cid in xrange(1+len(sensors_digital), 1+len(sensors_digital)+len(sensors_analog)):
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
.data-table{border-collapse:collapse;font-family:monospace;}
.data-table,.data-table td{border:solid 1px #888;text-align:right;padding:2px;}
.data-table th {text-align:center;}
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
