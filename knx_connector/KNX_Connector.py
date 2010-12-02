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
import time        


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

        #self.KNX = EIBConnection.EIBConnection()
        self.KNX = countEIBConnection()
        
        self.cKNX = countEIBConnection()
        
        self.KNXBuffer = EIBConnection.EIBBuffer()
        self.KNXSrc = EIBConnection.EIBAddr()
        self.KNXDst = EIBConnection.EIBAddr()
        
        self.eibmutex = threading.RLock()
        
        self.DeviceList = {}
        self.DeviceListLock = threading.RLock()
        
        self.sendQueue = KNXSendQueue(maxsize=5000)
        self.QueueWaitTime = 0.0

        self.busmon = BusMonitor.busmonitor(self)
        self.groupsocket = GroupSocket.groupsocket(self)
        self.dpt = DPT_Types.dpt_type(self)
        
        
        self.AddrRegex = re.compile(r"(?:|(\d+)[\x2F|\x2E])(\d+)[\x2F|\x2E](\d+)$",re.MULTILINE)

        ## Deafaultconfig
        defaultconfig = {
            'url':'ip:127.0.0.1',
            'parser' : 'groupsocket',
            'checktime' : 0
        }
        
        ## check Defaultconfig Options in main configfile
        self.WG.checkconfig(self.instanceName,defaultconfig)
        
        ## set local config
        self.config = self.WG.config[self.instanceName]
        
        self._readThread = threading.Thread()
        self._sendThread = threading.Thread()
        self._checkThread = threading.Thread()
        
        
        ## Start the Thread
        self.start()

    def run(self):
        cnt = 0
        while self.isrunning:
            ## Create Socket
            if cnt == 60 and self.isrunning:
                self.statistics()
            try:
                ## wait a second for the Busmon to activate
                if not self._readThread.isAlive():
                    self._readThread = threading.Thread(target=self._sendloop,name="%s_read" % self.instanceName)
                    self._readThread.setDaemon(0)
                    self._readThread.start()
                if not self._sendThread.isAlive():
                    self._sendThread = threading.Thread(target=self._run,name="%s_send" % self.instanceName)
                    self._sendThread.setDaemon(0)
                    self._sendThread.start()

                if not self._checkThread.isAlive():
                    self._checkThread = threading.Thread(target=self._healthCheck,name="%s_check" % self.instanceName)
                    self._checkThread.setDaemon(0)
                    self._checkThread.start()
                

                #self._run()
                #try:
                #    self.KNX.EIBClose()
                #except:
                #    self.WG.errorlog()
            except:
                self.WG.errorlog()
            if self.isrunning:
                cnt +=1
                self.idle(5)

    def _shutdown(self):
        ##self.statistics()
        for rthread in [self._checkThread,self._sendThread,self._readThread]:
            try:
                if rthread.isAlive():
                    rthread.join(2)
            except:
                pass

    def _run(self):
        try:
            self.KNX.EIBSocketURL(self.config['url'])
            self.KNX.EIB_Cache_Enable()
            if self.config['parser'] == "groupsocket":
                self.debug("Using Groupsocket parser")
                #self.KNX.EIBOpen_GroupSocket_async(0)
                self.KNX.EIBOpen_GroupSocket(0)
            else:
                self.debug("Using Busmonitor Parser")
                #self.KNX.EIBOpenVBusmonitor()
                self.KNX.EIBOpenVBusmonitor()

            while self.isrunning:
                ## Check if we are alive and responde until 10 secs
                self.WG.watchdog(self.instanceName,10)
                if self.config['parser'] == "groupsocket":
                    self.KNX.EIBGetGroup_Src(self.KNXBuffer,self.KNXSrc,self.KNXDst)
                    ## Only decode packets larger than 1 octet
                    try:
                        self.DeviceListLock.acquire()
                        if self.KNXSrc.data not in self.DeviceList:
                            self.DeviceList[self.KNXSrc.data] = self.groupsocket._decodePhysicalAddr(self.KNXSrc.data)
                    finally:
                        self.DeviceListLock.release()
                    if len(self.KNXBuffer.buffer) > 1 :
                        self.groupsocket.decode(self.KNXBuffer.buffer,self.KNXSrc.data,self.KNXDst.data)
                else:
                    self.KNX.EIBGetBusmonitorPacket(self.KNXBuffer)
                    ## Only decode packets larger than 7 octets
                    if len(self.KNXBuffer.buffer) > 7 :
                        self.busmon.decode(self.KNXBuffer.buffer)

        finally:
            self.KNX.EIBClose()


    def str2addr(self,addrstr):
        grpaddr = self.AddrRegex.findall(addrstr)
        if not grpaddr:
            return False
        ## regex result 1
        grpaddr = grpaddr[0]
        addr = 0
        ## if GROUP3 Addr
        if grpaddr[0]:
            if addrstr.find(".") < 1:
                addr = int(grpaddr[0]) << 11
            else:
                addr = int(grpaddr[0]) << 12
        addr = addr | (int(grpaddr[1]) << 8)
        addr = addr | int(grpaddr[2])
        return addr

        

    def _sendloop(self):
        addr = 0
        msg = []
        self.readconfig()
        try:
            while self.isrunning:
                try:
                    (addr,msg,wtime) = self.sendQueue.get(timeout=1)
                    wtime = time.time() - wtime
                    try:
                        self.eibmutex.acquire()
                        self.QueueWaitTime += wtime
                        print "ADDR %r -- MSG %r" % (addr,msg)
                        self.KNX.EIBSendGroup(addr,msg)
                    finally:
                        self.eibmutex.release()
                except Empty:
                    pass
                except:
                    self.WG.errorlog("Failed send %r %r" % (addr,msg))
        finally:
            #self._sendThread = None
            pass


    def send(self,msg,dstaddr,flag=KNXWRITEFLAG):
        try:
            addr = self.str2addr(dstaddr)
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
        self.debug("Starting HealthCheck")
        try:
            self.cKNX.EIBSocketURL(self.config['url'])
            self.idle(10)
            while self.isrunning:
                if self.config['checktime'] > 0:
                    ## wait 5 Minutes
                    self.idle(self.config['checktime'])
                    try:
                        self.DeviceListLock.acquire()
                        devices = self.DeviceList.items()
                    finally:
                        self.DeviceListLock.release()
                    for physaddr, device in devices:
                        while self.sendQueue.qsize() > 5 and self.isrunning:
                            ## no voltage check on higher busload
                            self.debug("SendQueue to busy wait check Voltage")
                            self.idle(5)
                        if not self.isrunning:
                            break
                        if physaddr < 4352:
                            continue
                        id = "%s:PHY_%s" % (self.instanceName,device)
                        self.debug("Checking Voltage for %s" % id)
                        obj = self.WG.DATASTORE.get(id)
                        if 'ignorecheck' in obj.config:
                            continue
                        try:
                            ret = self.cKNX.EIB_MC_Connect(physaddr)
                            if ret == -1:
                                self.cKNX.EIBReset()
                                continue
                            ## read voltage
                            ret = self.cKNX.EIB_MC_ReadADC(1,1,ebuf)
                            try:
                                if ret > -1:
                                    value = ebuf.data * .15
                                else:
                                    value = -1
                                self.WG.DATASTORE.update(id,value)
                            except:
                                pass
                            #self.KNX.EIBReset()
                            self.cKNX.EIBComplete()
                        finally:
                            pass
                        ## wait 1000ms between checks
                        self.idle(1)
                else:
                    self.idle(60)
        finally:
            #self._checkThread = None
            self.cKNX.EIBClose()


    def statistics(self):
        stats = self.KNX.getStatistic()
        stime = time.time() - stats['time']
        for s in ["","bytes"]:
            id = "%s:STATS-Read%sPerSecond" % (self.instanceName,s)
            readPerSec = float(stats['read%s' % s]) / stime
            self.WG.DATASTORE.update(id,readPerSec)

            id = "%s:STATS-Write%sPerSecond" % (self.instanceName,s)
            writePerSec = float(stats['write%s' % s]) / stime
            self.WG.DATASTORE.update(id,writePerSec)
            
            stats = self.cKNX.getStatistic()
            stime = time.time() - stats['time']
            
            id = "%s:STATS-checkRead%sPerSecond" % (self.instanceName,s)
            creadPerSec = float(stats['read%s' % s]) / stime
            self.WG.DATASTORE.update(id,creadPerSec)
            
            id = "%s:STATS-checkWrite%sPerSecond" % (self.instanceName,s)
            cwritePerSec = float(stats['write%s' % s]) / stime
            self.WG.DATASTORE.update(id,cwritePerSec)
            
            id = "%s:STATS-totalRead%sPerSecond" % (self.instanceName,s)
            self.WG.DATASTORE.update(id,readPerSec + creadPerSec)
            
            id = "%s:STATS-totalWrite%sPerSecond" % (self.instanceName,s)
            self.WG.DATASTORE.update(id,writePerSec + cwritePerSec)
        
        try:
            self.eibmutex.acquire()
            waittime = self.QueueWaitTime / stime
            self.debug("QueueWait: %r in %r sec" % (self.QueueWaitTime , stime))
            self.QueueWaitTime = 0.0
        finally:
            self.eibmutex.release()
        
        #print "THREADS %r" % threading.enumerate()
        id = "%s:STATS-QueueWaitTime" % (self.instanceName)
        self.WG.DATASTORE.update(id,waittime)


    def readconfig(self):
        getPhysical = re.compile(":PHY_((?:1[0-5]|[0-9])\x2E(?:1[0-5]|[0-9])\x2E(?:[0-9]{1,3}))")
        instLength = len(self.instanceName)
        for obj in self.WG.DATASTORE.namespaceRead(self.instanceName):
            physaddr = getPhysical.findall(obj.id.encode('iso8859-15'))
            if physaddr:
                try:
                    self.DeviceListLock.acquire()
                    self.DeviceList[self.str2addr(physaddr[0])] = physaddr[0]
                finally:
                    self.DeviceListLock.release()
            elif 'scan' in obj.config:
                ## read all objects marked for scan
                self.send(0,obj.id.encode('iso8859-15'),flag=KNXREADFLAG)

        


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
        item += time.time(),
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


class countEIBConnection(EIBConnection.EIBConnection):
    def __init__(self):
        self.statistic_mutex = threading.RLock()
        self.statistics = {}
        self.getStatistic()
        EIBConnection.EIBConnection.__init__(self)

    def getStatistic(self):
        try:
            self.statistic_mutex.acquire()
            return self.statistics.copy()
        finally:
            self.statistics = {'read' : 0, 'readbytes' : 0, 'write' : 0, 'writebytes' : 0, 'time' : time.time() }
            self.statistic_mutex.release()
    
    def _EIBConnection__EIB_CheckRequest(self, block):
        ret = EIBConnection.EIBConnection._EIBConnection__EIB_CheckRequest(self,block)
        try:
            self.statistic_mutex.acquire()
            self.statistics['read'] += 1
            self.statistics['readbytes'] += self.readlen
        finally:
            self.statistic_mutex.release()
        return ret

    def _EIBConnection__EIB_SendRequest(self, data):
        ret = EIBConnection.EIBConnection._EIBConnection__EIB_SendRequest(self, data)
        try:
            self.statistic_mutex.acquire()
            self.statistics['write'] += 1
            self.statistics['writebytes'] += len([ (len(data)>>8)&0xff, (len(data))&0xff ] + data)
        finally:
            self.statistic_mutex.release()
        return ret
    
