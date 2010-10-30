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
    connector_info = {'name':'OWFS Connector','version':'0.1','logname':'owfs_connector'}
    def __init__(self,WireGateInstance):
        self.WG = WireGateInstance
        try:
            self.config = self.WG.config['owfs']
        except KeyError:
            self.config = {'cycletime':15}
        
        ## onyl localhost FIXME: accept for remote host?
        self.owfs = connection.Connection()
        
        ## some regex for identifying Sensors and busses
        self.issensor = re.compile(r"[0-9][0-9]\x2E[0-9a-fA-F]+")
        self.isbus = re.compile(r"\x2Fbus\x2E[0-9]+$", re.MULTILINE)
        
        ## Sensors and their interfaces .. maybe import from a config file ?
        self.supportedsensors = { 
            "DS1420":[],
            "DS18B20" : [
                'temperature',
                'power'
             ], 
            "DS2438":[
                'temperature',
                'humidity',
                'vis',
                'VDD'
            ] 
        }
        
        ## Local-list for the sensors
        self.busmaster = {}
        self.sensors = {}
        self.start()


    def run(self):
        cnt = 10
        while self.isrunning:
            ## every 10 runs search new sensors
            if cnt == 10:
                cnt = 0
                ## find new sensors
                #self.findsensors()
                self.findbusmaster()
            
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
        for bus in self.owfs.dir("/uncached"+path):
            bus = bus[9:]
            if self.isbus.search(bus):
                nochilds = False
                ## get the bus ID
                busname = self.isbus.search(bus)
                if busname:
                    if self.findbusmaster(bus):
                        ## if this has no subbuses add it to the list
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
                        self.findsensors(bus)
        return nochilds



    def findsensors(self,path=""):
        for sensor in self.owfs.dir("/uncached"+path):
            ## remove /uncached/bus.x from sensorname
            sensor = sensor.split("/")[-1]
            ## check if it is really a sensor
            if self.issensor.match(sensor):
                
                self.debug("found Sensor %s at Bus %r" % (sensor,path))
                
                ## Check for supported sensor
                sensortype=self.owfs.read(sensor+"/type")
                interfaces = []
                try:
                    ## check if sensort is supported
                    interfaces = self.supportedsensors[sensortype]
                    ### add it to the list of active sensors 
                    ## FIXME: check for old sensor no longer active and remove
                    self.busmaster[path]['sensors'][sensor] = {
                        'type':sensortype,
                        'interfaces':interfaces,
                        'resolution':'10' ## Resolution schould be read from Datastore
                    }
                
                except KeyError:
                    self.debug("unsupported Type: "+sensortype)
                    continue
                except:
                    self.WG.errorlog()


    

    def _read(self,busname):
        ## loop through all sensors in lokal busmaster list
        self.debug("Thread running for %s" % busname)
        readtime = time.time()
        for sensor in self.busmaster[busname]['sensors'].keys():
            #self.sensors[sensor]['power'] = self.owfs.read("/"+sensor+"/power")
            
            ## loop through their interfaces
            for get in self.busmaster[busname]['sensors'][sensor]['interfaces']:
                
                ## read uncached and put into local-list
                self.busmaster[busname]['sensors'][sensor][get] = self.owfs.read("/uncached/"+sensor+"/"+get)
                
                ## make an id for the sensor (OW:28.043242a32_temperature
                id = "OW:"+sensor+"_"+get
                
                try:
                    ## only if there is any Data update it in the DATASTORE
                    if self.busmaster[busname]['sensors'][sensor][get]:
                        self.WG.DATASTORE.update(id,self.busmaster[busname]['sensors'][sensor][get])
                except:
                    self.WG.errorlog()
        self.busmaster[busname]['readthread'] = None
        self.debug("Thread for %s finshed in % f secs " % (busname,time.time() - readtime))
                    
    def read(self):
        for busname in self.busmaster.keys():
            if len(self.busmaster[busname]['sensors'])>0:
                if not self.busmaster[busname]['readthread']:
                    self.debug("Start read Thread for %s" % busname)
                    self.busmaster[busname]['readthread'] = threading.Thread(target=self._read,args=[busname])
                    self.busmaster[busname]['readthread'].start()
                