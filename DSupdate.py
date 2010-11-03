import getopt
import ConfigParser
try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import json
except ImportError:
    import simplejson as json


import datastore

import sys

class dbloader:
    def __init__(self,config,fname):
        self.config = config
        self.dataobjects = {}
        ## load datastore
        self.load()
        if config['type'].upper() == "KNX":
            self.KNXloader(fname)
        elif config['type'].upper() == "OWFS":
            self.OWFSloader(fname)
        self.save()

    def readConfig(self,configfile):
        cfile = open(configfile,"r")
        ## fix for missingsectionheaders
        while True:
            pos = cfile.tell()
            if cfile.readline().startswith("["):
                break
        cfile.seek(pos)
        config = {}
        configparse = ConfigParser.SafeConfigParser()
        configparse.readfp(cfile)
        for section in configparse.sections():
            options = configparse.options(section)
            config[section] = {}
            for opt in options:
                try:
                    config[section][opt] = configparse.getint(section,opt)
                except ValueError:
                    try:
                        config[section][opt] = configparse.getfloat(section,opt)
                    except ValueError:
                        config[section][opt] = configparse.get(section,opt)
        
        return config

    def KNXloader(self,fname):
        ga = self.readConfig(fname)
        for key in ga.keys():
            id = "%s:%s" % (self.config['namespace'],key)
            self.dataobjects[id] = datastore.dataObject(False,id,unicode(ga[key]['name'],errors='ignore'))
            self.dataobjects[id].config['dptid'] = ga[key]['dptsubid']

    def OWFSloader(self,fname):
        ow = self.readConfig(fname)
        for key in ow.keys():
            id = "%s:%s_temperature" % (self.config['namespace'],key)
            print "add %s " % id
            self.dataobjects[id] = datastore.dataObject(False,id,unicode(ow[key]['name'],errors='ignore'))
            if 'resolution' in ow[key]:
                self.dataobjects[id].config['resolution'] = ow[key]['resolution']
            if 'eib_ga_temp' in ow[key]:
                if len(ow[key]['eib_ga_temp']) >0:
                    knxid = "KNX:%s" % ow[key]['eib_ga_temp']
                    print "Try to attach to  %s " % knxid
                    self.dataobjects[id].connected.append(knxid)
                    print "attaached"


    def debug(self,msg=''):
        print msg

    def load(self):
        ## TODO:
        self.debug("load DATASTORE")
        try:
            db = open(self.config['datastore'],"rb")
            #loaddict = pickle.Unpickler(db).load()
            loaddict = json.load(db)
            db.close()
            for name, obj in loaddict.items():
                self.dataobjects[name] = datastore.dataObject(False,obj['id'],obj['name'])
                self.dataobjects[name].lastupdate = obj['lastupdate']
                self.dataobjects[name].config = obj['config']
                self.dataobjects[name].connected = obj['connected']
            self.debug("%d entries loaded in DATASTORE" % len(self.dataobjects))
        except:
            ## no DB File
            print "DB not found"
            pass
            ## Fixme: should belong to conncetor
        


    def save(self):
        ## TODO:
        self.debug("save DATASTORE")
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
        dbfile = open(self.config['datastore'],"wb")
        #db = pickle.Pickler(dbfile,-1)
        #db.dump(savedict)
        json.dump(savedict,dbfile,sort_keys=True,indent=3)
        dbfile.close()
        for i in savedict.keys():
            if len(savedict[i]['connected'])>0:
                print savedict[i]


if __name__ == "__main__":
        import os
        import sys
        import getopt
        try:
            opts, args = getopt.getopt(sys.argv[1:], "f:d:n:t:", ["file=","datastore=","namespace=","type="])
        except getopt.GetoptError:
            print "Fehler"
            sys.exit(2)
        config = {
            'datastore' : 'datastore.db',
            'namespace' : 'KNX',
            'type' : False
        }
        fname = False
        for opt, arg in opts:
            if opt in ("-d","--datastore"):
                config['datastore'] = arg

            if opt in ("-n","--namespace"):
                config['namespace'] = arg

            if opt in ("-t","--type"):
                config['type'] = arg

            if opt in ("-f","--file"):
                fname = arg

        if not fname:
            print "no configfilename"
            sys.exit(1)
        if not config['type']:
            config['type'] = config['namespace']
        dbloader(config,fname)

