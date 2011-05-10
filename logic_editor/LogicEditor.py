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

import Queue
import re

from logic_server import LogicLibrary

# tmp:
import time

thisPath = '/'
LOGIC = None

class logic_editor(ConnectorServer):
    CONNECTOR_NAME = 'Logic Editor'
    CONNECTOR_VERSION = 0.1
    CONNECTOR_LOGNAME = 'logic_editor'
    def __init__(self,parent, instanceName):
        self._parent = parent
        if parent:
            self.WG = parent.WG
            global LOGIC
            LOGIC = self._parent.connectors['LogicServer']
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
        thisLib = 'MainLib' # FIXME iterate over it...
        f.write( '{"%s":{' % thisLib )
        blockPrefix = ''
        for blockName in lib[ thisLib ]:
          f.write( '%s"%s":{"name":"%s",' % (blockPrefix, blockName, blockName) )
          block = lib[ thisLib ][ blockName ]
          
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
          
          f.write( '"maskOptions":{' )
          prefix = ''
          maskOptions = block.maskOptions()
          for maskOption in maskOptions:
            option = maskOptions[maskOption]
            if type(option) in (int, float):
              f.write( '%s"%s":%s' % (prefix, maskOption, option) )
            elif type(option) == bool:
              option = 'true' if option else 'false'
              f.write( '%s"%s":%s' % (prefix, maskOption, option) )
            else:
              f.write( '%s"%s":"%s"' % (prefix, maskOption, option) )
            prefix = ','
          f.write( '},' )
          
          f.write( '"width":100,"height":50,"rotation":0,"flip":false,"color":[0.0,0.0,0.0],"background":[1.0, 1.0, 1.0]' )
          
          f.write( '}' )
          blockPrefix = ','
        f.write( '}}' )
      elif self.path.startswith("/logicCode"):
        contentType="text/plain"
        self.path = self.path.replace('/logicCode', thisPath + '/..')
        return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
        
        
      # Create the CometVisu interface for the internal variables
      elif self.path.startswith('/live/l'):
        # FIXME: BIG, Big, big memory and CPU leak! A created Queue must be
        # removed later, or the LogicServer will continue to fill it, even if
        # no page will be listening anymore!
        l = LOGIC.createQueue( None, None, None ) # get everything!
        contentType="text/plain"
        f.write('{"v":"0.0.1","s":"live%s"}' % l)
      elif self.path.startswith('/live/r'):
        try:
          l = int( re.findall('s=live(\d*)', self.path )[0] )
        except IndexError:
          return # FIXME - return sensible error message
        self.send_response(200)
        #self.send_header("Content-type", 'text/plain')
        self.send_header("Content-type", 'application/json')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write( '{"d":[' )
        sep = ''
        getWait = True # wait for the first result, but not any longer
        while True:
          #self.wfile.write( "new line\n" )
          try:
            m = LOGIC.queues[l][3].get( getWait )
            getWait = False
            self.wfile.write( sep )
            self.wfile.write( '{"task":"%s","module":"%s","block":"%s","value":%s}' % m )
            sep = ','
          except Queue.Empty:
            self.wfile.write( '],"i":0}')
            return # Queue is empty, end connection
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
  