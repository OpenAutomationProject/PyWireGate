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

import DPT_Types
import time

class busmonitor:
    def __init__(self, WireGateInstance):
        self.WG = WireGateInstance
        self.nicehex=lambda x: " ".join(map(lambda y:"%.2x" % y,x))
        self.tobinstr=lambda n,b=8: "".join([str((n >> y) & 1) for y in range(b-1, -1, -1)])
        self.dpt = DPT_Types.dpt_type()

        ## FIXME: Not fully implemented
        self.apcicodes = {
            0:'A_GroupValue_Read', 
            64:'A_GroupValue_Response',
            128:'A_GroupValue_Write',
            192:'A_PhysicalAddress_Write',
            256:'A_PhysicalAddress_Read',
            320:'A_PhysicalAddress_Response',
            4:'A_ADC_Read',
            5:'A_ADC_Response',
            6:'A_Memory_Read',
            7:'A_Memory_Response',
            8:'A_Memory_Write',
            9:'A_UserMemory',
            10:'A_DeviceDescriptor_Read',
            11:'A_DeviceDescriptor_Response',
            12:'A_Restart',
            13:'A_OTHER'
        }
        ## FIXME: Not fully implemented
        self.tpducodes = {
            0:'T_DATA_XXX_REQ',
            16:'T_DATA_CONNECTED_REQ',
            2:'T_DISCONNECT_REQ',
            3:'T_ACK'
        }
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
        ## Accept List Hex or Binary Data
        if type(buf)==str:
            tmp = buf
            buf = []
            try:
                ##Hex or Binary
                if ord(tmp[0])>122:
                    ##Binary
                    for char in tmp:
                        buf.append(ord(char))
                else:
                    ##Hex
                    for hex in range(0,len(tmp),2):
                        buf.append(int(tmp[hex:hex+2],16))
            except:
                self.errormsg(tmp)
                
        msg = {'raw':buf,'value':''}
        try:
            msg['ctrl1'] = self._decodeCtrlField1(buf[0])
            msg['ctrl2'] = self._decodeCtrlField2(buf[1])
            msg['srcaddr'] = self._decodePhysicalAddr(buf[1:3])
            msg['AddressType'], msg['nctrl'], msg['datalen'] = self._decodeNPDU(buf[5])
            msg['apdu'], msg['data'] = self._decodeAPDU(buf[6:-1],msg['AddressType'],msg['datalen'])
            
            if msg['ctrl2']['DestAddrType'] == 0 and msg['apdu']['tpdu'] == "T_DATA_XXX_REQ":
                msg['dstaddr'] = self._decodeGrpAddr(buf[3:5])
                id = "KNX:%s" % msg['dstaddr']
                
                ## search Datastoreobject
                dsobj = self.WG.DATASTORE.get(id)
                ## Decode the DPT Value
                msg['value'] = self.dpt.decode( msg['data'],dsobj=dsobj)
                ## update Object in Datastore
                self.WG.DATASTORE.update(id,msg['value'])
                #print "%s (%s): \x22%r\x22" % (dsobj.name, msg['dstaddr'], msg['value'])
            else:
                print "NONGROUP"
                self.errormsg(msg)
                ## non Group Communication
                msg['dstaddr'] = self._decodePhysicalAddr(buf[3:5])
        except:
            self.errormsg(msg)

        self.debug(msg)
        
        return msg


    def errormsg(self,msg=''):
        f=open("/tmp/WGerror","a+")
        __import__('traceback').print_exc(file=f)
        f.write(time.asctime())
        f.write("MSG:"+repr(msg))
        f.close()

        
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
        tpdu,sequence = self._decodeTransportCtrl(raw,addresstype)
        if tpdu == "T_DATA_XXX_REQ":
            if datalength == 1:
                ## 6bit only
                self.debug("DEBUG:6BIT %s" % self.tobinstr(raw[1]))
                apci = (raw[1] & 0x80)
                data = [raw[1] & 0x3f]
            else:
                val = (raw[0] << 8) + raw[1]
                apci = (val & 0x3c0)
                data = raw[2:]
        else:
            self.debug("FIXME:#######################TPD: %r " % tpdu)
            data = ""
            apci = 13
              
        return {
            'tpdu':tpdu,
            'seq':sequence,
            'apci':self._decodeAPCI(apci) }, data

    def _decodeTransportCtrl(self,raw,adresstype):
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
        tcf = raw[0] >> 5
        ## FIXME: Not fully implemented 
        if tcf &0x2 and len(raw) >1:
            tcf = (raw[1] &0x3) <<8 + tcf
        sequence = 0
        
        try:
            tpdu = self.tpducodes[tcf]
        except KeyError:
            tpdu = "T_NOTIMPLEMENTED_ERROR"
            
        return tpdu,sequence
        
        
    def _decodeAPCI(self,apci):
        ## APCI
        try:
            apci = self.apcicodes[apci]
        except KeyError:
            pass
        return apci
        
    def debug(self,msg):
        #print "DEBUG: BUSMON: "+ repr(msg) 
        pass


if __name__ == "__main__":
    busmon = busmonitor(False)
    #busmon.decode([176, 17, 253, 17, 104, 80, 222, 84])
    #busmon.decode("b01104116e5080f5")
    #busmon.decode("".join([chr(x) for x in [176, 17, 4, 17, 110, 80, 128, 245]]))
    print busmon.decode([176,176, 17, 4, 17, 110, 80, 128, 245])
    print busmon.decode([ 188, 17, 43, 32, 131, 225, 0, 128, 187, 188])