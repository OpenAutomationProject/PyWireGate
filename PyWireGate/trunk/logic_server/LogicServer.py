#!/usr/bin/env python
# -*- coding: utf-8 -*-
## -----------------------------------------------------
## LogicServer.py
## -----------------------------------------------------
## Copyright (c) 2011, Christian Mayer, All rights reserved.
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
import LogicImportJSON
import TaskManager
import Queue
import time
import threading

## Load logik.json
#exec LogicImportJSON.get( 'logik.json' )
#Logik1 = LogikClass

## Load logik2.json - and show code and diagram
#exec LogicImportJSON.get( 'logik2.json' )
#Logik2 = LogikClass

#t = TaskManager.TaskManager()
#t.addInterval( 'Interval 1 - 75 ms Task', 0.075 )
#t.addInterval( 'Interval 2 - 10 ms Task', 0.01  )
#t.addTask( 'Interval 1 - 75 ms Task', 'Logik1', Logik1 )
#t.addTask( 'Interval 2 - 10 ms Task', 'Logik2', Logik2 )
#for i in range(10):
  #t.addInterval( 'i%s' % i, 6.0 )
  #t.addTask( 'i%s' % i, 'foo', Logik1 )
#t.start()
#time.sleep(6.5)
#t.stop()

class logic_server(Connector):
    CONNECTOR_NAME = 'Logic Server'
    CONNECTOR_VERSION = 0.1
    CONNECTOR_LOGNAME = 'logic_server'
    queues = {}
    lastQueueId = -1
    write_mutex = threading.RLock()
    
    def __init__(self,parent, instanceName):
        self._parent = parent
        self.WG = parent.WG
        self.instanceName = instanceName

        ## Deafaultconfig
        defaultconfig = {
        }
        
        ## check Defaultconfig Options in main configfile
        self.WG.checkconfig(self.instanceName,defaultconfig)
        
        ## set local config
        self.config = self.WG.config[self.instanceName]
        
        ## Start the Thread
        self.start()

    def run(self):
        # Load logik.json
        exec LogicImportJSON.get( self._parent.scriptpath + '/logik.json', True )
        self.Logik1 = LogikClass
        
        # Load logik2.json - and show code and diagram
        exec LogicImportJSON.get( self._parent.scriptpath + '/logik2.json', True )
        self.Logik2 = LogikClass

        t = TaskManager.TaskManager(self)
        t.addInterval( 'Interval 1 - 75 ms Task', 0.75 )
        t.addInterval( 'Interval 2 - 10 ms Task', 0.910  )
        t.addTask( 'Interval 1 - 75 ms Task', 'Logik1', self.Logik1 )
        t.addTask( 'Interval 2 - 10 ms Task', 'Logik2', self.Logik2 )
        t.start()
        while True:
          for m in iter( t.getMessage, None ):
            for q in self.queues:
              q = self.queues[q]
              if (q[0] == None or q[0] == m[0]) and (q[1] == None or q[1] == m[1]):
                for b in m[2]:
                  if q[2] == None or q[2] == b:
                    q[3].put( (m[0], m[1], b, m[2][b]) )
          time.sleep( 0.1 )
     
    def createQueue(self, taskFilter, logicFilter, blockFilter):
      try:
        self.write_mutex.acquire()
        self.lastQueueId += 1
        thisQueueId = self.lastQueueId # extra variable to be save when the lock is released
        self.queues[ thisQueueId ] = (taskFilter, logicFilter, blockFilter, Queue.Queue())
      finally:
        self.write_mutex.release()
        return thisQueueId