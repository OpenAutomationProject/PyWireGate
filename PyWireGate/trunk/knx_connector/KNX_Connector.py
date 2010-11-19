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
from Queue import Empty,Full,Queue
import heapq            
import threading

KNXREADFLAG = 0x00
KNXRESPONSEFLAG = 0x40
KNXWRITEFLAG = 0x80

class knx_connector(Connector):
    CONNECTOR_NAME = 'KNX Connector'
    CONNECTOR_VERSION = 0.2
    CONNECTOR_LOGNAME = 'knx_connector'
    def __init__(self,parent, instanceName):
        self._parent = parent
        self.WG = parent.WG
        self.instanceName = instanceName

        self.KNX = EIBConnection.EIBConnection()
        self.KNXBuffer = EIBConnection.EIBBuffer()
        self.KNXSrc = EIBConnection.EIBAddr()
        self.KNXDst = EIBConnection.EIBAddr()
        
        self.DeviceList = {}
        
        self.sendQueue = KNXSendQueue(maxsize=5000)
        

        self.busmon = BusMonitor.busmonitor(self)
        self.groupsocket = GroupSocket.groupsocket(self)
        self.dpt = DPT_Types.dpt_type(self)
        
        
        self.GrpAddrRegex = re.compile(r"(?:|(\d+)\x2F)(\d+)\x2F(\d+)$",re.MULTILINE)

        ## Deafaultconfig
        defaultconfig = {
            'url':'ip:127.0.0.1',
            'parser' : 'groupsocket',
            'checktime' : 300
        }
        
        ## check Defaultconfig Options in main configfile
        self.WG.checkconfig(self.instanceName,defaultconfig)
        
        ## set local config
        self.config = self.WG.config[self.instanceName]
        
        self._readThread = None
        self._sendThread = None
        self._checkThread = None
        
        ## Start the Thread
        self.start()

    def run(self):
        while self.isrunning:
            ## Create Socket
            try:
                ## wait a second for the Busmon to activate
                if self._sendThread == None:
                    self._sendThread = threading.Thread(target=self._run)
                    self._sendThread.setDaemon(True)
                    self._sendThread.start()
                if self._readThread == None:
                    self._readThread = threading.Thread(target=self._sendloop)
                    self._readThread.setDaemon(True)
                    self._readThread.start()
                if self._checkThread == None:
                    self._checkThread = threading.Thread(target=self._healthCheck)
                    self._checkThread.setDaemon(True)
                    self._checkThread.start()
                

                #self._run()
                #try:
                #    self.KNX.EIBClose()
                #except:
                #    self.WG.errorlog()
            except:
                self.WG.errorlog()
            if self.isrunning:
                self.idle(5)

    def _shutdown(self):
        for rthread in [self._checkThread,self._sendThread,self._readThread]:
            try:
                rthread.join()
            except:
                pass

    def _run(self):
        try:
            self.KNX.EIBSocketURL(self.config['url'])
            self.KNX.EIB_Cache_Enable()
            if self.config['parser'] == "groupsocket":
                self.debug("Using Groupsocket parser")
                self.KNX.EIBOpen_GroupSocket_async(0)
            else:
                self.debug("Using Busmonitor Parser")
                self.KNX.EIBOpenVBusmonitor()

            while self.isrunning:
                ## Check if we are alive and responde until 10 secs
                self.WG.watchdog(self.instanceName,10)
                if self.config['parser'] == "busmonior":
                    self.KNX.EIBGetBusmonitorPacket(self.KNXBuffer)
                    ## Only decode packets larger than 7 octets
                    if len(self.KNXBuffer.buffer) > 7 :
                        self.busmon.decode(self.KNXBuffer.buffer)
                else:
                    self.KNX.EIBGetGroup_Src(self.KNXBuffer,self.KNXSrc,self.KNXDst)
                    ## Only decode packets larger than 1 octet
                    if self.KNXSrc.data not in self.DeviceList:
                        self.DeviceList[self.KNXSrc.data] = self.groupsocket._decodePhysicalAddr(self.KNXSrc.data)
                    if len(self.KNXBuffer.buffer) > 1 :
                        self.groupsocket.decode(self.KNXBuffer.buffer,self.KNXSrc.data,self.KNXDst.data)
        finally:
            self._readThread = None
            self.KNX.EIBClose()


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
        

    def _sendloop(self):
        addr = 0
        msg = []
        try:
            while self.isrunning:
                try:
                    (addr,msg) = self.sendQueue.get(timeout=1)
                    self.KNX.EIBSendGroup(addr,msg)
                except Empty:
                    pass
                except:
                    self.WG.errorlog("Failed send %r %r" % (addr,msg))
        finally:
            self._sendThread = None


    def send(self,msg,dstaddr,flag=KNXWRITEFLAG):
        try:
            addr = self.str2grpaddr(dstaddr)
            if addr:
                apdu = [0]
                if type(msg) == int:
                   apdu.append(flag | msg)
                elif type(msg) == list:
                   apdu = apdu +[flag]+ msg
                else:
                    self.WG.errorlog("invalid Message  %r to %r" % (msg,dstaddr))
                    return 
                self.sendQueue.put((addr,apdu))
                #self.KNX.EIBSendGroup(addr,msg)
        except:
            self.WG.errorlog("Failed send %r to %r" % (msg,dstaddr))

    def setValue(self,dsobj,msg=False,flag=KNXWRITEFLAG):
        try:
            if not msg:
                msg = dsobj.getValue()
            self.debug("SEND %r to %s (%s)" % (msg,dsobj.name,dsobj.id))
            self.send(self.dpt.encode(msg,dsobj=dsobj),dsobj.id,flag=flag)
        except:
            print "----------- ERROR IN KNX_CONNECTOR.setValue ----------------"
            
    def _healthCheck(self):
        ebuf = EIBConnection.EIBBuffer()
        KNX = EIBConnection.EIBConnection()
        self.debug("Starting HealthCheck")
        try:
            KNX.EIBSocketURL(self.config['url'])
            while self.isrunning:
                self.idle(30)
                for physaddr, device in self.DeviceList.items():
                    if not self.isrunning:
                        break
                    if physaddr < 4352:
                        continue
                    id = "%s:PHY_%s" % (self.instanceName,device)
                    self.debug("Checking Voltage for %s" % id)
                    obj = self.WG.DATASTORE.get(id)
                    if 'ignorecheck' in obj.config:
                        continue
                    KNX.EIB_MC_Connect(physaddr)
                    ## read voltage
                    ret = KNX.EIB_MC_ReadADC(1,1,ebuf)
                    try:
                        if ret > -1:
                            value = ebuf.data * .15
                        else:
                            value = -1
                        self.WG.DATASTORE.update(id,value)
                    except:
                        pass
                    KNX.EIBReset()
                    ## wait 500ms between checks
                    self.idle(.5)
                ## wait 5 Minutes
                self.idle(self.config['checktime'])
        finally:
            self._checkThread = None
            KNX.EIBClose()


class KNXSendQueue(Queue):
    def _init(self, maxsize):
        self.maxsize = maxsize
        self.queue = []
        self.activeaddr = []

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
        ## add addr to active addr
        addr = item[0]
        prio = 0
        if len(self.queue) > 10:
            ## if queue size is over 10 use priority
            prio = int(self.activeaddr.count(addr) > 5)
        self.activeaddr.append(addr)
        heapq.heappush(self.queue,(prio,item))

    # Get an item from the queue
    def _get(self):
        prio,item = heapq.heappop(self.queue)
        addr = item[0]
        self.activeaddr.remove(addr)
        return item
        