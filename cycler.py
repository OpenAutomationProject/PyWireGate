# -*- coding: iso8859-1 -*-
## -----------------------------------------------------
## Cycler
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

import threading

import time


class cycler:
    def __init__(self,WireGateInstance):
        self.WG = WireGateInstance
        
        self.isrunning = True
        ## Dummy Timer
        self.waiting = threading.Timer(0,lambda: None)
        self.waiting.setDaemon(1)
        self.mutex = threading.RLock()
        self.getTime = lambda x: x.getTime
        self.timerList = []
        self.running = {}
    
    def debug(self,msg):
        print "DEBUG Cycler: %s" % msg
    def remove(self, obj):
        if not self.isrunning:
            ## dont try to get a mutex
            return False
        try:
            self.mutex.acquire()
            if obj in self.timerList:
                try:
                    self.timerList.remove(obj)
                except:
                    pass
                self.debug("Removed %r" % obj.action)
                if len(self.timerList) == 0:
                    ## kill waiting timer
                    self.debug("Cancel GLobal wait")
                    self.waiting.cancel()
            if obj in self.running:
                try:
                    if self.running[obj].isAlive():
                        self.running[obj].cancel()
                        self.debug("Canceled %r" % obj.args)
                finally:
                    self.debug("terminated %r" % obj.args)
                    del self.running[obj]

        finally:
            self.mutex.release()

    
    def add(self,rtime,function,*args,**kwargs):
        if not self.isrunning:
            ## dont try to get a mutex
            return False
        self.debug("adding task: %r (%r / %r)" % (function,args,kwargs))
        self.addShedule(sheduleObject(self,self.WG,rtime,function,args=args,kwargs=kwargs))
    
    def cycle(self,rtime,function,*args,**kwargs):
        if not self.isrunning:
            ## dont try to get a mutex
            return False
        self.debug("adding cycliv task: %r (%r / %r)" % (function,args,kwargs))
        self.addShedule(sheduleObject(self,self.WG,rtime,function,cycle=True,args=args,kwargs=kwargs))
    
    def addShedule(self,shed):
        print "ADD _shed %r" % shed
        self.mutex.acquire()
        self.timerList.append(shed)
        ## Try to stop running timer
        try:
            self.waiting.cancel()
        except:
            pass
        self.timerList.sort(key=self.getTime)
        self.mutex.release()

        ## check if any Timer need activation
        self._check()
        
        return shed
    
    
    def _check(self):
        self.debug("Cycle")
        try:
            self.mutex.acquire()
            ## all actions that need activation in next 60seconds
            for shedobj in filter(lambda x: x.getTime() < 60, self.timerList):
                try: 
                    self.running[shedobj] = threading.Timer(shedobj.getTime(),shedobj.run)
                    self.running[shedobj].start()
                    #print "run %s" % t.name
                except:
                    print "Failed"
                    raise
                ## remove from List because its now in the past
                self.timerList.remove(shedobj)
        finally:
            if len(self.timerList) >0:
                print "Wait for later timer %r" % (self.timerList[0].getTime()-5)
                self.waiting = threading.Timer(self.timerList[0].getTime()-5 ,self._check)
                self.waiting.start()
            self.mutex.release()

            
    def shutdown(self):
        print "Try killing"
        self.isrunning = False
        try:
            ## stop all new timer
            self.mutex.acquire()
            print "Have Mutex"
            self.waiting.cancel()
            try:
                self.waiting.join(2)
            except:
                ## maybe not even running
                pass
            print "Thread canceld"
            self.timerList = []
            for obj in self.running.keys():
                print "cancel task %r" % obj.args
                try:
                    tobecanceled = self.running.pop(obj)
                    
                except:
                    pass
                tobecanceled.cancel()
                tobecanceled.is
                    tobecanceled.join(2)
                
            
        except:
            self.debug("SHUTDOWN FAILED")


class sheduleObject:
    def __init__(self,parent,WireGateInstance,rtime,function,cycle=False,args = [],kwargs={}):
        self.Parent = parent
        self.WG = WireGateInstance
        self.delay = rtime
        self.cycle = cycle
        self._set()
        self.action = function
        self.args = args
        self.kwargs = kwargs
    
    def _set(self):
        self.timer = time.time() + self.delay
    
    def run(self):
        args = self.args
        kwargs = self.kwargs
        self.action(*args,**kwargs)
        self.Parent.remove(self)
        if self.cycle:
            self._set()
            self.Parent.addShedule(self)
            

    def getTime(self):
        return self.timer - time.time()



if __name__ == '__main__':
    try:
        cycle = cycler(False)
        import sys
        import atexit
        atexit.register(cycle.shutdown)
        def write_time(text=''):
            print "running %s: %f" % (text,time.time())
        write_time('Main')
        cycle.cycle(4,write_time,"Cycletask1!")
        #longtask=cycle.add(80,write_time,"task2!")
        #f=cycle.add(7,write_time,"task3!")
        time.sleep(2)
        #cycle.remove(f)
        #time.sleep(5)
        #cycle.remove(longtask)
        #cycle.shutdown()
        #cycle.add(6,write_time,"task4!")
    except KeyboardInterrupt:
        #cycle.shutdown()
        sys.exit(0)
    
