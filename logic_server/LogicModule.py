#!/usr/bin/env python
# -*- coding: utf-8 -*-
## -----------------------------------------------------
## LogicModule.py
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

class LogicModule:
  """The base class for a generic logic module"""
  def name( self ):
    return self._name
  
  def inPorts( self ):
    return self._inPorts
  
  def outPorts( self ):
    return self._outPorts
  
  def parameters( self ):
    return self._parameters
  
  def drawingIntructions( self ):
    return self._drawingInstructions
  
  def maskOptions( self ):
    return self._maskOptions
  
  def codingIntructions( self, name, ins, outs, params ):
    return self._codingInstructions( name, ins, outs, params )

  def hasState( self ):
    for port in self.outPorts():
      if ('state' == port[1]) or ('const' == port[1]):
        return True
    return False
    
  def outPortNumberHasState( self, i ):
    portType = self.outPorts()[ i ][1]
    if ('state' == portType) or ('const' == portType):
      return True
    return False
    
  def outPortNameHasState( self, n ):
    for port in self.outPorts():
      if port[0] == n:
        if ('state' == port[1]) or ('const' == port[1]):
          return True
        return False
