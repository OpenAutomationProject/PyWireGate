import time

class datastore:
    def __init__(self,WireGateInstance):
        self.WG = WireGateInstance
        self.dataobjects = {}
        self.readgaconf()
    
    def readgaconf(self):
        ga = self.WG.readConfig("/etc/wiregate/eibga.conf")
        for key in ga.keys():
            obj = self.get("KNX:"+key)
            obj.dptid = ga[key]['dptsubid']
            obj.name = ga[key]['name']
    
    def update(self,id,val):
        try:
            type(self.dataobjects[id])
        except KeyError:
            self.dataobjects[id] = dataObject(self.WG,id)
        self.debug("Updating %s (%s): %r" % (self.dataobjects[id].name,id,val))
        self.dataobjects[id].setValue(val)
        return self.dataobjects[id]

    def get(self,id):
        try:
            return self.dataobjects[id]
        except KeyError:
            self.dataobjects[id] = dataObject(self.WG,id)
            return self.dataobjects[id]


    def load(self):
        self.debug("load DATASTORE")
        pass

    def save(self):
        self.debug("save DATASTORE")
        pass
    
    def debug(self,msg):
        self.log(msg,'debug')
        
    def log(self,msg,severity='info',instance=False):
        self.WG.log(msg,severity,"datastore")


class dataObject:
    def __init__(self,WireGateInstance,id,name=False):
        self.WG = WireGateInstance
        namespace = id.split(":",1)[0]
        self.name = namespace +":unbekannt-"+time.strftime("%Y-%m-%d_%H:%M:%S")
        self.value = ""
        self.lastupdate = 0
        self.id = id
        self.dptid = -1
        self.config = {}

    def setValue(self,val):
        self.lastupdate = time.time()
        self.value = val

    def getValue(self):
        return self.value

