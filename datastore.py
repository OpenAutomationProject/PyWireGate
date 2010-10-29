import time

class datastore:
    def __init__(self,WireGateInstance):
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
    
    ## Update the communication Object with value
    def update(self,id,val):
        
        
        ## get the Datastore object
        obj = self.get(id)
        self.debug("Updating %s (%s): %r" % (obj.name,id,val))

        ## Set the value of the object
        obj.setValue(val)

        ##TODO: central subscriber function for other connectore or servers

        
        ## return the object for additional updates
        return obj

    ## Get the Datastore object
    def get(self,id):
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
        self.log(msg,'debug')
        
    def log(self,msg,severity='info',instance=False):
        self.WG.log(msg,severity,"datastore")


class dataObject:
    def __init__(self,WireGateInstance,id,name=False):
        self.WG = WireGateInstance
        
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
        ## Fixme: not threadsave
        
        ## save the modified time
        self.lastupdate = time.time()
        self.value = val

    def getValue(self):
        return self.value

