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

import sys
sys.path.append( "/usr/local/WireGate" )
import DPT_Types

class busmonitor:
    def __init__(self, WireGateInstance):
        self.WG = WireGateInstance
        self.nicehex=lambda x: " ".join(map(lambda y:"%.2x" % y,x))
        self.tobinstr=lambda n,b=8: "".join([str((n >> y) & 1) for y in range(b-1, -1, -1)])
        self.dpt = DPT_Types.dpt_type()

        ## FIXME: Not fully implemented
        self.apcicodes = [
            'A_GroupValue_Read', 
            'A_GroupValue_Response',
            'A_GroupValue_Write',
            'A_PhysicalAddress_Write',
            'A_PhysicalAddress_Read',
            'A_PhysicalAddress_Response',
            'A_ADC_Read',
            'A_ADC_Response',
            'A_Memory_Read',
            'A_Memory_Response',
            'A_Memory_Write',
            'A_UserMemory',
            'A_DeviceDescriptor_Read',
            'A_DeviceDescriptor_Response',
            'A_Restart',
            'A_OTHER'
        ]
        ## FIXME: Not fully implemented
        self.tpducodes = [
            'T_DATA_XXX_REQ',
            'T_DATA_CONNECTED_REQ',
            'T_DISCONNECT_REQ',
            'T_ACK'
        ]
        self.prioclasses = [
            'system',
            'alarm',
            'high',
            'low'
        ]
        ##



    def decode(self,buf):
        ######################################################################################
        ## 11111111 22222222 SSSSSSSS SSSSSSSS DDDDDDDD DDDDDDDD LLLLLLLL AAAAAAAA AAAAAAAA
        ## 1 Control Field 1
        ## 2 Control Field 2
        ## S Source Address
        ## D Destination Address
        ## L Data Len
        ## A APDU
        ######################################################################################
        msg = {'raw':buf,'value':''}
        try:
            msg['ctrl1'] = self._decodeCtrlField1(buf[0])
            msg['ctrl2'] = self._decodeCtrlField2(buf[1])
            msg['srcaddr'] = self._decodePhysicalAddr(buf[1:3])
            msg['AddressType'], msg['nctrl'], msg['datalen'] = self._decodeNPDU(buf[5])
            msg['apdu'], msg['data'] = self._decodeAPDU(buf[6:-1],msg['AddressType'],msg['datalen'])

            if msg['ctrl2']['DestAddrType'] == 0:
                msg['dstaddr'] = self._decodeGrpAddr(buf[3:5])
                id = "KNX:%s" % msg['dstaddr']
                
                ## search Datastoreobject
                dsobj = self.WG.DATASTORE.get(id)
                
                ## Decode the DPT Value
                msg['value'] = self.dpt.decode( msg['data'],dsobj=dsobj)
                
                ## update Object in Datastore
                self.WG.DATASTORE.update(id,msg['value'])
                if not dsobj:
                    name = "unknown"
                else:
                    name = dsobj.name

                print "%s (%s): %r" % (name, msg['dstaddr'], msg['value'])
            else:
                ## non Group Communication
                msg['dstaddr'] = self._decodePhysicalAddr(buf[3:5])
        except:
            self.errormsg(msg)

        self.debug(msg)
        
        return msg


    def errormsg(self,msg=''):
        f=open("/tmp/WGerror","a+")
        __import__('traceback').print_exc(file=__import__('sys').stdout)
        __import__('traceback').print_exc(file=f)
        f.write("MSG:"+repr(msg))
        f.close()
        print repr(msg)

        
    def _decodeCtrlField1(self,raw):
        ############################
        ## Control Field 1
        ## TRrBPPAC
        ## T FrameType
        ## R Reserved 
        ## r Repeat
        ## B Broadcast
        ## P Priority
        ## A ACK req
        ## C Confirm
        return {
            'FrameType':(raw >>7) & 0x1,
            'Repeat':(raw >> 5) & 0x1,
            'BroadCast':(raw >> 4) & 0x1,
            'Prio':self.prioclasses[(raw >>2) & 0x3],
            'AckReq':(raw >>1) & 0x1,
            'Confirm':raw & 0x1
        }


    def _decodeCtrlField2(self,raw):
        ############################
        ## Control Field 2
        ## DHHHEEEE
        ## D Destination addr. Type 0=individual/1=group
        ## H Hop Count
        ## E Extended Frame Format 0=standard 
        return {
            'DestAddrType':(raw >>7) & 0x1,
            'HopCount': (raw >>4) & 0x7,
            'ExtFormat':raw & 0x7
        }
        

        
    def _decodePhysicalAddr(self,raw):
        ############################
        ## Source Address (indiduell Address)
        ## AAAALLLLDDDD
        ## A Area
        ## L Line
        ## D Device
        area = raw[0] >> 4
        line = raw[0] & 0xf
        device = raw[1]

        return "%d.%d.%d" % (area,line,device)
        
    def _decodeGrpAddr(self,raw):
        ############################
        ## Destination Address (group Address)
        ## RHHHHMMM SSSSSSSS
        ## R Reserved
        ## H Maingroup
        ## M Middlegroup
        ## S Subgroup
        main = (raw[0] >> 3) & 0xf
        middle = raw[0] & 0x7
        sub = raw[1]

        return "%d/%d/%d" % (main,middle,sub)
        
    def _decodeNPDU(self,raw):
        ############################
        ## Data length
        ## ANNNLLLL
        ## A Addresstype
        ## N NectworkControlField
        ## L Data Length
        AddressType = (raw >> 7) & 0x1
        NetworkCtrl = (raw >> 4) & 0x7
        DataLength = raw & 0xf
        self.debug("NPDU: %s " % self.tobinstr(raw))
        
        return AddressType,NetworkCtrl,DataLength
  
    def _decodeAPDU(self,raw, addresstype, datalength):
        ############################
        ## TPDU Bytes 7 and 8
        ## TTTTTTAA AAMMMMMM
        ## T Transport Control Field
        ## A APCI
        ## M APCI/data
        val = (raw[0] << 8) + raw[1]
        tcf = val >> 10
        tpdu,sequence = self._decodeTransportCtrl(tcf,addresstype)
        apci = (val & 0x3c0)
        if tpdu =="T_DATA_XXX_REQ" and datalength==1:
            ## 6bit only
            self.debug("DEBUG:6BIT")
            apci = apci >> 6
            data = [val & 0x3f]
        else:
            data = raw[2:]
        return {
            'tpdu':tpdu,
            'seq':sequence,
            'apci':apci }, data
        
    def _decodeTransportCtrl(self,tcf,adresstype):
        ## Transport Control Field
        ## 1 0 0 0 0 0 0     T_Data_Broadcast-PDU (destination_address = 0)
        ## 1 0 0 0 0 0 0     T_Data_Group-PDU (destination_address <> 0)
        ## 1 0 0 0 0 0 1     T_Data_Tag_Group-PDU
        ## 0 0 0 0 0 0 0     T_Data_Individual-PDU
        ## 0 0 1 S S S S     T_Data_Connected-PDU
        ## 0 1 0 0 0 0 0 0 0 T_Connect-PDU
        ## 0 1 0 0 0 0 0 0 1 T_Disconnect-PDU
        ## 0 1 1 S S S S 1 0 T_ACK-PDU
        ## 0 1 1 S S S S 1 1 T_NAK-PDU
        ## FIXME: Incomplete, only Data/ControlFlag and Numbered used
        sequence = 0
        try:
            tpdu = self.tpducodes[(tcf & 0xc0) >> 6]
        except KeyError:
            tpdu = "T_NOTIMPLEMENTED_ERROR"
            
        return tpdu,sequence
        
        
    def _decodeAPCI(self,apci):
        ## APCI
        return apci
        
    def debug(self,msg):
        #print "DEBUG: BUSMON: "+ repr(msg) 
        pass


if __name__ == "__main__":
    busmon = busmonitor(False)
    #busmon.decode([176, 17, 253, 17, 104, 80, 222, 84])
    busmon.decode([176, 17, 4, 17, 110, 80, 128, 245])