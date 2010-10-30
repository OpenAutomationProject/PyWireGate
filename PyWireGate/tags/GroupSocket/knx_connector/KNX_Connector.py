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


class knx_connector(Connector):
    connector_info = {'name':'KNX Connector','version':'0.1','logname':'knx_connector'}
    def __init__(self,WireGateInstance):
        self.WG = WireGateInstance

        self.KNX = EIBConnection.EIBConnection()
        self.KNXBuffer = EIBConnection.EIBBuffer()
        self.busmon = BusMonitor.busmonitor(WireGateInstance)
        self.config = {}
        try:
            self.config = self.WG.config['KNX']
            type(self.config['url'])
        except KeyError:
            self.config['url']='local:/tmp/eib'
        self.start()

    def run(self):
        while self.isrunning:
            ## Create Socket
            try:
                self.KNX.EIBSocketURL(self.config['url'])
                self.KNX.EIB_Cache_Enable()
                self.KNX.EIBOpenVBusmonitor_async()
                ## wait a second for the Busmon to activate
                self.idle(0.5)
                self._run()
                try:
                    self.KNX.EIBClose()
                except:
                    self.WG.errorlog()
            except:
                self.WG.errorlog()
            self.debug("Socket Closed waiting 5 sec")
            self.idle(5)

    def _run(self):
        while self.isrunning:
            ## Check if we are alive and responde until 10 secs
            self.WG.watchdog("knx_connector",10)
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
                        break
                    except:
                        pass
                if not iscomplete:
                    ## Eibd closed connection
                    break
                if iscomplete==1:
                    ## capture BusMon packets
                    self.KNX.EIBGetBusmonitorPacket(self.KNXBuffer)
                    ## Only decode packets larger than 7 octets
                    if len(self.KNXBuffer.buffer) > 7 :
                        self.busmon.decode(self.KNXBuffer.buffer)
                
