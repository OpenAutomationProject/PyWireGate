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

class owfs_connector(Connector):
    CONNECTOR_NAME = 'OWFS Connector'
    CONNECTOR_VERSION = 0.2
    CONNECTOR_LOGNAME = 'owfs_connector'
    def __init__(self,parent, instanceName):
        self._parent = parent
        if parent:
            self.WG = parent.WG
        else:
            self.WG = False
        self.instanceName = instanceName
        
        self.mutex = threading.RLock()
        
        defaultconfig = {
            'cycletime' : 15,
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
                cycledefault = sensorconfig[sensor]['cycle']
                del sensorconfig[sensor]['cycle']
            if 'interfaces' in sensorconfig[sensor]:
                self.supportedsensors[sensor]['interfaces'] = {}
                for interface in sensorconfig[sensor]['interfaces'].split(","):
                    self.supportedsensors[sensor]['interfaces'][interface] = {'config': {'cycle':cycledefault} }
                ## remove Interface key from dict
                del sensorconfig[sensor]['interfaces']
            
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
        cnt = 10
        while self.isrunning:
            ## every 10 runs search new sensors
            if cnt == 10:
                cnt = 0
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
            self.idle(self.config['cycletime'])
            
            ## counter increment for sensorsearch
            cnt += 1
            



    def findbusmaster(self,path=""):
        ## search for active busses
        nochilds = True
        uncachedpath = "/uncached%s" % path
        for bus in self.owfs.dir(uncachedpath):
            bus = bus[9:]
            if self.isbus.search(bus):
                nochilds = False
                ## get the bus ID
                busname = self.isbus.search(bus)
                if busname:
                    try:
                        if self.findbusmaster(bus):
                            ## if this has no subbuses add it to the list
                            try:
                                self.mutex.acquire()
                                try:
                                    ## check if bus already in list and set time
                                    self.busmaster[bus]['lastseen'] = time.time()
                                except KeyError:
                                    ## add to list
                                    self.busmaster[bus] = {
                                        'sensors' : {},
                                        'lastseen' : time.time(),
                                        'readthread' : None
                                    }
                            finally:
                                self.mutex.release()
                            self.findsensors(bus)
                            self.checkBusCycleTime(bus)
                    except:
                        ## ignore all OWFS Errors
                        pass
        return nochilds

    def checkBusCycleTime(self,bus):
        pass
    

    def findsensors(self,path=""):
        uncachedpath = "/uncached%s" % path
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
                if sensortype not in self.supportedsensors:
                    self.debug("unsupported Type: %r" % sensortype)
                    continue                
                if 'interfaces' not in self.supportedsensors[sensortype]:
                    self.debug("Sensor Type: %r has no supported Interfaces" % sensortype)
                    continue
                
                ### add it to the list of active sensors 
                ## FIXME: check for old sensor no longer active and remove
                try:
                    self.mutex.acquire()
                    self.busmaster[path]['sensors'][sensor] = {
                        'type':sensortype,
                        'interfaces': self.supportedsensors[sensortype]['interfaces']
                    }
                finally:
                    self.mutex.release()

    

    def _read(self,busname):
        ## loop through all sensors in lokal busmaster list
        self.debug("Thread running for %s" % busname)
        readtime = time.time()
        for sensor in self.busmaster[busname]['sensors'].keys():
            #self.sensors[sensor]['power'] = self.owfs.read("/"+sensor+"/power")
            
            ## loop through their interfaces
            for get in self.busmaster[busname]['sensors'][sensor]['interfaces'].keys():
                resolution = ""
                id = "%s:%s_%s" % (self.instanceName,sensor,get)

                ## get the Datastore Object and look for config
                obj = self.WG.DATASTORE.get(id)
                sensortype = self.busmaster[busname]['sensors'][sensor]['type']
                self.checkConfigDefaults(obj,self.supportedsensors[sensortype]['interfaces'][get])
                if "resolution" in obj.config:
                    resolution = str(obj.config['resolution'])
                    
                owfspath = "/uncached/%s/%s%s" % (sensor,get,resolution)
                self.debug("Reading from path %s" % owfspath)
                data = False
                try:
                    ## read uncached and put into local-list
                    data = self.owfs.read(owfspath)
                except:
                    ## ignore all OWFS Errors
                    #self.WG.errorlog("Reading from path %s failed" % owfspath)                    
                    self.log("Reading from path %s failed" % owfspath)                    

                try:
                    self.mutex.acquire()
                    self.busmaster[busname]['sensors'][sensor][get] = data
                finally:
                    self.mutex.release()
                ## make an id for the sensor (OW:28.043242a32_temperature
                try:
                    ## only if there is any Data update it in the DATASTORE
                    if self.busmaster[busname]['sensors'][sensor][get]:
                        self.WG.DATASTORE.update(id,self.busmaster[busname]['sensors'][sensor][get])
                except:
                    self.WG.errorlog()
        self.busmaster[busname]['readthread'] = None
        self.debug("Thread for %s finshed reading %d sensors in %f secs " % (busname,len(self.busmaster[busname]['sensors']), time.time() - readtime))
                    
    def read(self):
        for busname in self.busmaster.keys():
            if len(self.busmaster[busname]['sensors'])>0:
                if not self.busmaster[busname]['readthread']:
                    self.debug("Start read Thread for %s" % busname)
                    threadname = "OWFS-Reader_%s" % busname
                    try:
                        self.mutex.acquire()
                        self.busmaster[busname]['readthread'] = threading.Thread(target=self._read,args=[busname],name=threadname)
                        self.busmaster[busname]['readthread'].start()
                    finally:
                        self.mutex.release()


