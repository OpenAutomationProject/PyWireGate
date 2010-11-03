import time
import threading

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import json
except ImportError:
    import simplejson as json

import sys
import xml.dom.minidom

class datastore:
    """
        Datastore Instance
    """
    def __init__(self,WireGateInstance):
        ####################################################
        ## Function: __init__
        ## Parameter:
        ##    WireGateInstance
        ## Description:
        ##    Contructor for the DATASTORE instance
        ##
        ####################################################
        self.WG = WireGateInstance
        self.log("DATASTORE starting up")
        self.dataobjects = {}
        self.locked = threading.RLock()
        self.locked.acquire()
        self.xmltag = lambda x,y,z='': len(z)>0 and "<%s %s>%s</%s>" % (x,z,y,x) or "<%s>%s</%s>" % (x,y,x)
        ## Load XML Database
        self.load()
        
    
    def update(self,id,val):
        ## Update the communication Object with value
        ####################################################
        ## Function: update
        ## Parameter:
        ##    id: Connector specific id
        ##    val: Value that should be set in the Datastoreobject 
        ## Description:
        ##    update or create a Datastoreobject
        ##    schould be used by all connectors to set their Values
        ####################################################
        ## 
        ## get the Datastore object
        obj = self.get(id)
        self.debug("Updating %s (%s): %r" % (obj.name,id,val))

        ## Set the value of the object
        obj.setValue(val)
        
        ##TODO: central subscriber function for other connectore or servers
        
        for attached in obj.connected:
            try:
                self.dataobjects[attached].setValue(val,True)
            except:
                print "FAILED %s" % attached
                __import__('traceback').print_exc(file=__import__('sys').stdout)                
                pass

        
        ## return the object for additional updates
        return obj

    def get(self,id):
        ####################################################
        ## Function: get
        ## Parameter:
        ##    id: the id to look for in the Datastore
        ## Description:
        ##    returns or create and returns the Dataobejct with ID id
        ##
        ####################################################
        self.locked.acquire()
        try:
            ## check for existence
            type(self.dataobjects[id])
        except KeyError:
            ## create a new one if it don't exist
            self.dataobjects[id] = dataObject(self.WG,id)
        ## return it
        self.locked.release()
        return self.dataobjects[id]


    ## FIXME: that should belong to the Connector
    def readgaconf(self):
        print "SHOULD NOT BE CALLED"
        ga = self.WG.readConfig("/etc/wiregate/eibga.conf")
        for key in ga.keys():
            obj = self.get("KNX:%s" % key)
            obj.config['dptid'] = ga[key]['dptsubid']
            obj.name = ga[key]['name']
            obj._send = self.WG.connectors['KNX'].send


    def load(self):
        ## TODO:
        self.debug("load DATASTORE")
        try:
            db = open(self.WG.config['WireGate']['datastore'],"rb")
            #loaddict = pickle.Unpickler(db).load()
            loaddict = json.load(db)
            db.close()
            for name, obj in loaddict.items():
                self.dataobjects[name] = dataObject(self.WG,obj['id'],obj['name'])
                self.dataobjects[name].lastupdate = obj['lastupdate']
                self.dataobjects[name].config = obj['config']
                self.dataobjects[name].connected = obj['connected']
            self.debug("%d entries loaded in DATASTORE" % len(self.dataobjects))
            self.locked.release()
        except IOError:
            ## no DB File
            pass
            ## Fixme: should belong to conncetor
            self.locked.release()
            self.readgaconf()
        
        except:
            ## error
            pass


    def save(self):
        ## TODO:
        self.debug("save DATASTORE")
        self.locked.acquire()
        savedict = {}
        ## FIXME: user create a __reduce__ method for the Datastoreitem object
        for name,obj in  self.dataobjects.items():
            savedict[name] = {
                'name' : obj.name,
                'id' : obj.id,
                'value' : obj.value,
                'lastupdate' : obj.lastupdate,
                'config' : obj.config,
                'connected' : obj.connected
            }
        dbfile = open(self.WG.config['WireGate']['datastore'],"wb")
        #db = pickle.Pickler(dbfile,-1)
        #db.dump(savedict)
        json.dump(savedict,dbfile,sort_keys=True,indent=3)
        dbfile.close()
        

    def savetoXML(self):
        objitemxml = ""
        for name,obj in  self.dataobjects.items():
             configxml = ""
             for cname,cval in obj.config.items():
                  configxml += self.xmltag(cname,cval)
             objitemxml += self.xmltag(
                    "DSitem",
                    self.xmltag("id",name) + 
                    self.xmltag("value",obj.getValue(),'type=%r' % type(obj.value).__name__) +
                    self.xmltag("config",configxml)
                    )
        self.locked.release()
        xmlout = xml.dom.minidom.parseString(self.xmltag("Datastore",objitemxml))
        #xmlout = xmlout.toprettyxml(indent="  ")
        xmlout = xmlout.toxml()
        ## write binary to preserve UTF8
        open(self.WG.config['WireGate']['datastore'],"wb").write(xmlout)
    
    def debug(self,msg):
        ####################################################
        ## Function: debug
        ## Parameter:
        ##    msg: a message object, could be str/float/dict whateverk
        ## Description:
        ##    Debugging either to logobject or can be changed to log to stdout
        ####################################################
        self.log(msg,'debug')
        
    
    ## Central logging
    def log(self,msg,severity='info',instance=False):
        self.WG.log(msg,severity,"datastore")


class dataObject:
    def __init__(self,WireGateInstance,id,name=False):
        self.WG = WireGateInstance
        
        ## Threadlocking
        self.write_mutex = threading.RLock()
        self.read_mutex = threading.RLock()
        
        ## check for namespace
        namespace = id.split(":",1)
        if len(namespace)>1:
            namespace = namespace[0]
        else:
            ## Fixme: maybe default Namespace
            namespace = ""
        self.namespace = namespace    

        if not name:
            ## Initial Name 
            self.name = "%s:unbekannt-%s" % (namespace, time.strftime("%Y-%m-%d_%H:%M:%S"))
        else:
            self.name = name
        
        ## some defaults
        self.value = ""
        self.lastupdate = 0
        self.id = id
        
        ## Fixme: dpt is only KNX specific , should be moved to self.config['KNX:dptid']
        self.dptid = -1
        
        ## connector specific vars
        self.config = {}
        
        ## connected Logics, communication objects ... goes here
        self.connected = []

    def _setValue(self,refered_self):
        ## self override 
        print "Ovveride now"
        if self.namespace:
            self._setValue = self.WG.connectors[self.namespace].setValue
            self.WG.connectors[self.namespace].setValue(refered_self)
        ## override with connector send function
        pass

    def setValue(self,val,send=False):
        try:
            ## get read lock
            self.read_mutex.acquire()
            ## get write lock
            self.write_mutex.acquire()
            ## save the modified time
            self.lastupdate = time.time()
            self.value = val
            if send:
                self._setValue(self)
        finally:
            ## release locks
            self.write_mutex.release()
            self.read_mutex.release()


    def getValue(self):
          try:
              ## get read lock
              self.read_mutex.acquire()
              return self.value
          finally:
              ## release lock
              self.read_mutex.release()

        

#import json

def JSON2DataStore(text):
    obj = {}
    return obj


def DataStore2JSON(obj):
    text = ""
    return text

class testtwo:
    def __init__(self):
        self.i=10
    def _send(self,val):
        """Hallo"""
        print str(dir(self)) +str(val+self.i)
        
class testthree:
    def __init__(self):
        self.u=1
    def send(self,val):
        """its me"""
        print str(dir(self)) +str(self.u)
    
        

if __name__ == "__main__":
    two = testtwo()
    two._send(20)
    three = testthree()
    two._send = three.send
    two._send(20)
    print two._send
    print dir(two)
    