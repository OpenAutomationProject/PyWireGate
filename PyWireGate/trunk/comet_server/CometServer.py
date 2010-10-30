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


from connector import ConnectorServer
from StringIO import StringIO
import shutil
import BaseHTTPServer
import SimpleHTTPServer
import SocketServer
import threading

import re



class comet_server(ConnectorServer):
    CONNECTOR_NAME = 'Comet Server'
    CONNECTOR_VERSION = 0.1
    CONNECTOR_LOGNAME = 'comet_server'
    def __init__(self,WireGateInstance, instanceName):
        self.WG = WireGateInstance
        self.instanceName = instanceName
        defaultconfig = {
            'port' : 4498
        }
        
        self.WG.checkconfig(self.instanceName,defaultconfig)
        config = self.WG.config[self.instanceName]
        ConnectorServer.__init__(self,("0.0.0.0",config['port']),CometRequestHandler )
        self.start()
        

#class CometRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
class CometRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
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
        if not self.path.startswith("/rpc/"):
            return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
        f = StringIO()
        print self.path
        contentType="text/html"
        mustWait=True
        if self.path.startswith("/rpc/l"):
            contentType="text/plain"
            mustWait=False
            f.write('{ \x22v\x22:\x220.0.1\x22, \x22s\x22:\x22SESSION\x22 }\n\n')
        elif self.path.startswith("/rpc/r"):
            subscribega = re.findall("a=(.*?)\x26", self.path)
            for ga in subscribega:
                print "GA:"+str(ga)
        if mustWait:
            self.server.idle(3)
        length = f.tell()
        f.seek(0)
        print "Length: "+str(length)
        self.send_response(200)
        self.send_header("Content-type", contentType)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if f:
            print "send"
            self.copyfile(f, self.wfile)
            f.close()
        
    def copyfile(self, source, outputfile):
        shutil.copyfileobj(source, outputfile)
