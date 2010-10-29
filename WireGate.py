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

import sys
import os
import time
import signal
import traceback
import daemon
import logging

import datastore

class WireGate(daemon.Daemon):
    def __init__(self,REDIRECTIO=False):
        self.WG = self
        self.watchdoglist = {}
        self.plugins = {}
        self.LOGGER = {}
        self.DATASTORE = datastore.datastore(self)

        self.readWireGateConfig()
        daemon.Daemon.__init__(self,self.config['WireGate']['pidfile'],REDIRECTIO)

    def readWireGateConfig(self):
        self.config = self.readConfig("/etc/wiregate/pywiregate.conf")
        try:
            type(self.config['WireGate']['pidfile'])
        except:
            self.config['WireGate']['pidfile'] = "/usr/local/WireGate/wiregated.pid"
        



    def isdaemon(self):
        signal.signal(signal.SIGTERM,self._signalhandler)
        signal.signal(signal.SIGHUP,self._signalhandler)

    def _signalhandler(self,signum,frame):
        if signum == signal.SIGHUP:
            self.debug("LOGROTATE")
        elif signum == signal.SIGTERM:
            sys.exit(1)
        else:
            self.debug("Unknown Signal: "+str(signum))

    def readConfig(self,configfile):
        import ConfigParser
        config = {}
        configparse = ConfigParser.SafeConfigParser()
        configparse.readfp(open(configfile))
        for section in configparse.sections():
            options = configparse.options(section)
            config[section] = {}
            for opt in options:
                try:
                    config[section][opt] = configparse.getint(section,opt)
                except ValueError:
                    try:
                        config[section][opt] = configparse.getfloat(section,opt)
                    except ValueError:
                        config[section][opt] = configparse.get(section,opt)
        return config


    def shutdown(self):
        #for dobj in self.DATASTORE.dataobjects.keys():
        #    print dobj+": "+str(self.DATASTORE.dataobjects[dobj].getValue())
        self.log("### Shutdown WireGated ###")
        for instance in self.plugins.keys():
            try:
                self.plugins[instance].shutdown()
            except:
                pass
                
        ## now save Datastore
        self.DATASTORE.save()

    def run(self):
        import time
        for plugin in self.config['WireGate']['plugins'].split(","):
            try:
                exec("import " +plugin)
                exec("self.plugins['"+plugin+"'] = "+plugin+"."+plugin+"(self)")
            except:
                self.WG.errorlog(plugin)
                pass

        if os.getuid() == 0:
            import pwd
            startuser=pwd.getpwuid(os.getuid())
            try:
                runasuser=pwd.getpwnam(self.config['WireGate']['user'])
                ##Set Permissions
                os.chown(self.config['WireGate']['pidfile'],runasuser[2],runasuser[3])
                os.chown(self.config['WireGate']['logfile'],runasuser[2],runasuser[3])
                os.setregid(runasuser[3],runasuser[3])
                os.setreuid(runasuser[2],runasuser[2])
                self.log("Change User/Group from %s(%d) to %s(%d)" % (startuser[0],startuser[2],runasuser[0],runasuser[2]))
            except KeyError:
                pass
        if os.getuid()==0:
            self.log("\n### Run as root is not recommend\n### set user in pywiregate.conf\n\n")
        while True:
            time.sleep(5)
            self._checkwatchdog()


    def getname(self):
        return "WireGate"

    def _checkwatchdog(self):
        for obj in self.watchdoglist.keys():
            if time.time() > self.watchdoglist[obj]:
                    self.log("\n\nInstanz %s reagiert nicht\n\n" % obj,'error')
                    del self.watchdoglist[obj]
    
    def watchdog(self,instance,wtime):
        self.watchdoglist[instance] = time.time()+wtime
    
    def errorlog(self,msg=False):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tback = traceback.extract_tb(exc_traceback)
        print tback
        print exc_type, exc_value
        if msg:
            print repr(msg)
        

    def createLog(self,instance):
        self.LOGFILES = ""
        return self.__createLog(instance)


    def __createLog(self,instance,filename=False,maxlevel='debug'):
        LEVELS = {'debug': logging.DEBUG,'info': logging.INFO,'warning': logging.WARNING,'error': logging.ERROR,'critical': logging.CRITICAL}
        level = LEVELS.get(maxlevel, logging.NOTSET)
        # create logger
        logging.basicConfig(level=level,format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
        logger = logging.getLogger(instance)
        logger.setLevel(logging.DEBUG)

        # create console handler and set level to debug
        #if not self.REDIRECTIO:
        #    console = logging.StreamHandler()
        #    logger.addHandler(console)
        return logger

    def log(self,msg,severity="info",instance="WireGate"):
        LEVELS = {'debug': logging.debug,'info': logging.info,'warning': logging.warning,'error': logging.error,'critical': logging.critical}
        level = LEVELS.get(severity, logging.info)
        try:
            logger = self.LOGGER[instance]
        except KeyError:
            logger = self.LOGGER[instance] = self.createLog(instance)
            pass
        if severity=="debug":
            logger.debug(msg)
        elif severity=="info":
            logger.info(msg)
        elif severity=="warning":
            logger.warning(msg)
        elif severity=="error":
            logger.error(msg)
        elif severity=="critical":
            logger.critical(msg)
        else:
            logger.info(msg)


    def debug(self,msg):
        self.log(msg,"debug")

    def decouple(self):
        os.chdir("/usr/local/WireGate")
        os.umask(0)



if __name__ == "__main__":

    try:
        import os
        import sys
        import getopt
        try:
            opts, args = getopt.getopt(sys.argv[1:], "", ["start","stop","logrotate","nodaemon","stdout"])
        except getopt.GetoptError:
            print "Fehler"
            sys.exit(2)
        ACTION = ""
        RUNDAEMON = True
        REDIRECTIO = True
        for opt, arg in opts:
            if opt in ("--start"):
                ACTION = "start"
            if opt in ("--stop"):
                ACTION = "stop"
            if opt in ("--logrotate"):
                ACTION = "logrotate"
            if opt in ("--nodaemon"):
                RUNDAEMON = False
            if opt in ("--stdout"):
                REDIRECTIO = False


        WIREGATE = WireGate(REDIRECTIO)
        if ACTION == "start":
            WIREGATE.start(RUNDAEMON)
        elif ACTION == "stop":
            WIREGATE.stop()
        elif ACTION == "logrotate":
            WIREGATE.logrotate()
        else:
            print "--start oder --stop"
            sys.exit(1)
        if not RUNDAEMON:
            while True:
                pass
    except KeyboardInterrupt:
        pass
        print "Exiting"
        sys.exit(0)




