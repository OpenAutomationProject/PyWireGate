try:
    import rrdtool
except ImportError:
    print "apt-get install python-rrdtool"

from connector import Connector

class rrd_connector(Connector):
    pass
