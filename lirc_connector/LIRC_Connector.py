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
import socket
import select
import re

class lirc_connector(Connector):


    CONNECTOR_NAME = 'LIRC Connector'
    CONNECTOR_VERSION = 0.1
    CONNECTOR_LOGNAME = 'lirc_connector'
    def __init__(self,parent, instanceName):
        self._parent = parent
        self.WG = parent.WG
        self.instanceName = instanceName
        
        defaultconfig = {
            'server' : '127.0.0.1',
            'port' : 8765
        }
        self.WG.checkconfig(self.instanceName,defaultconfig)
        self.config = self.WG.config[instanceName]
        
        self.start()


    def run(self):
        while self.isrunning:
            ## Create Socket
            try:
                self._socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                try:
                    self._socket.connect((self.config['server'],self.config['port']))
                    self._sockfile = self._socket.makefile()
                    self._run()
                except socket.error ,e:
                    if e[0] == 111:
                        print "NO Connection"
                
            finally:
                try:
                    self._socket.close()
                except:
                    pass
            if self.isrunning:
                self.debug("Socket to %s:%d Closed waiting 5 sec" % (self.config['server'],self.config['port']))
                self.idle(5)

    def _run(self):
        while self.isrunning:
            ##00000014de890000 00 BTN_VOLUP X10_CHAN9
            r,w,e = select.select([self._socket],[],[],1)
            if not r:
                continue
            rawmsg = self._sockfile.readline()
            try:
                raw, counter, button, channel = rawmsg.split()
                ## default "LIRC:channel_button
                id = u"%s:%s:%s" % (self.instanceName,channel,button)
                obj = self.WG.DATASTORE.get(id)
                val = int(counter,16)
                if 'toggle' in obj.config:
                    if counter <> "00":
                        continue
                    toggle = obj.config['toggle']
                    val = obj.getValue()
                    if type(val) == int:
                        val = int(val == 0)
                    else:
                        val = 0
                    #if type(obj.config['toggle']) == list:
                    #    toglen = len(val)
                    

                    
                self.WG.DATASTORE.update(id,val)

                id = u"%s:%s" % (self.instanceName,button)
                ## dont't create it "LIRC:Button"
                if id in self.WG.DATASTORE.dataobjects:
                    self.WG.DATASTORE.update(id,channel.decode(self.WG.config['WireGate']['defaultencoding']))
                
            except ValueError:
                self.debug("invalid Data %r" % rawmsg)
            
            
