import time
import thread


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
        self.dataobjects = {}
        
        ## Load XML Database
        self.load()
        
        ## Fixme: should belong to conncetor
        self.readgaconf()
        
    
    ## FIXME: that should belong to the Connector
    def readgaconf(self):
        ga = self.WG.readConfig("/etc/wiregate/eibga.conf")
        for key in ga.keys():
            obj = self.get("KNX:"+key)
            obj.dptid = ga[key]['dptsubid']
            obj.name = ga[key]['name']
    
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
        ## get the Datastore object
        obj = self.get(id)
        self.debug("Updating %s (%s): %r" % (obj.name,id,val))

        ## Set the value of the object
        obj.setValue(val)

        ##TODO: central subscriber function for other connectore or servers

        
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
        try:
            ## check for existence
            type(self.dataobjects[id])
        except KeyError:
            ## create a new one if it don't exist
            self.dataobjects[id] = dataObject(self.WG,id)
        ## return it
        return self.dataobjects[id]


    def load(self):
        ## TODO:
        self.debug("load DATASTORE")
        pass

    def save(self):
        ## TODO:
        self.debug("save DATASTORE")
        pass
    
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
        self.write_mutex = thread.allocate_lock()
        self.read_mutex = thread.allocate_lock()
        ## check for namespace
        namespace = id.split(":",1)
        if len(namespace)>1:
            namespace = namespace[0]
        else:
            ## Fixme: maybe default Namespace
            namespace = ""
        
        ## Initial Name 
        self.name = namespace +":unbekannt-"+time.strftime("%Y-%m-%d_%H:%M:%S")
        
        ## some defaults
        self.value = ""
        self.lastupdate = 0
        self.id = id
        
        ## Fixme: dpt is only KNX specific , should be moved to self.config['KNX:dptid']
        self.dptid = -1
        
        ## connector specific vars
        self.config = {}
        
        ## connected Logics, communication objects ... goes here
        self.connected = {}

    def setValue(self,val):
        try:
            ## get read lock
            self.read_mutex.acquire()
            ## get write lock
            self.write_mutex.acquire()
            ## save the modified time
            self.lastupdate = time.time()
            self.value = val
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

        

