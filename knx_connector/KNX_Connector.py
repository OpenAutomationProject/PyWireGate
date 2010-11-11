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
        
        #self.sendQueue = Queue.PriorityQueue(maxsize=5000)
        self.sendQueue = KNXSendQueue(maxsize=5000)
        

        self.busmon = BusMonitor.busmonitor(self)
        self.groupsocket = GroupSocket.groupsocket(self)
        self.dpt = DPT_Types.dpt_type(self)
        
        
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
        self._sendThread = threading.Thread(target=self._sendloop)
        self._sendThread.setDaemon(True)
        self._sendThread.start()
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

    def _shutdown(self):
        try:
            self._sendThread.join()
        except:
            pass

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
        

    def _sendloop(self):
        addr = 0
        msg = []
        while self.isrunning:
            try:
                (addr,msg) = self.sendQueue.get(timeout=1)
                self.KNX.EIBSendGroup(addr,msg)
            except Empty:
                pass
            except:
                self.WG.errorlog("Failed send %r %r" % (addr,msg))



    def send(self,msg,dstaddr):
        try:
            if type(msg) <> list:
                self.log("Failed send %r to %r" % (msg,dstaddr),'warn')
                return
            addr = self.str2grpaddr(dstaddr)
            if addr:
                msg = [0,KNXWRITEFLAG] + msg
                self.sendQueue.put((addr,msg))
                #self.KNX.EIBSendGroup(addr,msg)
        except:
            self.WG.errorlog("Failed send %r to %r" % (msg,dstaddr))

    def setValue(self,dsobj,msg=False):
        try:
            if not msg:
                msg = dsobj.getValue()
            self.debug("SEND %r to %s (%s)" % (msg,dsobj.name,dsobj.id))
            self.send(self.dpt.encode(msg,dsobj=dsobj),dsobj.id)
        except:
            print "----------- ERROR IN KNX_CONNECTOR.setValue ----------------"
            

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
        