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


class TaskRunner:
    def __init__(self,parent):
        self._parent = parent
        if parent:
            self.WG = parent.WG
        else:
            self.WG = False
        self.isrunning = True

        self.waiting = threading.Timer(0,lambda: None)


        self.mutex = threading.RLock()
        
        ## function for time based sortingg of tasks
        self.getTime = lambda x: x.getTime
        
        ## all not running tasks goes here
        self.taskList = []
        
        ## all started tasks goes here
        self.running = {}
    
    def debug(self,msg):
        print "DEBUG Cycler: %s" % msg

    def remove(self, task):
        if not self.isrunning:
            
            ## dont try to get a mutex on shutdown
            return False
        try:
            self.mutex.acquire()
            if task in self.taskList:
                try:
                    self.taskList.remove(task)
                except:
                    pass
                self.debug("Removed %r" % task.action)
                if len(self.taskList) == 0:
                    ## kill waiting timer
                    self.debug("Cancel GLobal wait")
                    self.waiting.cancel()
                    
            if task in self.running:
                try:
                    if self.running[task].isAlive():
                        self.running[task].cancel()
                        self.debug("Canceled %r" % task.args)
                finally:
                    self.debug("terminated %r" % task.args)
                    del self.running[task]

        finally:
            self.mutex.release()



    def event(self,rtime,function,*args,**kwargs):
        if not self.isrunning:
            ## dont try to get a mutex
            return False
        self.debug("adding event: %r (%r / %r)" % (function,args,kwargs))
        ## rtime is a date as unix timestamp
        rtime = rtime - time.time()
        if rtime >0:
            task = Task(self,rtime,function,args=args,kwargs=kwargs)
            self._Shedule(task)
            return task
        else:
            print "expired  %r (%r / %r)" % (function,args,kwargs)

    
    def add(self,rtime,function,*args,**kwargs):
        if not self.isrunning:
            ## dont try to get a mutex
            return False
        self.debug("adding task: %r (%r / %r)" % (function,args,kwargs))
        task = Task(self,rtime,function,args=args,kwargs=kwargs)
        self._Shedule(task)
        return task
    
    def cycle(self,rtime,function,*args,**kwargs):
        if not self.isrunning:
            ## dont try to get a mutex
            return False
        self.debug("adding cycliv task: %r (%r / %r)" % (function,args,kwargs))
        task = Task(self,rtime,function,cycle=True,args=args,kwargs=kwargs)
        self._Shedule(task)
        return task
    
    def _Shedule(self,task):
        print "adding task %r" % task
        self.mutex.acquire()
        self.taskList.append(task)
        
        ## Try to stop running timer
        ## Fixme isalive
        try:
            self.waiting.cancel()
        except:
            pass
        
        self.taskList.sort(key=self.getTime)
        self.mutex.release()

        ## check if any Timer need activation
        self._check()
        
        
    def _check(self):
        self.debug("Cycle")
        try:
            self.mutex.acquire()
            print "acitve tasks %d " % threading.activeCount()
            atasks = "Active tasks: "
            for rtask in threading.enumerate():
                atasks += " %r" % rtask.getName()
                    
                
            print atasks
            ## all actions that need activation in next 60seconds
            for task in filter(lambda x: x.getTime() < 60, self.taskList):
                try: 
                    exectime = task.getTime()
                    name = "event"
                    if task.cycle:
                        name = "cycle"
                    self.running[task] = threading.Timer(exectime,task.run)
                    self.running[task].setName("%s_%r" % (name,time.asctime(time.localtime(task.timer))))
                    self.running[task].start()
                except:
                    print "Failed"
                    raise
                ## remove from List because its now active
                self.taskList.remove(task)
        finally:
            if len(self.taskList) >0:
                print "Wait for later timer %r" % (self.taskList[0].getTime()-5)
                self.waiting = threading.Timer(self.taskList[0].getTime()-5 ,self._check)
                self.waiting.start()
            self.mutex.release()

            
    def shutdown(self):
        print "Try killing"
        self.isrunning = False
        try:
            ## stop all new timer
            self.mutex.acquire()
            self.taskList = []
            for task in self.running.keys():
                print "acitve tasks %d " % threading.activeCount()
                print "cancel task %r" % task.args
                try:
                    rtask = self.running.pop(task)
                    rtask.cancel()
                    rtask.join()
                except:
                    pass
                
            print self.waiting
            
            print "Have Mutex"
            try:
                self.waiting.cancel()
                self.waiting.join()
            except:
                pass
            print "Thread canceld"


        except:
            self.debug("SHUTDOWN FAILED")


class Task:
    def __init__(self,parent,rtime,function,cycle=False,args = [],kwargs={}):
        self.Parent = parent
        self.WG = parent.WG
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
            self.Parent._Shedule(self)
            

    def getTime(self):
        return self.timer - time.time()



if __name__ == '__main__':
    try:
        cycle = TaskRunner(False)
        import sys
        import atexit
        #atexit.register(cycle.shutdown)
        def write_time(text=''):
            print "running %s: %f" % (text,time.time())
        write_time('Main')
        cycle1 = cycle.cycle(4,write_time,"Cycletask1!")
        cycle2 = cycle.cycle(8,write_time,"Cycletask2!")
        
        longtask=cycle.add(80,write_time,"Longtask 80 secs!")
        
        f=cycle.add(7,write_time,"task3!")
        
        cycle.event(time.mktime((2010,11,6,21,54,00,0,0,0)),write_time,"event 21:54")
        time.sleep(2)
        cycle.remove(f)
        time.sleep(5)
        print "##################remove longtask %r" % longtask
        cycle.remove(longtask)
        
        #cycle.cycle(4,write_time,"Cycletask6!")
        print "KILL CYCLE"
        cycle.remove(cycle1)
        cycle.remove(cycle2)
        #cycle.shutdown()
        #cycle.add(6,write_time,"task4!")
        while threading.activeCount() > 1:
            time.sleep(1)
    except KeyboardInterrupt:
        cycle.shutdown()
        cycle.waiting.join(5)
        sys.exit(0)
    
