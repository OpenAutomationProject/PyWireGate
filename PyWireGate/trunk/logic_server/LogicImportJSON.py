#!/usr/bin/env python
# -*- coding: utf-8 -*-
## -----------------------------------------------------
## LogicImportJSON.py
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

import codecs
import simplejson as json
import networkx as nx
import LogicLibrary

def get( file, printCode = False, displayGraph = False ):
  G=nx.DiGraph()
  lib = LogicLibrary.LogicLibrary().getLibrary()

  db = codecs.open( file, 'r', encoding = 'UTF-8' )
  data = db.read()
  loaddict = json.loads(data)
  db.close()

  parameter   = '' # the string to set up the block parameters
  init        = '' # the string containing the inital setup
  program     = '' # the string containing the concatenated instructions
  stateupdate = '' # the string containing the update of the states

  for name, attribute in loaddict['blocks'].iteritems():
    block = lib[ attribute['type'] ]
    G.add_node( name, attribute )
    # Add aditional, virtual node "<name>.state" that is treates as an additional
    # input with no dependancy as the state won't change during an update cycle,
    # only afterwards
    if block.hasState():
      G.add_node( name + '.state' )
      for p in range(len(block.outPorts())):
        if block.outPortNumberHasState( p ):
          stateupdate += "    self.%s_%s = %s_%s_next\n" % ( name, p, name, p )

  for signal in loaddict['signals']:
    b = loaddict['blocks']
    if lib[ loaddict['blocks'][ signal[0] ]['type'] ].outPortNumberHasState( signal[1] ):
      G.add_edge( signal[0] + '.state', signal[2], { 'ports': ( signal[1], signal[3] ), 'start': signal[0] } )
    else:
      G.add_edge( signal[0], signal[2], { 'ports': ( signal[1], signal[3] ), 'start': signal[0] } )
      
  intructionOrder = nx.topological_sort(G)
  
  for instruction in intructionOrder:
    if not instruction in loaddict['blocks']:
      continue # ignore the virtual state nodes
    libBlock = lib[ loaddict['blocks'][ instruction ]['type'] ]
    ins = []
    for i in range(len(libBlock.inPorts())):
      for e in G.in_edges_iter( instruction, True ):
        if e[2]['ports'][1] == i:
          if lib[ loaddict['blocks'][ e[2]['start'] ]['type'] ].outPortNumberHasState( e[2]['ports'][0] ):
            ins.append( "self.%s_%s" % ( e[2]['start'], e[2]['ports'][0] ) )
          else:
            ins.append( "%s_%s" % ( e[2]['start'], e[2]['ports'][0] ) )
    outs = []
    for o in range(len(libBlock.outPorts())):
      outs.append( "%s_%s" % (instruction, o) )
    params = []
    for p in G.node[instruction]['parameters']:
      paramName = "%s_%s" % (instruction, p)
      paramValue = G.node[instruction]['parameters'][p]
      if isinstance( paramValue, basestring):
        paramValue = "globalVariables['%s']" % paramValue
      parameter += "    self.%s = %s\n" % (paramName, paramValue)
      params.append( "self." + paramName )
    i = libBlock.codingIntructions( instruction, ins, outs, params )
    if None != i[0]:
      init    += "    self.%s\n" % i[0]
    program += "    %s\n" % i[1]

  code = """import CodeClass
class LogikClass( CodeClass.CodeClass ):
  def __init__( self, globalVariables ):
%s
%s
  def run( self, globalVariables ):
    inspector = {}
    __dt = globalVariables['__dt']
    __time = globalVariables['__elapsedTime']
%s
%s
    return inspector
""" % ( parameter, init, program, stateupdate )

  if printCode:
    print code

  if displayGraph:
    # just to show - connect the states
    for name, attribute in loaddict['blocks'].iteritems():
      block = lib[ attribute['type'] ]
      if block.hasState():
        G.add_edge( name, name + '.state' )
    import matplotlib.pyplot as plt
    nx.draw(G)
    plt.show()
  
  c = compile( code, '<string>', 'exec' )
  return c