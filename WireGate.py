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

import ConfigParser


import datastore

class WireGate(daemon.Daemon):
    def __init__(self,REDIRECTIO=False):
        self.WG = self
        self.watchdoglist = {}
        self.connectors = {}
        self.LOGGER = {}
        
        ## Get the path of this script
        self.startpath = str(datastore).split( )[3][1:-15]

        ## Start the Datastore
        self.DATASTORE = datastore.datastore(self)

        self.readWireGateConfig()
        
        ## Start the Daemon
        daemon.Daemon.__init__(self,self.config['WireGate']['pidfile'],REDIRECTIO)



    def readWireGateConfig(self):
        self.config = self.readConfig("/etc/wiregate/pywiregate.conf")
        configdefault = {
            'pidfile' : '/usr/local/WireGate/wiregated.pid',
            'connector' : ''
        }
        
        ## Remove this
        if "plugins" in self.config['WireGate']:
            self.log("deprecated Config: use 'connector' instead of plugin",'warning')

        self.checkconfig("WireGate",configdefault)
        


    def checkconfig(self,instance,defaults):
        if instance not in self.config:
            self.config[instance] = defaults
            return
        for cfg in defaults:
            if cfg not in self.config[instance]:
                self.config[instance][cfg] = defaults[cfg]


    def readConfig(self,configfile):
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




    def isdaemon(self):
        ## Called when in Daemon state
        signal.signal(signal.SIGTERM,self._signalhandler)
        signal.signal(signal.SIGHUP,self._signalhandler)

    def _signalhandler(self,signum,frame):
        if signum == signal.SIGHUP:
            self.debug("LOGROTATE")
        elif signum == signal.SIGTERM:
            sys.exit(1)
        else:
            self.debug("Unknown Signal: %d  " % signum)


    def run(self):
        import time
        for configpart in self.config.keys():
            if "connector" in self.config[configpart]:
                name = configpart
                connector = self.config[configpart]['connector']
            else:
                ## no connector in Section
                continue
            try:
                if len(connector)>0:
                    ## Import Connector
                    exec("import %s" % connector)
                    ## Load the Connector
                    exec("self.connectors['%s'] = %s.%s(self,name)" % (name,connector,connector))
            except:
                self.WG.errorlog(connector)
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
        
        ## Mainloop only checking for Watchdog
        while True:
            time.sleep(5)
            self._checkwatchdog()


    ## always looping watchdog checker
    def _checkwatchdog(self):
        for obj in self.watchdoglist.keys():
            if time.time() > self.watchdoglist[obj]:
                    self.log("\n\nInstanz %s reagiert nicht\n\n" % obj,'error')
                    del self.watchdoglist[obj]
    
    ## set Watchdog
    def watchdog(self,instance,wtime):
        self.watchdoglist[instance] = time.time()+wtime


    def shutdown(self):
        #for dobj in self.DATASTORE.dataobjects.keys():
        #    print dobj+": "+str(self.DATASTORE.dataobjects[dobj].getValue())
        self.log("### Shutdown WireGated ###")
        for instance in self.connectors.keys():
            try:
                self.connectors[instance].shutdown()
            except:
                pass
                
        ## now save Datastore
        self.DATASTORE.save()

    
    ## Handle Errors
    def errorlog(self,msg=False):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tback = traceback.extract_tb(exc_traceback)
        print tback
        print exc_type, exc_value
        if msg:
            print repr(msg)
        
    ## TODO: Check COnfig for seperate Logfiles and min level for logging
    def createLog(self,instance):
        self.LOGFILES = ""
        return self.__createLog(instance)

    ## Create the Loginstance
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

    ## Logger for all instances that check/create logger based on Configfile
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

    ## Decouple from dir to avoid unmount troubles
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




