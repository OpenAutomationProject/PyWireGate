import time
import hashlib
import re
import os
try:
    import rrdtool
except ImportError:
    print "apt-get install python-rrdtool"

from connector import Connector

class rrd_connector(Connector):
    CONNECTOR_NAME = 'RRD Connector'
    CONNECTOR_VERSION = 0.1
    CONNECTOR_LOGNAME = __name__
    def __init__(self,parent,instanceName):
        self._parent = parent
        self.WG = parent.WG
        self.instanceName = instanceName
        self.makeASCII = re.compile(r"[^a-zA-Z0-9_.]+")

        ## Defaultconfig
        defaultconfig = {
            'path':self.WG.scriptpath +"/rrd",
            'defaultstep':300,
            'defaultRRA':'RRA:%s:0.5:1:2160,RRA:%s:0.5:5:2016,RRA:%s:0.5:15:2880,RRA:%s:0.5:180:8760',
            'defaultARCHIV':'AVERAGE,MIN,MAX',
            'defaultVALTYPE':'GAUGE',
            'defaultHEARTBEAT':600,
            'defaultMIN':'-55',
            'defaultMAX':'255000'
            
        }
        
        ## check Defaultconfig Options in main configfile
        self.WG.checkconfig(self.instanceName,defaultconfig)
        
        ## set local config
        self.config = self.WG.config[self.instanceName]
        self.start()
        
    
    def setValue(self,dsobj,msg=False):
        if len(dsobj.connected) == 0:
            if dsobj.lastsource:
                self._setValue(dsobj.lastsource.id)
        
        for objid in dsobj.connected:
            self._setValue(objid)
            
    def _setValue(self,objid):
        try:
            dsobj = self.WG.DATASTORE.dataobjects[objid]
        except KeyError:
            ## if not found ignore
            return 
        rrdfilename = self.config['path'] +"/"+ self.makeASCII.sub("_",(str(dsobj.id)))+".rrd"
        if not os.path.exists(rrdfilename):
            self.create(dsobj,rrdfilename)
        val = dsobj.getValue()
        if val == None or type(val) not in (int,float):
            val = "U"
        else:
            val = "%.2f" % val
        val = "N:%s" % val
        self.debug("set RRD %s VAL: %r" % (rrdfilename,val))
        rrdtool.update(rrdfilename,val)
            


    def create(self,dsobj,rrdfilename):
        rrdarchiv = {}
        if 'rrd' not in dsobj.config:
            dsobj.config['rrd'] = {}
        rrdconfig = dsobj.config['rrd']
        rrdconfig['rrdfilename'] = rrdfilename
        for cfg in ['RRA','ARCHIV','VALTYPE','HEARTBEAT','MIN','MAX']:
            if cfg in rrdconfig:
                rrdarchiv[cfg] = rrdconfig[cfg]
            else:
                rrdarchiv[cfg] = self.config['default%s' % cfg]

        args = []
        datasources = [] + dsobj.connected
        if len(datasources) == 0:
            datasources.append(dsobj.id)


        args.append(str("DS:value:%s:%d:%s:%s" % (rrdarchiv['VALTYPE'],rrdarchiv['HEARTBEAT'],str(rrdarchiv['MIN']),str(rrdarchiv['MAX']))))
        for _a in rrdarchiv['ARCHIV'].split(","):
            for _r in rrdarchiv['RRA'].split(","):
                args.append(str(_r % _a))

        startdate = int(time.time()) - 5 * 86400
        ret = 0
        try:
            ret = rrdtool.create(rrdfilename,'--start',str(startdate), *tuple(args))
        except:
            __import__('traceback').print_exc(file=__import__('sys').stdout)
            print "FAILED WITH %r" % args

        if ret:
            self.debug(rrdtool.error())
    def run(self):
        while self.isrunning:
            self.idle(1)
            
            