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

import struct

class dpt_type:
    def __init__(self,parent):
        self._parent = parent
        if parent:
            self.WG = parent.WG
        else:
            self.WG = False
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
        self.ENCODER = {
            1:self.encodeDPT1,       # EIS 1/7       / 1 bit  0=Aus/1=Ein
            2:self.encodeDPT2,       # EIS 8         / 2 bit  0,1=Frei/2=Prio_Aus/3=Prio_Ein
            3:self.encodeDPT3,       # EIS 2         / 4 bit
            4:self.encodeDPT4,       # EIS 13        / 1 byte 1 Zeichen
            5:self.encodeDPT5,       # EIS 6/14.001  / 1 byte 0...255 5.001 
            5.001:self.encodeDPT501, # PDT_SCALING
            5.005:self.encodeDPT5,   # DPT_DecimalFactor
            5.010:self.encodeDPT5,   # DPT_Value_1_Ucount
            6:self.encodeDPT6,       # EIS 14.000    / 1 byte -128 ... 127
            7:self.encodeDPT7,       # EIS 10.000    / 2 byte 0....65535
            8:self.encodeDPT8,       # EIS 10.001    / 2 byte -32768 .... 32767
            9:self.encodeDPT9,       # EIS 5         / 2 byte Float
            10:self.encodeDPT10,     # EIS 3         / 3 byte WoTag/Stunde/Minute/Sekunde
            11:self.encodeDPT11,     # EIS 4         / 3 byte Tag/Monat/Jahr
            12:self.encodeDPT12,     # EIS 11.000    / 4 byte unsigned [0...4.294.967.295]
            13:self.encodeDPT13,     # EIS 11.001    / 4 byte signed -2.147.483.648 ... 2.147.483.647]
            14:self.encodeDPT14,     # EIS 9         / 4 byte float 
            16:self.encodeDPT16      # EIS 15        / 14 byte Text
        }
        
        
    def decode(self,raw,dptid=0,dsobj=False):
        dpt=-1
        if dptid > 0:
            dpt = dptid
        elif dsobj:
            if "dptid" in dsobj.config:
                dpt = dsobj.config['dptid']
        #else:
        #    return False
        if dpt == -1:
            dpt = self.guessType(raw)
            if dsobj:
                dsobj.dptid = dpt
            self.debug("Guessed: %f" % dpt)
        if dpt == 0:
            return raw
        return self._decode(raw,dpt)

    def encode(self,msg,dptid=0,dsobj=False):
        dpt=-1
        if dptid > 0:
            dpt = dptid
        elif dsobj:
            if "dptid" in dsobj.config:
                dpt = dsobj.config['dptid']
        else:
            return False
        return self._encode(msg,dpt)
    

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
    
    def _encode(self,msg,dpt):
        try:
            try:
                return self.ENCODER[dpt](msg)
            except KeyError:
                try:
                    return self.ENCODER[int(dpt)](msg)
                except KeyError:
                    return msg
        except:
            self.errormsg()
            return msg

    def errormsg(self,msg=False):
        if self.WG:
            self.WG.errorlog(msg)

    def debug(self,msg):
        self.log(msg,'debug')
        
    def log(self,msg,severity='info',instance=False):
        if not instance:
            instance = "dpt-types"
        if self._parent:
            self._parent.log(msg,severity,instance)

    def toByteArray(self,val,length):
        ## Set ByteArray
        ret = [0 for b in range(length)]
        for val in struct.pack("L",val):
            ## Fill up from end
            length -= 1
            ## if struct larger then len return
            if length < 0:
                return ret
            ## write from end to start
            ret[length] = ord(val)
        return ret

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

    def encodeDPT1(self,val):
        return int(val) & 0x1

    def decodeDPT2(self,raw):
        ## 2 Bit Control
        ## RRRRRRCS
        ## R Reserved
        ## C Control (0=Not enforced/1=enforced)
        ## S Switch 0=off/1=on
        return int(raw[0]) & 0x3

    def encodeDPT2(self,val):
        return int(val) & 0x3

    def decodeDPT3(self,raw):
        ## 4 bit Dim (DPT 3.007)
        ## RRRRDSSS
        ## R Reserved
        ## D Direction 0=Decrease/1=Increase
        ## S Step (1-7) 0=Break
        ## FIXME: dont know what a Datastore should accept here
        return int(raw[0]) & 0xf

    def encodeDPT3(self,val):
        return int(val) & 0xf
        
    def decodeDPT4(self,raw):
        ## 1 Byte Character 
        ## ISO 2 Unicode
        return chr(raw[0] & 0xff).decode('iso-8859-15')
    
    def encodeDPT4(self,val):
        if type(val) == unicode:
            ## convert to str
            val = val.encode('iso-8859-15')
        if type(val) <> str:
            val = "%r" % val
        return ord(val[0]) & 0xff
    
    def decodeDPT5(self,raw):
        ## 1 Byte unsigned
        return int(raw[0]) & 0xff

    def encodeDPT5(self,val):
        return int(val) & 0xff

    def decodeDPT501(self,raw):
        ## 1 Byte unsigned percent
        self.debug("DPT5.001 Scaling: value: %d" % raw[0])
        return (int(raw[0]) & 0xff) * 100 / 255

    def encodeDPT501(self,val):
        return (int(val) * 255 / 100 ) & 0xff
    
    def decodeDPT6(self,raw):
        ## 1 Byte signed
        val = int(raw[0] & 0xff)
        return  (val > 127 and val - 256 or val)

    def encodeDPT6(self,val):
        if val > 127:
            ## Max
            val = 127
        return int(val) & 0xff
        
    def decodeDPT7(self,raw):
        ## 2 byte unsigned
        return int(self.toBigInt(raw) & 0xffff)

    def encodeDPT7(self,val):
        return self.toByteArray(val & 0xffff,2)
        
    def decodeDPT8(self,raw):
        ## 2 Byte signed
        val = int(self.toBigInt(raw) & 0xffff)
        return  (val > 32767 and val - 32768 or val)

    def encodeDPT8(self,val):
        if val > 32767:
            val = 32767
        return self.toByteArray(val & 0xffff,2)

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
            mant = -(~(mant - 1) & 0x07ff) 
        self.debug("DPT9: value: %d sign: %d exp: %d mant: %f" % (val, sign,exp,mant))
        return (1 << exp) * 0.01 * mant

    def encodeDPT9(self,val):
        sign = 0
        exp = 0
        if val < 0:
            sign = 0x8000
        mant = val * 100
        while mant > 0x07ff:
            mant = mant >> 1
            exp +=1
        data = sign | (exp << 11) | (int(mant) & 0x07ff)
        self.debug("DPT9: value: %d sign: %d exp: %d mant: %r" % (val, sign,exp,mant))
        ## change to 2Byte bytearray 
        return self.toByteArray(data,2)
    

    def decodeDPT10(self,raw):
        ## 3 Byte Time
        ## DDDHHHHH RRMMMMMM RRSSSSSS
        ## R Reserved
        ## D Weekday
        ## H Hour
        ## M Minutes
        ## S Seconds
        weekday = (raw[0] & 0xe0) >> 5
        
        ## Fixme: I18N
        weekdays = ["","Mo","Di","Mi","Do","Fr","Sa","So"]
        hour = raw[0] & 0x1f
        min = raw[1] & 0x3f
        sec = raw[2] & 0x3f
        ## Fixme: eigentlich sollte Zeit als Unix Timestamp gespeichert werden, was macht man mit dem Wochentag
        ## machs erstmal so wie makki
        return u"%s %d:%d:%d" % (weekdays[weekday], hour,min,sec)

    def encodeDPT10(self,val):
        ## checktype default unix timestamp
        ## except standard timestring 20:15 or 20:15:34 or Mo 20:14:55
        weekday = 0
        hour = 0
        min = 0 
        sec = 0
        if type(val) == str:
            ## check for weekday
            if val[0].isalpha():
                ## extract Weekday
                day,val = val.split(" ",1)
                ## Fixme: I18N
                day = day.lower()
                weekdays = ["","mo","di","mi","do","fr","sa","so"]
                if weekday in weekdays:
                    weekday = weekdays.index(day)

            timeval = val.split(":")
            if len(timeval) == 2:
                hour = int(timeval[0])
                min = int(timeval[1])
            if len(timeval) == 3:
                sec = int(timeval[2])
        elif type(val) in [float, int]:
            now = time.localtime(val)
            weekday = now[6]
            hour = now[3]
            min = now[4]
            sec = now[5]

        else:
            ## can't convert
            return False
        
        weekday = weekday << 5
        return [weekday | hour , min, sec]
                
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
        return u"%02d.%02d.%04d" % (day,mon,year)

    def encodeDPT11(self,val):
        if type(val) in [float, int]:
            tval = val
        else:
            tval =0
        ## make time struct accesible
        utime = [v for v in time.localtime(tval)]
        if type(val) == str:
            datestr = val.split(".")
            if len(datestr) == 2:
                # day
                utime[2] = val[0]
                # month
                utime[1] = val[1]
                ##year
                if val[2]<90:
                    utime[2] = 2000 + val[2]
                elif val[2]<100:
                    utime = 1900 + val[2]
                else:
                    utime = val[2]
                
        day = utime[2]
        mon = utime[1] 
        year = utime[2]
        if year < 2000:
            year -= 1900
        else:
            year -= 2000
        return [ day & 0x1f, mon & 0xf, year & 0x7f ]

    def decodeDPT12(self,raw):
        return int(self.toBigInt(raw)) % 0xffffffff

    def encodeDPT12(self,val):
        return self.toByteArray(val & 0xffffffff,4)

    def decodeDPT13(self,raw):
        val = int(self.toBigInt(raw)) % 0xffffffff
        return (val > 2147483647 and val - 2147483648 or val)

    def encodeDPT13(self,val):
        if val > 2147483647:
            val = 2147483647
        return self.toByteArray(val & 0xffffffff,4)

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

    def encodeDPT14(self,val):
        sign = 0
        exp = 0
        if val < 0:
            sign = 0x80000000
        mant = val * 100
        while mant > 0x7fffff:
            mant = mant >> 1
            exp +=1
        data = sign | (exp << 23) | (int(mant) & 0x07ff)
        self.debug("DPT14: value: %d sign: %d exp: %d mant: %r" % (val, sign,exp,mant))
        ## change to 4Byte bytearray 
        return self.toByteArray(data,4)

    def decodeDPT16(self,raw):
        res = ""
        for char in raw:
            ## stop on terminating \x00
            if char == 0:
                break
            res += chr(char)
        
        ## Decode ISO 2 Unicode
        return res.decode('iso-8859-15')

    def encodeDPT16(self,val):
        if type(val) == unicode:
            val = val.encode('iso-8859-15')
        ## max 14
        val = val[:14]
        data = []
        for cnt in range(14):
            if len(val) > cnt:
                char = ord(val[cnt])
            else:
                char = 0
            data.append(char)
        return data

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
    dpttypes = dpt_type(False)
    print dpttypes.decode([24,88],dptid=9)
    print dpttypes.decode([1],dptid=1)
    print dpttypes.decode([35,76,58],dptid=16)
    print dpttypes.encode("Das ist",dptid=16)