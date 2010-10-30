try:
    import rrdtool
except ImportError:
    print "apt-get install python-rrdtool"

from connector import Connector

class rrd_connector(Connector):
    CONNECTOR_NAME = 'RRD Connector'
    CONNECTOR_VERSION = 0.1
    CONNECTOR_LOGNAME = __name__
    pass
