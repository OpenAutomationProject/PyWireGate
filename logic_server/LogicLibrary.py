#!/usr/bin/env python
# -*- coding: utf-8 -*-
## -----------------------------------------------------
## LogicLibrary.py
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

import LogicModule

class ConstBlock( LogicModule.LogicModule ):
  _name                = "const"
  _inPorts             = []
  _outPorts            = [ ( 'out', 'const' ) ]
  _parameters          = [ 'value' ]
  _drawingInstructions = ""
  _codingInstructions  = lambda s, n, i, o, p: ( "%s = %s" % ( o[0], p[0] ), "%s_next = %s" % ( o[0], p[0] ) )

class LogBlock( LogicModule.LogicModule ):
  _name                = "display"
  _inPorts             = [ 'in' ]
  _outPorts            = []
  _parameters          = []
  _drawingInstructions = ""
  #_codingInstructions  = lambda s, n, i, o, p: ( None, "print __time,',','\"%%s\"' %% globalVariables['__name'],',','%s',',',%s" % ( n, i[0]) )
  _codingInstructions  = lambda s, n, i, o, p: ( None, "inspector['%s'] = %s" % ( n, i[0]) )

class GainBlock( LogicModule.LogicModule ):
  _name                = "gain"
  _inPorts             = [ 'in' ]
  _outPorts            = [ ( 'out', 'signal' )  ]
  _parameters          = [ 'gain' ]
  _drawingInstructions = ""
  _codingInstructions  = lambda s, n, i, o, p: ( None, "%s = %s * %s" % ( o[0], p[0], i[0] ) )

class SumBlock( LogicModule.LogicModule ):
  _name                = "sum"
  _inPorts             = [ 'in1', 'in2' ]
  _outPorts            = [ ( 'out', 'signal' )  ]
  _parameters          = []
  _drawingInstructions = ""
  _codingInstructions  = lambda s, n, i, o, p: ( None, "%s = %s + %s" % ( o[0], i[0], i[1] ) )

class MemoryBlock( LogicModule.LogicModule ):
  _name                = "memory"
  _inPorts             = [ 'in' ]
  _outPorts            = [ ( 'out', 'state' )  ]
  _parameters          = [ 'inital_value' ]
  _drawingInstructions = ""
  _codingInstructions  = lambda s, n, i, o, p: ( "%s = %s" % (o[0], p[0]), "%s_next = %s" % ( o[0], i[0] ) )

class IntegralBlock( LogicModule.LogicModule ):
  _name                = "integral"
  _inPorts             = [ 'in'   ]
  _outPorts            = [ ( 'out', 'state' )  ]
  _parameters          = [ 'initial_value' ]
  _drawingInstructions = ""
  _codingInstructions  = lambda s, n, i, o, p: ( "%s = %s" % (o[0], p[0]), "%s_next = %s * %s + self.%s" % ( o[0], "__dt", i[0], o[0] ) )

class LogicLibrary:
  """The container for all known library blocks"""
  _db = {}
  
  def __init__( self ):
    self.addBlock( ConstBlock    )
    self.addBlock( LogBlock      )
    self.addBlock( GainBlock     )
    self.addBlock( SumBlock      )
    self.addBlock( MemoryBlock   )
    self.addBlock( IntegralBlock )
    
  def addBlock( self, block ):
    b = block()
    self._db[ b.name() ] = b
  
  def getLibrary( self ):
    return self._db
  
