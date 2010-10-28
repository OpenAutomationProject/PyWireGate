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

class owfs_connector(Connector):
    connector_info = {'name':'OWFS Connector','version':'0.1','logname':'owfs_connector'}
    def __init__(self,WireGateInstance):
        self.WG = WireGateInstance
        try:
            self.config = self.WG.config['owfs']
        except KeyError:
            self.config = {'cycletime':15}
        self.owfs = connection.Connection()
        self.issensor = re.compile(r"^\x2F[0-9][0-9]")
        self.isbus = re.compile(r"^\x2Fbus\x2E([0-9]+)")
        self.supportedsensors = { "DS1420":[],"DS18B20" : ['temperature'] }
        self.sensors = {}
        self.start()

    def findsensors(self):
        for sensor in self.owfs.dir("/"):
            if self.issensor.match(sensor):
                sensortype=self.owfs.read(sensor+"/type")
                interfaces = []
                try:
                    interfaces = self.supportedsensors[sensortype]
                    self.sensors[sensor[1:]] = {'type':sensortype,'interfaces':interfaces,'resolution':'10'}
                except KeyError:
                    self.debug("unsupported Type: "+sensortype)
                    continue
                except:
                    self.WG.errorlog()


            elif self.isbus.findall(sensor):
                self.debug("BUSTIME: "+str(self.owfs.read(sensor+"/interface/statistics/bus_time")))

    
    def run(self):
        cnt = 10
        while self.isrunning:
            if cnt == 10:
                cnt = 0
                self.findsensors()
            self.read()
            #self.debug(self.sensors)
            self.idle(self.config['cycletime'])
            cnt += 1
            
    def read(self):
        for sensor in self.sensors.keys():
            self.sensors[sensor]['power'] = self.owfs.read("/"+sensor+"/power")
            for get in self.sensors[sensor]['interfaces']:
                self.sensors[sensor][get] = self.owfs.read("/"+sensor+"/"+get+self.sensors[sensor]['resolution'])
                id = "OW:"+sensor+"_"+get
                try:
                    self.WG.DATASTORE.update(id,self.sensors[sensor][get])
                except:
                    self.WG.errorlog(msg)

                    
