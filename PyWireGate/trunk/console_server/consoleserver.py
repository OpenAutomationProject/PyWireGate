from connector import ConnectorServer
import SocketServer
import threading
import select
import re

class ConsoleRequestHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        print "Connect"
        self.request.send("WireGate Serivce Konsole\n# ")
        commands=""
        running = True
        self.removecr = re.compile(r"\r")
        while running:
            cliread,cliwrite,clierr = select.select([self.request],[],[],10)
            if self.request in cliread:
                data=self.request.recv(1024)
                if not data:
                    break
                commands = str(data)
                while commands.find("\n") != -1:
                    cmd, commands = commands.split("\n", 1)
                    cmd = self.removecr.sub("",cmd)
                    if cmd == "exit":
                        running = False
                        break
                    else:
                        self.request.send(self.server.getcmd(cmd,self))
                        self.request.send("# ")



class console_server(ConnectorServer):
    connector_info = {'name':'Console Server','version':'0.1','logname':'console_server'}
    def __init__(self,wiregate):
        self.WG = wiregate
        try:
            config = self.WG.config['ConsoleServer']
        except KeyError:
            config = {'port':4401}

        ConnectorServer.__init__(self,("0.0.0.0",config['port']),ConsoleRequestHandler )
        self.start()
    def getcmd(self,cmd,client):
        if len(cmd)==0:
            return ""
        area = ""
        name = ""
        command = ""
        cmdsplit = cmd.split(" ")
        if len(cmdsplit)==2:
            area, command = cmdsplit
        elif len(cmdsplit)==3:
            area, name, command = cmdsplit
        if area=="wiregate":
            if command=="stop":
                self.WG.stop()
                client.finish()
        if area=="plugins":
            print "command"+command
            if command=="list":
                ret = ""
                for plug in self.WG.plugins.keys():
                    ret +=plug+"\n"
                return ret
            if command=="stop":
                try:
                    self.WG.plugins[name].shutdown()
                    return "Done\n"
                except:
                    pass
                    return "Failed\n"
            if command=="start":
                try:
                    self.WG.plugins[name].start()
                    return "Done\n"
                except:
                    pass
                    return "Failed\n"
                
        return "unknown cmd: "+repr(cmdsplit)+"\n"
        
    
        
