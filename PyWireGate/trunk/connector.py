import threading
import time

class Connector:
    CONNECTOR_NAME = 'unnamed connector'
    CONNECTOR_VERSION = 0.1
    CONNECTOR_LOGNAME = __name__

    isrunning=False
    def __init__(self,parent,instanceName):
        self._parent = parent
        self.WG = parent.WG
        self.instanceName = instanceName
        """Overide"""
    def start(self):
        self.log("%s (%s) starting up" % (self.CONNECTOR_NAME, self.instanceName) ,'info','WireGate')
        self.isrunning=True
        self._thread = threading.Thread(target=self.run,name=__name__)
        self._thread.setDaemon(1)
        self._thread.start()

    def debug(self,msg):
        self.log(msg,'debug')
        
    def log(self,msg,severity='info',instance=False):
        if not instance:
            instance = self.instanceName
        self._parent.log(msg,severity,instance)

    def shutdown(self):
        self.log("%s (%s) shutting down" % (self.CONNECTOR_NAME, self.instanceName) ,'info','WireGate')
        self.isrunning=False
        self._thread.join(2)
        if self._thread.isAlive():
            self.log("Shutdown Failed",'critical')

    def idle(self,stime):
        cnt = 0
        while self.isrunning:
            if cnt >= stime:
                return
            cnt+=.5
            time.sleep(.5)
        
    def run(self):
        """Overide"""
        while self.isrunning:
            pass
            

    def setValue(self, dsobj):
        self.log("unconfigured setValue in %r called for %s" % (self,dsobj.name) ,'warn','WireGate')
        pass

import SocketServer
import socket
class ConnectorServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer,Connector):
    allow_reuse_address = 1 
    def __init__(self, server_address, RequestHandlerClass):
        SocketServer.BaseServer.__init__(self, server_address, RequestHandlerClass)
        self.socket = socket.socket(self.address_family,self.socket_type)
        self.socket.settimeout(1)
        self.server_bind()
        self.server_activate()

    def run(self):
        self.serve_forever()

    def serve_forever(self):
        while self.isrunning:
            self.handle_request()

    def get_request(self):
        while self.isrunning:
            try:
                sock, addr = self.socket.accept()
                sock.settimeout(None)
                return (sock, addr)
            except socket.timeout:
                if not self.isrunning:
                    raise socket.error

    def shutdown(self):
        self.server_close()
        Connector.shutdown(self)


