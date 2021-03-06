#!/usr/bin/env python
# -*- coding: utf-8 -*-
## -----------------------------------------------------
## TaskManager.py
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

# A task manager that runs the little code snippets 
#from multiprocessing import Process, Queue as mpQueue
import threading
import Queue
import time

class TaskManager:
  """The task manager that called all programs in the defined order at the
  specified interval"""
  taskList = {}
  inspection = Queue.Queue()
  
  def __init__( self, parent ):
    self._parent = parent
  
  def addInterval( self, name, interval ):
    if name in self.taskList:
      raise # Name already in interval list!
    #q = mpQueue()
    q = Queue.Queue()
    self.taskList[name] = [ None, interval, q, [] ]
    
  def addTask( self, interval, name, code ):
    if interval in self.taskList:
      self.taskList[ interval ][3].append( [name, code] )
    else:
      raise # interval doesn't exist
  
  def getMessage( self ):
    try:
      return self.inspection.get( False )
    except Queue.Empty:
      return
      
  def start( self ):
    # start the task handling
    self.startTime = time.time() # only *nix is interesting here
    for i in self.taskList:
      interval = self.taskList[ i ][1]
      q        = self.taskList[ i ][2]
      #self.taskList[ i ][0] = Process( target = self.aIntervall, args = ( i, interval, q, self.startTime ) )
      self.taskList[ i ][0] = threading.Thread( target = self.aIntervall, args = ( i, interval, q, self.inspection, self.startTime ) )
      self.taskList[ i ][0].start()
    
  def stop( self ):
    # stop all tasks
    for i in self.taskList:
      self.taskList[ i ][2].put( 'STOP' )
      self.taskList[ i ][0].join()
    
  def aIntervall( self, name, interval, q, inspection, startTime ):
    globalVariables = {
      '__name'       : name,
      '__interval'   : interval,
      '__startTime'  : startTime,
      '__elapsedTime': 0.0,
      '__dt'         : interval
    }
    # initialize the classes
    for i in range( len( self.taskList[ name ][3] )):
      self.taskList[ name ][3][i][1] = self.taskList[ name ][3][i][1]( globalVariables )
    # main loop
    while 1:
      __elapsedTime = time.time() - startTime
      globalVariables['__dt'] = __elapsedTime - globalVariables['__elapsedTime']
      globalVariables['__elapsedTime'] = __elapsedTime
      #print 'XX', self.taskList[ name ][3]
      for i in self.taskList[ name ][3]:
        inspector = i[1].run( globalVariables )
        inspection.put( (name, i[0], inspector) ) 
      try:
        message = q.get( True, interval )
      except Queue.Empty:
        continue # just start next iteration immediately
      
      if 'STOP' == message:
	break
    
  def showStatus( self ):
    print self.taskList
    