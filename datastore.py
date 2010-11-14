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


try:
    from apscheduler.scheduler import Scheduler as apscheduler
except ImportError:
    print >> sys.stderr, "apt-get install python-apscheduler"
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
        
        self.CYCLER = apscheduler()
        self.CYCLER.start()
        
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
        obj.setValue(val,source=connector)
        
        ##TODO: central subscriber function for other connectore or servers
        
        obj.sendConnected()
        
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
            if hasattr(connector,'get_ds_defaults'):
                self.dataobjects[id].config = connector.get_ds_defaults(id)
        ## return it
        self.locked.release()
        return self.dataobjects[id]


    def load(self):
        self.debug("load DATASTORE")
        try:
            db = codecs.open(self.WG.config['WireGate']['datastore'],"r",encoding=self.WG.config['WireGate']['defaultencoding'])
            loaddict = json.load(db)
            db.close()
            for name, obj in loaddict.items():
                self.dataobjects[name] = dataObject(self,obj['id'],obj['name'])
                self.dataobjects[name].lastupdate = obj['lastupdate']
                self.dataobjects[name].config = obj['config']
                self.dataobjects[name].connected = obj['connected']
                self.dataobjects[name].value = obj['value']
            self.debug("%d entries loaded in DATASTORE" % len(self.dataobjects))
            self.DBLOADED = True
        except IOError:
            ## no DB File
            pass
        except ValueError:
            ## empty DB File
            self.DBLOADED = True
            raise
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
        dbfile = codecs.open(self.WG.config['WireGate']['datastore'],"w",encoding=self.WG.config['WireGate']['defaultencoding'])
        utfdb = json.dumps(savedict,dbfile,ensure_ascii=False,sort_keys=True,indent=3)
        dbfile.write(utfdb)
        dbfile.close()
        

    def shutdown(self):
        self.CYCLER.shutdown()
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
        
        ## set Name to function for Scheduler
        if type(self.name) <> unicode:
            ## guess that non unicode is default encoded
            self.name = name.decode(self.WG.config['WireGate']['defaultencoding'])
        ## some defaults
        self.value = None
        self.lastupdate = 0
        self.lastsource = None
        self.id = id
        
        ## connector specific vars
        self.config = {}
        
        self.cyclestore = []
        self._cyclejob = False
        
        ## connected Logics, communication objects ... goes here
        self.connected = []

    def __repr__(self):
        return json.dumps({
                'name' : self.name,
                'id' : self.id,
                'value' : self.value,
                'lastupdate' : self.lastupdate,
                'config' : self.config,
                'connected' : self.connected
        })

        
    def __str__(self):
        return "%s - %s" % (self.id,self.name)


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

    def setValue(self,val,send=False,source=None):
        if 'sendcycle' in self.config and self.value <> None:
            if not self._cyclejob:
                self._parent.debug("start Cycle ID: %s" % self.id)
                cycletime = float(self.config['sendcycle']) + self.lastupdate - time.time()
                if cycletime < 0.0:
                    cycletime = 0
                    
                ## add value to List
                self.cyclestore.append(val)

                ## 
                repeat = 1
                if 'always' in self.config['sendcycleoption'].split(","):
                    repeat = 0
                self.write_mutex.acquire()
                self._cyclejob = self.WG.DATASTORE.CYCLER.add_interval_job(self._cycle,seconds=cycletime,repeat=repeat)
                self.write_mutex.release()
            else:
                self._parent.debug("ignore Cycle ID: %s" % self.id)
                self.cyclestore.append(val)
        else:
            self._real_setValue(val,send,source=source)

    def _real_setValue(self,val,send,source=None):
        try:
            ## get read lock
            self.read_mutex.acquire()
            ## get write lock
            self.write_mutex.acquire()
            ## save the modified time
            self.lastupdate = time.time()
            self.lastsource = source
            if type(val) == str:
                self.WG.log("Non Unicode Value received for %s" % self.id,'warning')
                val = unicode(val,encoding=self.WG.config['WireGate']['defaultencoding'],errors='ignore')
            self.value = val
            if send:
                self._setValue(self)
        finally:
            ## release locks
            self.write_mutex.release()
            self.read_mutex.release()

    def sendConnected(self):
        self.read_mutex.acquire()
        val = self.getValue()
        self.read_mutex.release()
        for attached in self.connected:
            try:
                self.WG.DATASTORE.dataobjects[attached].setValue(val,True,source=self)
            except:
                self.WG.log("sendconnected failed for %s" % attached,'error')
                __import__('traceback').print_exc(file=__import__('sys').stdout)                
                
        

    def getValue(self,other=''):
          try:
              ## get read lock
              self.read_mutex.acquire()
              ret = self.value
              if other == 'lastupdate':
                  ret = [ret,self.lastupdate]
              return ret
          finally:
              ## release lock
              self.read_mutex.release()

    def _cycle(self):
        self._parent.debug("----------------------execute Cycle ID: %s" % self.id)
        val = None
        cycleopts = []
        if 'sendcycleoption' in self.config:
              cycleopts = self.config['sendcycleoption'].split(",")
        ## average only possible with data in cyclesotre else DivisionByZero
        if len(self.cyclestore) > 0:
            ## Average/Min/Max only possible with int and float
            if type(self.value) in (int,float):
                val = type(self.value)(0)
                if 'average' in cycleopts:
                    for i in self.cyclestore:
                        val += i
                    val = val / len(self.cyclestore)
                    self._parent.debug("Cycle ID: %s average: %f (%r)" % (self.id, val, self.cyclestore ))
                ## default use last
                else:
                    val = self.cyclestore.pop()
            else:
                val = self.cyclestore.pop()
            
        if 'always' in cycleopts:
            if val == None:
                val = self.getValue()
        else:
            self.write_mutex.acquire()
            self._cyclejob = False
            self.write_mutex.release()
        
        ## reset cyclestore
        self.cyclestore = []
        if val <> None:
            self._real_setValue(val,False)
