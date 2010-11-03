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


### Da die EIBConnection Lib den string nicht hexadezimal zurueckgibt,
### sondern als LIST mit den dezimalen Werten ist das decode hier ein bischen angepasst

class dpt_type:
    def __init__(self,WireGateInstance):
        self.WG = WireGateInstance
        self.DECODER = {
            1:self.decodeDPT1,       # EIS 1/7       / 1 bit  0=Aus/1=Ein
            2:self.decodeDPT2,       # EIS 8         / 2 bit  0,1=Frei/2=Prio_Aus/3=Prio_Ein
            3:self.decodeDPT3,       # EIS 2         / 4 bit
            4:self.decodeDPT4,       # EIS 13        / 1 byte 1 Zeichen
            5:self.decodeDPT5,       # EIS 6/14.001  / 1 byte 0...255 5.001 
            5.001:self.decodeDPT501, # PDT_SCALING
            5.005:self.decodeDPT5,   # DPT_DecimalFactor
            5.010:self.decodeDPT5,   # DPT_Value_1_Ucount
            6:self.decodeDPT6,       # EIS 14.000    / 1 byte -128 ... 127
            7:self.decodeDPT7,       # EIS 10.000    / 2 byte 0....65535
            8:self.decodeDPT8,       # EIS 10.001    / 2 byte -32768 .... 32767
            9:self.decodeDPT9,       # EIS 5         / 2 byte Float
            10:self.decodeDPT10,     # EIS 3         / 3 byte WoTag/Stunde/Minute/Sekunde
            11:self.decodeDPT11,     # EIS 4         / 3 byte Tag/Monat/Jahr
            12:self.decodeDPT12,     # EIS 11.000    / 4 byte unsigned [0...4.294.967.295]
            13:self.decodeDPT13,     # EIS 11.001    / 4 byte signed -2.147.483.648 ... 2.147.483.647]
            14:self.decodeDPT14,     # EIS 9         / 4 byte float 
            16:self.decodeDPT16      # EIS 15        / 14 byte Text
        }
        
        
    def decode(self,raw,dptid=0,dsobj=False):
        dpt=-1
        if dptid > 0:
            dpt = dptid
        elif dsobj:
            if "dptid" in dsobj.config:
                dpt = dsobj.config['dptid']
        else:
            return False
        if dpt == -1:
            dpt = self.guessType(raw)
            if dsobj:
                dsobj.dptid = dpt
            self.debug("Guessed: %f" % dpt)
        if dpt == 0:
            return raw
        return self._decode(raw,dpt)

    def _decode(self,raw,dpt):
        try:
            try:
                return self.DECODER[dpt](raw)
            except KeyError:
                try:
                    return self.DECODER[int(dpt)](raw)
                except KeyError:
                    return raw
        except:
            self.errormsg()
            return raw

    def errormsg(self,msg=False):
        self.WG.errormsg(msg)

    def debug(self,msg):
        self.log(msg,'debug')
        
    def log(self,msg,severity='info',instance=False):
        if not instance:
            instance = "dpt-types"
        self.WG.log(msg,severity,instance)


    def toBigInt(self,raw):
        c=0
        res = 0
        rawlen= len(raw)-1
        for octet in range(rawlen+1):
            res += raw[rawlen -octet] << (c * 8)
            c += 1
        return res

    def decodeDPT1(self,raw):
        return int(raw[0]) & 0x1
    
    def decodeDPT2(self,raw):
        ## 2 Bit Control
        ## RRRRRRCS
        ## R Reserved
        ## C Control (0=Not enforced/1=enforced)
        ## S Switch 0=off/1=on
        return int(raw[0]) & 0x3

    def decodeDPT3(self,raw):
        ## 4 bit Dim (DPT 3.007)
        ## RRRRDSSS
        ## R Reserved
        ## D Direction 0=Decrease/1=Increase
        ## S Step (1-7) 0=Break
        ## FIXME: dont know what a Datastore should accept here
        return int(raw[0]) & 0xf
        
    def decodeDPT4(self,raw):
        ## 1 Byte Character
        return chr(raw[0] & 0xff)
    
    def decodeDPT5(self,raw):
        ## 1 Byte unsigned
        return (int(raw[0] & 0xff))

    def decodeDPT501(self,raw):
        ## 1 Byte unsigned percent
        self.debug("DPT5.001 Scaling: value: %d" % raw[0])
        return int(raw[0] & 0xff) * 100 / 255
    
    def decodeDPT6(self,raw):
        ## 1 Byte signed
        val = int(raw[0] & 0xff)
        return  (val > 127 and val - 256 or val)
        
    def decodeDPT7(self,raw):
        ## 2 byte unsigned
        return int(self.toBigInt(raw) & 0xffff)
        
    def decodeDPT8(self,raw):
        ## 2 Byte signed
        val = int(self.toBigInt(raw) & 0xffff)
        return  (val > 32767 and val - 32768 or val)

    def decodeDPT9(self,raw):
        ## 2 Byte Float
        ## SEEEEMMM MMMMMMMM
        ## S Sign (0/1)
        ## E Exponent (0..15)
        ## M Mantisse (-2048 ... 2047)
        ## For all Datapoint Types 9.xxx, the encoded value 7FFFh shall always be used to denote invalid data.
        val = self.toBigInt(raw)
        sign = (val & 0x8000) >> 15
        exp = (val & 0x7800) >> 11
        mant = val & 0x07ff
        if sign <> 0:
            mant = -(~(mant - 1) & 0x7ff) 
        self.debug("DPT9: value: %d sign: %d exp: %d mant: %f" % (val, sign,exp,mant))
        return (1 << exp) * 0.01 * mant


    def decodeDPT10(self,raw):
        ## 3 Byte Time
        ## DDDHHHHH RRMMMMMM RRSSSSSS
        ## R Reserved
        ## D Weekday
        ## H Hour
        ## M Minutes
        ## S Seconds
        weekday = (raw[0] & 0xe0) >> 5
        weekdays = ["","Mo","Di","Mi","Do","Fr","Sa","So"]
        hour = raw[0] & 0x1f
        min = raw[1] & 0x3f
        sec = raw[2] & 0x3f
        ## Fixme: eigentlich sollte Zeit als Unix Timestamp gespeichert werden, was macht man mit dem Wochentag
        ## machs erstmal so wie makki
        return "%s %d:%d:%d" % (weekdays[weekday], hour,min,sec)
    
    def decodeDPT11(self,raw):
        ## 3 byte Date
        ## RRRDDDDD RRRRMMMM RYYYYYYY
        ## R Reserved
        ## D Day
        ## M Month
        ## Y Year
        day = raw[0] & 0x1f
        mon = raw[1] & 0xf
        year = raw[2] & 0x7f
        if year<90:
            year += 2000
        else:
            year += 1900
        return "%02d.%02d.%04d" % (day,mon,year)

    def decodeDPT12(self,raw):
        return int(self.toBigInt(raw)) % 0xffffffff
    def decodeDPT13(self,raw):
        val = int(self.toBigInt(raw)) % 0xffffffff
        return (val > 2147483647 and val - 2147483648 or val)

    def decodeDPT14(self,raw):
        ## 4 Byte Float
        ## SEEEEEEE EFFFFFFF FFFFFFFF FFFFFFFF
        ## S (Sign) = {0,1}
        ## Exponent = [0 ... 255]
        ## Fraction = [0 .. 8 388 607]
        val = self.toBigInt(raw)
        sign = (val & 0x80000000) >> 31
        exp = (val & 0x7f8000) >> 23
        mant = val & 0x7fffff
        if sign <> 0:
            mant = -(~(mant - 1) & 0x7fffff) 
        self.debug("DPT14: value: %d sign: %d exp: %d mant: %f" % (val, sign,exp,mant))
        return (1 << exp) * 0.01 * mant

    def decodeDPT16(self,raw):
        res = ""
        for char in raw:
            ## stop on terminating \x00
            if char == 0:
                break
            res += chr(char)
        return res

    def validTypes(self,datalen):
        ##TODO:
        ret = []
        return ret

    def guessType(self,raw):
        if len(raw) == 1:
            ## there cant be anything wrong 0..255
            return 5
        elif len(raw) == 2:
            ## should also be clear unsigned 2byte, but as DPT9 is more common default to that
            return 9
        elif len(raw) == 3:
            ## length 3 can only be time or date
            if ((raw[0] & 0xe0) >> 5) >0:
                ## first 3 bits are only valid in time for weekday
                return 10
            else:
                ## else date
                return 11
        elif len(raw) == 4:
            ## 4yte usigned
            return 12
        elif len(raw) == 14:
            ## 14byte String
            return 16
        return 0



if __name__ == "__main__":
    dpttypes = dpt_type()
    print dpttypes.decode([24,88],dptid=9)
    print dpttypes.decode([1],dptid=1)
    print dpttypes.decode([35,76,58],dptid=16)
    