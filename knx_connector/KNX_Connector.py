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
import re
import EIBConnection
import select
import BusMonitor
import GroupSocket
import DPT_Types

KNXREADFLAG = 0x00
KNXRESPONSEFLAG = 0x40
KNXWRITEFLAG = 0x80

class knx_connector(Connector):
    CONNECTOR_NAME = 'KNX Connector'
    CONNECTOR_VERSION = 0.2
    CONNECTOR_LOGNAME = 'knx_connector'
    def __init__(self,WireGateInstance, instanceName):
        self.WG = WireGateInstance
        self.instanceName = instanceName

        self.KNX = EIBConnection.EIBConnection()
        self.KNXBuffer = EIBConnection.EIBBuffer()
        self.KNXSrc = EIBConnection.EIBAddr()
        self.KNXDst = EIBConnection.EIBAddr()
        self.busmon = BusMonitor.busmonitor(WireGateInstance,self)
        self.groupsocket = GroupSocket.groupsocket(WireGateInstance,self)
        self.dpt = DPT_Types.dpt_type(WireGateInstance)
        
        self.GrpAddrRegex = re.compile(r"(?:|(\d+)\x2F)(\d+)\x2F(\d+)$",re.MULTILINE)

        ## Deafaultconfig
        defaultconfig = {
            'url':'ip:127.0.0.1',
            'parser' : 'groupsocket'
        }
        
        ## check Defaultconfig Options in main configfile
        self.WG.checkconfig(self.instanceName,defaultconfig)
        
        ## set local config
        self.config = self.WG.config[self.instanceName]
        
        ## Start the Thread
        self.start()

    def run(self):
        while self.isrunning:
            ## Create Socket
            try:
                self.KNX.EIBSocketURL(self.config['url'])
                self.KNX.EIB_Cache_Enable()
                if self.config['parser'] == "groupsocket":
                    self.debug("Using Groupsocket parser")
                    self.KNX.EIBOpen_GroupSocket_async(0)
                else:
                    self.debug("Using Busmonitor Parser")
                    self.KNX.EIBOpenVBusmonitor_async()
                
                ## wait a second for the Busmon to activate
                self.idle(1)
                self._run()
                try:
                    self.KNX.EIBClose()
                except:
                    self.WG.errorlog()
            except:
                self.WG.errorlog()
            if self.isrunning:
                self.debug("Socket %r Closed waiting 5 sec" % self.config['url'])
                self.idle(5)

    def _run(self):
        while self.isrunning:
            ## Check if we are alive and responde until 10 secs
            self.WG.watchdog(self.instanceName,10)
            try:
                vbusmonin, vbusmonout, vbusmonerr = select.select([self.KNX.EIB_Poll_FD()],[],[],1)
            except:
                self.WG.errorlog()
                break
            if self.KNX.EIB_Poll_FD() in vbusmonin:
                iscomplete=0
                while True:
                    try:
                        iscomplete = self.KNX.EIB_Poll_Complete()
                        ### evtl. fixed das die abgehackten Telegramme
                        if iscomplete==1:
                            break
                    except:
                        pass
                if not iscomplete:
                    ## Eibd closed connection
                    break
                if iscomplete==1:
                    ## capture BusMon packets
                    if self.config['parser'] == "groupsocket":
                        self.KNX.EIBGetGroup_Src(self.KNXBuffer,self.KNXSrc,self.KNXDst)
                        ## Only decode packets larger than 1 octet
                        if len(self.KNXBuffer.buffer) > 1 :
                            self.groupsocket.decode(self.KNXBuffer.buffer,self.KNXSrc.data,self.KNXDst.data)
                    else:
                        self.KNX.EIBGetBusmonitorPacket(self.KNXBuffer)
                        ## Only decode packets larger than 7 octets
                        if len(self.KNXBuffer.buffer) > 7 :
                            self.busmon.decode(self.KNXBuffer.buffer)
                

    def str2grpaddr(self,addrstr):
        grpaddr = self.GrpAddrRegex.findall(addrstr)
        if not grpaddr:
            return False
        ## regex result 1
        grpaddr = grpaddr[0]
        addr = 0
        ## if GROUP3 Addr
        if grpaddr[0]:
            addr = int(grpaddr[0]) << 11
        addr = addr | (int(grpaddr[1]) << 8)
        addr = addr | int(grpaddr[2])
        return addr
        

    def send(self,msg,dstaddr):
        try:
            addr = self.str2grpaddr(dstaddr)
            if addr:
                msg = [0,KNXWRITEFLAG] +msg
                self.KNX.EIBSendGroup(addr,msg)
        except:
            self.errormsg("Failed send %r to %r" % (msg,dstaddr))

    def setValue(self,dsobj,msg=False):
        if not msg:
            msg = dsobj.getValue()
        self.debug("SEND %r to %s (%s)" % (msg,dsobj.name,dsobj.id))
        self.send(self.dpt.encode(msg,dsobj=dsobj),dsobj.id)
        