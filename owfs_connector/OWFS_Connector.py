#!/usr/bin/env python
# -*- coding: iso8859-1 -*-
## -----------------------------------------------------
## WireGate.py
## -----------------------------------------------------
## Copyright (c) 2010, knx-user-forum e.V, All rights reserved.
##
## This program is free software; you can redistribute it and/or modify it under the terms
## of the GNU General Public License as published by the Free Software Foundation; either
## version 3 of the License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
## without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
## See the GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along with this program;
## if not, see <http://www.gnu.de/documents/gpl-3.0.de.html>.

from connector import Connector
import connection
import re
import threading
import time

from Queue import Empty,Full,Queue
import heapq            


class owfs_connector(Connector):


    CONNECTOR_NAME = 'OWFS Connector'
    CONNECTOR_VERSION = 0.2
    CONNECTOR_LOGNAME = 'owfs_connector'
    def __init__(self,parent, instanceName):
        self._parent = parent
        self.WG = parent.WG
        self.instanceName = instanceName
        
        self.mutex = threading.RLock()
        
        defaultconfig = {
            'cycletime' : 600,
            'server' : '127.0.0.1',
            'port' : 4304
        }
        self.WG.checkconfig(self.instanceName,defaultconfig)
        self.config = self.WG.config[instanceName]
        
        ## OWFS Connection
        self.owfs = connection.Connection(server=self.config['server'], port=self.config['port'])
        
        ## some regex for identifying Sensors and busses
        self.issensor = re.compile(r"[0-9][0-9]\x2E[0-9a-fA-F]+")
        self.isbus = re.compile(r"\x2Fbus\x2E([0-9])+$", re.MULTILINE)
        
        owfsdir = re.findall("from \x27(.*)\x2F",str(connection))[0]
        ## Sensors and their interfaces 
        self.debug("Read ini file from %s" % owfsdir+"/sensors.ini")
        sensorconfig =  self.WG.readConfig(owfsdir+"/sensors.ini")
        self.supportedsensors = {}
        for sensor in sensorconfig.keys():
            ## add sensors
            self.supportedsensors[sensor] = {}
            cycledefault = defaultconfig['cycletime']
            if 'cycle' in sensorconfig[sensor]:
                self.supportedsensors[sensor]['cycle'] = sensorconfig[sensor]['cycle']
                del sensorconfig[sensor]['cycle']
            if 'interfaces' in sensorconfig[sensor]:
                self.supportedsensors[sensor]['interfaces'] = {}
                for interface in sensorconfig[sensor]['interfaces'].split(","):
                    self.supportedsensors[sensor]['interfaces'][interface] = {'config': {'cycle':cycledefault} }
                ## remove Interface key from dict
                del sensorconfig[sensor]['interfaces']
            
            if 'subtypes' in sensorconfig[sensor]:
                subtypes = sensorconfig[sensor]['subtypes'].split(",")
                self.supportedsensors[sensor]['subtypes'] = {}
                for stype in subtypes:
                    id,subname = stype.split(":",1)
                    try:
                        self.supportedsensors[sensor]['subtypes'][int(id,16)] = subname
                    except:
                        pass
                del sensorconfig[sensor]['subtypes']
                
            for key in sensorconfig[sensor].keys():
                if key.startswith("config_"):
                    try:
                        cfg,interface,config = key.split("_",2)
                        self.supportedsensors[sensor]['interfaces'][interface]['config'][config] = sensorconfig[sensor][key]
                        print self.supportedsensors[sensor]['interfaces'][interface]
                    except KeyError:
                        pass
                        
        #self.supportedsensors =  self.WG.readConfig(owfsdir+"/sensors.ini")
        
        ## Local-list for the sensors
        self.busmaster = {}
        self.sensors = {}
        self.start()

    def checkConfigDefaults(self,obj,default):
        try:
            for cfg in default['config'].keys():
                    if cfg not in obj.config:
                        obj.config[cfg] = default['config'][cfg]
        except:
            pass

    def get_ds_defaults(self,id):
        ## the defualt config for new Datasotre Items
        config = {}
        #if id[-11:] == 'temperature':
        #    config['resolution'] = 10
        return config
    
    def run(self):
        busscantime = 0
        while self.isrunning:
            ## every 10 runs search new sensors
            if busscantime < time.time():
                busscantime = time.time() + self.config['cycletime']
                ## find new sensors
                #self.findsensors()
                try:
                    self.findbusmaster()
                except:
                    ## ignore OWFS Errors
                    pass
            
            ## read the sensors in the local-list
            self.read()
            
            #self.debug(self.sensors)
            
            ## IDLE for cycletime seconds (default 15sec)
            ## Fixme: maybe optimize cycletime dynamic based on busload
            self.idle(.1)
        for busname in self.busmaster.keys():
            if self.busmaster[busname]['readthread'] <> None:
                self.busmaster[busname]['readthread'].join()
            



    def findbusmaster(self,path=""):
        ## search for active busses
        childs = False
        uncachedpath = "/uncached%s" % path
        for bus in self.owfs.dir(uncachedpath):
            bus = bus[9:]
            if self.isbus.search(bus):
                childs = True
                ## get the bus ID
                busname = self.isbus.search(bus)
                if busname:
                    try:
                        if not self.findbusmaster(bus):
                            ## if this has no subbuses add it to the list
                            try:
                                self.mutex.acquire()
                                try:
                                    ## check if bus already in list and set time
                                    self.busmaster[bus]['lastseen'] = time.time()
                                except KeyError:
                                    ## add to list
                                    self.busmaster[bus] = {
                                        'buscycle' : 600,
                                        'nextrun' : 0,
                                        'lastseen' : time.time(),
                                        'readthread' : None,
                                        'readQueue' : ReadQueue(200)
                                    }
                            finally:
                                self.mutex.release()
                            self.findsensors(bus)
                            self.checkBusCycleTime(bus)
                    except:
                        ## ignore all OWFS Errors
                        pass
        return childs


    def findsensors(self,path=""):
        uncachedpath = "/uncached%s" % path
        mincycle = 600
        for sensor in self.owfs.dir(uncachedpath):
            ## remove /uncached/bus.x from sensorname
            sensor = sensor.split("/")[-1]
            ## check if it is really a sensor
            if self.issensor.match(sensor):
                
                self.debug("found Sensor %s at Bus %r" % (sensor,path))
                try:
                    ## Check for supported sensor
                    sensortype=self.owfs.read("%s/type" % sensor)
                except:
                    ## ignore all OWFS Errors
                    continue
                if 'subtypes' in self.supportedsensors[sensortype]:
                    ##check subtypes
                    try:
                        info = ord(self.owfs.read("%s/pages/page.3" % sensor)[0])
                        sensortype += self.supportedsensors[sensortype]['subtypes'][info]
                        self.debug("Sensor Subtype %s is used" % sensortype)
                    except:
                        ## nothing found
                        pass

                if sensortype not in self.supportedsensors:
                    self.debug("unsupported Type: %r" % sensortype)
                    continue                

                if 'interfaces' not in self.supportedsensors[sensortype]:
                    self.debug("Sensor Type: %r has no supported Interfaces" % sensortype)
                    continue
                
                sensorlist = "sensors"
                cycle = 600
                if 'cycle' in self.supportedsensors[sensortype]:
                    cycle = self.supportedsensors[sensortype]['cycle']
                
                try:
                    self.mutex.acquire()
                    print "Sensortype: %s config: %r" % (sensortype,self.supportedsensors[sensortype]['interfaces'])
                    
                    self.sensors[sensor] = {
                        'type':sensortype,
                        'cycle':cycle,
                        'nextrun':0,
                        'present': True,
                        'interfaces': self.supportedsensors[sensortype]['interfaces']
                    }
                finally:
                    self.mutex.release()
                
                self._addQueue(path,sensor)
                    
    def read(self):
        for busname in self.busmaster.keys():
           if not self.busmaster[busname]['readQueue'].empty():
              if not self.busmaster[busname]['readthread']:
                  self.debug("Start read Thread for %s" % busname)
                  threadname = "OWFS-Reader_%s" % busname
                  try:
                      self.mutex.acquire()
                      self.busmaster[busname]['readthread'] = threading.Thread(target=self._readThread,args=[busname],name=threadname)
                      self.busmaster[busname]['readthread'].start()
                  finally:
                      self.mutex.release()


    def _read(self,busname,sensor):
        for iface in self.sensors[sensor]['interfaces'].keys():
            if not self.sensors[sensor]['present'] and iface <> "present":
                ## if not present check only for present
                continue
            ## make an id for the sensor (OW:28.043242a32_temperature
            id = "%s:%s_%s" % (self.instanceName,sensor,iface)
            ## get the Datastore Object and look for config
            obj = self.WG.DATASTORE.get(id)
            
            sensortype = self.sensors[sensor]['type']

            ## recheck config
            self.checkConfigDefaults(obj,self.supportedsensors[sensortype]['interfaces'][iface])
                
            owfspath = "/uncached/%s/%s%s" % (sensor,iface,obj.config.get('resolution',''))
            self.debug("Reading from path %s" % owfspath)

            data = None
            try:
                ## read uncached and put into local-list
                data = self.owfs.read(owfspath)
            except:
                ## ignore all OWFS Errors
                #self.WG.errorlog("Reading from path %s failed" % owfspath)                    
                self.log("Reading from path %s failed" % owfspath)                    

            if data:
                self.debug("%s: %r" % (id,data))
                self.WG.DATASTORE.update(id,data)
            if iface == "present" and str(data) <> "1":
                self.sensors[sensor]['present'] = False
            
        self._addQueue(busname,sensor)

    def _addQueue(self,busname,sensor):
        cycletime = time.time() +self.sensors[sensor]['cycle']
        self.debug("ADDED %s on %s with %s (%d)s" % (sensor,busname, time.asctime(time.localtime(cycletime)),self.sensors[sensor]['cycle']))
        ## FIXME:  not present iButtons should be added to all Busmaster Queues
        #if self.sensors[sensor]['']
        if self.sensors[sensor]['present']:
            self.busmaster[busname]['readQueue'].put((cycletime,sensor))
        else:
            for busmaster in self.busmaster.keys():
                ## add to all busmaster queues
                self.busmaster[busmaster]['readQueue'].put((cycletime,sensor))


    def _readThread(self,busname):
        try:
            while self.isrunning:
                while not self.busmaster[busname]['readQueue'].check():
                    if not self.isrunning:
                        break
                    time.sleep(.1)
                rtime, sensor = self.busmaster[busname]['readQueue'].get()
                self._read(busname,sensor)
        finally:
            if self.isrunning:
                self.busmaster[busname]['readthread'] = None



class ReadQueue(Queue):
    def _init(self, maxsize):
        self.maxsize = maxsize
        self.queue = []

    def _qsize(self):
        return len(self.queue)

    # Check whether the queue is empty
    def _empty(self):
        return not self.queue

    # Check whether the queue is full
    def _full(self):
        return self.maxsize > 0 and len(self.queue) == self.maxsize

    # Put a new item in the queue
    def _put(self, item):
        ## only new Sensors
        if not filter(lambda x: x[1]==item[1],self.queue):
            heapq.heappush(self.queue,item)

    # Get an item from the queue
    def _get(self):
        return heapq.heappop(self.queue)
        
    def check(self):
        if len(self.queue) == 0:
            return False
        next = min(self.queue)
        if len(next)==2:
            next = next[0]
        else:
            next = 0
        return (next <= time.time())