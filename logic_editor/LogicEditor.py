#!/usr/bin/env python
# -*- coding: iso8859-1 -*-
## -----------------------------------------------------
## LogicEditor.py
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


from connector import ConnectorServer
from StringIO import StringIO
import shutil
import BaseHTTPServer
import SimpleHTTPServer
import SocketServer
import threading

import re

from logic_server import LogicLibrary

# tmp:
import time

thisPath = '/'

class logic_editor(ConnectorServer):
    CONNECTOR_NAME = 'Logic Editor'
    CONNECTOR_VERSION = 0.1
    CONNECTOR_LOGNAME = 'logic_editor'
    def __init__(self,parent, instanceName):
        self._parent = parent
        if parent:
            self.WG = parent.WG
            global thisPath
            thisPath = parent.scriptpath + '/logic_editor'
        else:
            self.WG = False
        self.instanceName = instanceName
        defaultconfig = {
            'port' : 8080
        }
        
        self.WG.checkconfig(self.instanceName,defaultconfig)
        config = self.WG.config[self.instanceName]
        ConnectorServer.__init__(self,("0.0.0.0",config['port']),LERequestHandler )
        self.start()
        

class LERequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def handle2(self):
        data = self.request.recv(1024)
        cur_thread = threading.currentThread()
        response = "%s: %s: %s" % (self.server.WG.getname(),cur_thread.getName(), data)
        self.request.send(response)

    def log_message(self, format, *args):
        self.server.log("%s - %s" %
                         (self.address_string(),
                          format%args))

    def do_GET(self):
      f = StringIO()
      contentType="application/json"
      if self.path.startswith("/config"):
        contentType="text/plain"
        f.write('{ \x22v\x22:\x220.0.1\x22, \x22s\x22:\x22SESSION\x22 }\n\n')
      elif self.path.startswith("/logicLib"):
        lib = LogicLibrary.LogicLibrary().getLibrary()
        f.write( '{"MainLib":{' )
        blockPrefix = ''
        for blockName in lib:
          f.write( '%s"%s":{"name":"%s",' % (blockPrefix, blockName, blockName) )
          block = lib[ blockName ]
          
          f.write( '"inPorts":[' )
          prefix = ''
          for inPort in block.inPorts():
            f.write( '%s{"name":"%s","type":"signal"}' % (prefix, inPort) )
            prefix = ','
          f.write( '],' )
          
          f.write( '"outPorts":[' )
          prefix = ''
          for outPort in block.outPorts():
            portType = 'UNKNOWN'
            if outPort[1] in ( 'const', 'signal', 'state' ):
              portType = 'state'
            f.write( '%s{"name":"%s","type":"%s"}' % (prefix, outPort[0], portType) )
            prefix = ','
          f.write( '],' )
          
          f.write( '"parameters":[' )
          prefix = ''
          for parameter in block.parameters():
            f.write( '%s{"name":"%s","type":"float","default":0.0}' % (prefix, parameter) )
            prefix = ','
          f.write( '],' )
          
          f.write( '"width":100,"height":50,"rotation":0,"flip":false,"color":[0.0,0.0,0.0],"background":[1.0, 1.0, 1.0]' )
          
          f.write( '}' )
          blockPrefix = ','
        f.write( '}}' )
      elif self.path.startswith("/logicCode"):
        contentType="text/plain"
        self.path = self.path.replace('/logicCode', thisPath + '/..')
        return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
      elif self.path.startswith('/live'):
        self.send_response(200)
        self.send_header("Content-type", 'text/plain')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        while True:
          self.wfile.write( "new line\n" )
          self.wfile.flush()
          time.sleep( 1.0 )
      else:
        self.path = "%s%s" % ( thisPath, self.path )
        return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
        
      length = f.tell()
      f.seek(0)
      print "Length: "+str(length)
      self.send_response(200)
      self.send_header("Content-type", contentType)
      self.send_header("Access-Control-Allow-Origin", "*")
      self.send_header("Content-Length", str(length))
      self.end_headers()
      if f:
        print "send"
        self.copyfile(f, self.wfile)
        f.close()
  
    def copyfile(self, source, outputfile):
        shutil.copyfileobj(source, outputfile)
  