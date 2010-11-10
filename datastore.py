import sys
import time
import threading

import codecs

try:
    ## use included json in > Python 2.6 
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        print >>sys.stderr, "apt-get install python-simplejson"
        sys.exit(1)


class datastore:
    """
        Datastore Instance
    """
    def __init__(self,parent):
        ####################################################
        ## Function: __init__
        ## Parameter:
        ##    WireGateInstance
        ## Description:
        ##    Contructor for the DATASTORE instance
        ##
        ####################################################
        self._parent = parent
        self.WG = parent.WG
        self.log("DATASTORE starting up")
        self.DBLOADED = False
        self.dataobjects = {}
        
        self.cycleThreadLock = threading.RLock()
        self.cycleThreads = {}
        
        self.locked = threading.RLock()
        self.locked.acquire()
        ## Load JSON Database
        self.load()
        
    
    def update(self,id,val,connector=False):
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
        obj = self.get(id,connector=connector)
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

    def get(self,id,connector=False):
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
            self.dataobjects[id] = dataObject(self,id)
            if connector:
                self.dataobjects[id].config = connector.get_ds_defaults(id)
        ## return it
        self.locked.release()
        return self.dataobjects[id]


    def load(self):
        self.debug("load DATASTORE")
        try:
            db = codecs.open(self.WG.config['WireGate']['datastore'],"rb",encoding='utf-8')
            loaddict = json.load(db)
            db.close()
            for name, obj in loaddict.items():
                self.dataobjects[name] = dataObject(self,obj['id'],obj['name'])
                self.dataobjects[name].lastupdate = obj['lastupdate']
                self.dataobjects[name].config = obj['config']
                self.dataobjects[name].connected = obj['connected']
            self.debug("%d entries loaded in DATASTORE" % len(self.dataobjects))
            self.DBLOADED = True
        except IOError:
            ## no DB File
            pass
        except ValueError:
            ## empty DB File
            self.DBLOADED = True
            pass
        except:
            self.WG.errorlog()
            ## error
            pass
        self.locked.release()


    def save(self):
        self.debug("save DATASTORE")
        if not self.DBLOADED:
            self.debug("No valid config, not saving")
            return False
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
        dbfile = codecs.open(self.WG.config['WireGate']['datastore'],"wb",encoding='utf-8')
        utfdb = json.dumps(savedict,dbfile,ensure_ascii=False,sort_keys=True,indent=3)
        dbfile.write(utfdb)
        dbfile.close()
        

    def attachThread(self,obj,threadObj=False):
        try:
            self.cycleThreadLock.acquire()
            ## check only
            if not threadObj:
                return obj in self.cycleThreads
            self.cycleThreads[obj] = threadObj
        finally:
            self.cycleThreadLock.release()
            
        return self.cycleThreads[obj]
        
        
    def removeThread(self,obj):
        self.cycleThreadLock.acquire()
        del self.cycleThreads[obj]
        self.cycleThreadLock.release()
    

    def shutdown(self):
        self.cycleThreadLock.acquire()
        for obj in self.cycleThreads.keys():
            try:
                self.cycleThreads[obj].cancel()
                self.cycleThreads[obj].join()
            except:
                pass
        self.cycleThreadLock.release()
        self.save()
    
   
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
    def __init__(self,parent,id,name=False):
        self._parent = parent
        self.WG = parent.WG
        
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
            self.name = u"%s:unbekannt-%s" % (namespace, time.strftime("%Y-%m-%d_%H:%M:%S"))
        else:
            self.name = name
        
        if type(self.name) <> unicode:
            ## guess that non unicode is iso8859
            self.name = name.decode("iso-8859-15")
        ## some defaults
        self.value = u""
        self.lastupdate = 0
        self.id = id
        
        ## Fixme: dpt is only KNX specific , should be moved to self.config['KNX:dptid']
        self.dptid = -1
        
        ## connector specific vars
        self.config = {}
        
        self.cyclestore = []
        
        ## connected Logics, communication objects ... goes here
        self.connected = []

    def _setValue(self,refered_self):
        ## self override 
        ## override with connector send function
        if self.namespace:
            try:
                self.write_mutex.acquire()
                self._setValue = self.WG.connectors[self.namespace].setValue
                self.WG.connectors[self.namespace].setValue(refered_self)
            finally:
                self.write_mutex.release()

    def setValue(self,val,send=False):
        if 'sendcycle' in self.config:
            if not self.WG.DATASTORE.attachThread(self):
                self._parent.debug("start Cycle ID: %s" % self.id)
                cycletime = float(self.config['sendcycle']) + self.lastupdate - time.time()
                if cycletime < 0.0:
                    cycletime = 0
                self.cyclestore.append(val)
                _cyclethread = self.WG.DATASTORE.attachThread(self,threading.Timer(cycletime,self._cycle))
                #_cyclethread.setDaemon(1)
                _cyclethread.start()
            else:
                self._parent.debug("ignore Cycle ID: %s" % self.id)
                self.cyclestore.append(val)
        else:
            self._real_setValue(val,send)

    def _real_setValue(self,val,send):
        try:
            ## get read lock
            self.read_mutex.acquire()
            ## get write lock
            self.write_mutex.acquire()
            ## save the modified time
            self.lastupdate = time.time()
            if type(val) == str:
                self.WG.log("Non Unicode Value received for %s" % self.id,'warning')
                val = unicode(val,encoding='iso-8859-15',errors='ignore')
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

    def _cycle(self):
        self._parent.debug("execute Cycle ID: %s" % self.id)
        self.WG.DATASTORE.removeThread(self)
        val = self.getValue()
        if 'sendcycleoption' in self.config:
            if self.config['sendcycleoption'] == 'average' and type(self.cyclestore[0]) in (int,float):
                val = type(self.cyclestore[0])(0)
                for i in self.cyclestore:
                    val += i
                val = val / len(self.cyclestore)
                self._parent.debug("Cycle ID: %s average: %f (%r)" % (self.id, val, self.cyclestore ))
                self.cyclestore = []
        else:
            val = self.cyclestore.pop()
        self._real_setValue(val,False)
