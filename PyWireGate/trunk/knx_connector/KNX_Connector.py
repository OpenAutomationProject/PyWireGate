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
import EIBConnection
import select
import BusMonitor
import DPT_Types


class knx_connector(Connector):
    connector_info = {'name':'KNX Connector','version':'0.1','logname':'knx_connector'}
    def __init__(self,WireGateInstance):
        self.WG = WireGateInstance
        self.busmon = BusMonitor.busmonitor(WireGateInstance)
        self.DPT = DPT_Types.dpt_type()
        self.config = {}
        try:
            self.config = self.WG.config['KNX']
            type(self.config['url'])
        except KeyError:
            self.config['url']='local:/tmp/eib'
        
        self.nicehex=lambda x: " ".join(map(lambda y:"%.2x" % y,x))
        
        
        self.start()


    def decodeDPT(self,msg,obj=False):
        if obj:
            dpt=int(obj.dptid)
        if dpt==1:
            ## 1Byte
            return int(msg['data'][0])
        elif dpt==2:
            ## DPT5
            return int(msg['data'][0]) * 100 /255
        elif dpt==9:
            ## 2byte
            #print self.tobinstr(data[1])+" "+self.tobinstr(data[2])
            sign = msg['data'][0] & 0x80
            exp = (msg['data'][0] & 0x78) >> 3
            mant = (msg['data'][0] & 0x7) << 8 | msg['data'][1]
            if sign <> 0:
                mant = -(~(mant - 1) & 0x7ff) 
            return (1 << exp) * 0.01 * mant
        
        elif dpt==10:
            self.debug("DATE/TIME")
        elif dpt==11:
            self.debug("DATE/TIME")
        self.debug("unknownDPT: "+repr(msg))
        return msg['data']


    def decodeBusmonitor(self,buf):
        msg = {'data':[]}
        msg['hex'] = self.nicehex(buf)
        msg['src'] = ".".join(map(lambda x: str(x),self.getsrcaddr(buf)))
        msg['dst'] = "/".join(map(lambda x: str(x),self.getgrpaddr(buf)))
        frametpy,reserved,msg['repeated'],broadcast,prio,ack,confirm = self.getctrl1(buf)
        destaddr, msg['rcount'],msg['datalen'] = self.getctrl2(buf)
        msg['prio'] = self.prioclasses[prio]
        data=buf[6:]
        try:
            msg['tpdu_type'] = self.tpducodes[(data[0] & 0xC0)>>6]
        except IndexError:
            self.log("unknonw TPDU: "+str((data[0] & 0xC0)>>6)+ " - "+msg['hex'],'warning')
        if msg['tpdu_type'] == "T_DATA_XXX_REQ":
            if msg['datalen'] == 1:
                ## 6bit only
                msg['data'].append(data[1] & 0x3F)
            else:
                for i in range(2,msg['datalen']+1):
                    msg['data'].append(data[i])
                
        msg['sequence'] = (data[0] & 0x3C)>>2;
        try:
            msg['apci'] = self.apcicodes[((data[0] & 0x03)<<2) | ((data[1] & 0xC0)>>6)];
        except IndexError:
            self.log("unknonw ACPI: "+str(((data[0] & 0x03)<<2) | ((data[1] & 0xC0)>>6))+ " - "+msg['hex'],'warning')
        id = "KNX:"+msg['dst']
        try:
            #msg['value'] = self.decodeDPT(msg,self.WG.DATASTORE.get(id))
            #msg['value'] = self.DPT.decode(msg['data'])#,self.WG.DATASTORE.get(id))
            msg['value'] = self.DPT.decode(msg['data'],DSobj=self.WG.DATASTORE.get(id))
            self.WG.DATASTORE.update(id,msg['value'])
        except:
            self.WG.errorlog(msg)
        self.debug(msg)
    def run(self):
        while self.isrunning:
            self.KNX = EIBConnection.EIBConnection()
            self.KNX.EIBSocketURL(self.config['url'])
            self.KNX.EIB_Cache_Enable()
            self.KNX.EIBOpenVBusmonitor_async()
            self.KNXBuffer = EIBConnection.EIBBuffer()
            self._run()
            try:
                self.KNX.EIBClose()
            except:
                self.WG.errorlog()
            self.idle(15)

    def _run(self):
        while self.isrunning:
            self.WG.watchdog("knx_connector",5)
            try:
                vbusmonin, vbusmonout, vbusmonerr = select.select([self.KNX.EIB_Poll_FD()],[],[],1)
            except:
                self.WG.errorlog()
                continue
            if self.KNX.EIB_Poll_FD() in vbusmonin:
                try:
                    iscomplete = self.KNX.EIB_Poll_Complete()
                except:
                    self.WG.errorlog()
                    ###FIXME: Fehler wird eigentlich in der EIBConnectio.py erzeugt.
                    iscomplete=0
                if iscomplete==1:
                    self.KNX.EIBGetBusmonitorPacket(self.KNXBuffer)
                    if len(self.KNXBuffer.buffer)>7:
                        ###FIXME: Warum kommt initial ein leeres Packet an?
                        #self.decodeBusmonitor(self.KNXBuffer.buffer)
                        self.busmon.decode(self.KNXBuffer.buffer)
                    
