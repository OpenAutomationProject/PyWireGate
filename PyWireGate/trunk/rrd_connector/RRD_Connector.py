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

        ## Defaultconfig
        defaultconfig = {
            'path':self.WG.scriptpath +"/rrd",
            'defaultstep':300,
            'defaultDS':'value',
            'defaultRRA':'RRA:%s:0.5:1:2160,RRA:%s:0.5:5:2016,RRA:%s:0.5:15:2880,RRA:%s:0.5:180:8760',
            'defaultARCHIV':'AVERAGE,MIN,MAX',
            'defaultVALTYPE':'GAUGE',
            'defaultHEARTBEAT':900,
            'defaultMIN':'-55',
            'defaultMAX':'255000'
            
        }
        
        ## check Defaultconfig Options in main configfile
        self.WG.checkconfig(self.instanceName,defaultconfig)
        
        ## set local config
        self.config = self.WG.config[self.instanceName]
        self.start()
        
    
    def setValue(self,dsobj,msg=False):
        rrdfilename = self.config['path'] +"/"+ re.sub(r"[^\w]","_",(str(dsobj.id)))+".rrd"
        if not os.path.exists(rrdfilename):
            self.create(dsobj,rrdfilename)
        val = "N"
        if len(dsobj.connected) == 0:
            val += ":%.2f" % dsobj.getValue()
        
        for objid in dsobj.connected:
            obj = self.WG.DATASTORE.dataobjects[objid]
            oval = obj.getValue()
            if oval == None or type(oval) not in (int,float):
                oval = "U"
            else:
                oval = "%.2f" % oval
            val += ":%s" % oval

        print "RRD %s VAL: %r" % (rrdfilename,val)
        rrdtool.update(rrdfilename,val)

    def create(self,dsobj,rrdfilename):
        rrdarchiv = {}
        if 'rrd' in dsobj.config:
            for cfg in ['DS','RRA','ARCHIV','VALTYPE','HEARTBEAT','MIN','MAX']:
                if cfg in dsobj.config['rrd']:
                    rrdarchiv[cfg] = dsobj.config['rrd'][cfg]
                else:
                    rrdarchiv[cfg] = self.config['default%s' % cfg] # FIXME: das mag nicht

        #FIXME: needed if single DS per rrd?
        args = []
        datasources = [] + dsobj.connected
        if len(datasources) == 0:
            datasources.append(dsobj.id)


#        for _d in datasources:
#            id = hashlib.md5(_d).hexdigest()[:19]
        args.append(str("DS:%s:%s:%d:%s:%s" % (rrdarchiv.get('DS',self.config['defaultDS']),rrdarchiv.get('VALTYPE',self.config['defaultVALTYPE']),rrdarchiv.get('HEARTBEAT',self.config['defaultHEARTBEAT']),str(rrdarchiv.get('MIN',self.config['defaultMIN'])),str(rrdarchiv.get('MAX',self.config['defaultMAX'])))))
        for _a in rrdarchiv.get('ARCHIV',self.config['defaultARCHIV']).split(","):
            for _r in rrdarchiv.get('RRA',self.config['defaultRRA']).split(","):
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
            
