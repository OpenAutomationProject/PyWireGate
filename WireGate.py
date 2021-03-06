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
import log 
import re
import threading

import ConfigParser

import datastore
import scheduler


class WireGate(daemon.Daemon):
    def __init__(self,REDIRECTIO=False):
        self._parent = self
        self.WG = self
        self.watchdoglist = {}
        self.connectors = {}
        self.LOGGER = {}
        self.LoggerCreateLock = threading.RLock()
        
        self.REDIRECTIO = REDIRECTIO
        
        ## Get the path of this script
        self.scriptpath = re.findall("from \x27(.*)\x2F",str(datastore))[0]

        self.readWireGateConfig()

        self.ErrorLOGGER = self.__createLog("WireGateErr",filename=self.config['WireGate']['errorlog'],maxlevel='error')
        
        ## Start the Datastore
        self.DATASTORE = datastore.datastore(self)
        
        ## Start the Daemon
        daemon.Daemon.__init__(self,self.config['WireGate']['pidfile'],REDIRECTIO)



    def readWireGateConfig(self):
        self.config = self.readConfig("/etc/wiregate/pywiregate.conf")
        defaultconfig = {
            'pidfile' : "%s/wiregated.pid" % self.scriptpath,
            'datastore' : "%s/datastore.db" % self.scriptpath,
            'logfile' : "%s/wiregated.log" % self.scriptpath,
            'errorlog' : "%s/wiregated-error.log" % self.scriptpath,
            'loglevel': 'info',
            'defaultencoding': 'iso-8859-15'
        }
        
        self.checkconfig("WireGate",defaultconfig)
        ## Remove this later
        if "plugins" in self.config['WireGate']:
            self.log("old Config",'critical')
        


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
                    try:
                        exec("import %s" % connector)
                    except:
                        self.WG.errorlog(connector)
                        self.log("unknown connector: %s" % connector,'error')
                        continue
                    ## Load the Connector
                    exec("self.connectors['%s'] = %s.%s(self,name)" % (name,connector,connector))
            except:
                self.WG.errorlog(connector)
                pass
        
        ## Start the Sheduler
        self.SCHEDULER = scheduler.scheduler(self)
        self.SCHEDULER.start()

        if os.getuid() == 0:
            import pwd
            startuser=pwd.getpwuid(os.getuid())
            try:
                runasuser=pwd.getpwnam(self.config['WireGate']['user'])
                getpath = lambda x: "/".join(x.split("/")[:-1])
                        
                ##Set Permissions on 
                for sysfile in [self.config['WireGate']['pidfile'],self.config['WireGate']['logfile'],self.config['WireGate']['datastore']]:
                    if not os.path.exists(sysfile):
                        open(sysfile,'w').close()
                    os.chown(sysfile,runasuser[2],runasuser[3])
                
                
                ##removed until fixing permissions
                #os.setregid(runasuser[3],runasuser[3])
                #os.setreuid(runasuser[2],runasuser[2])
        
                self.log("Change User/Group from %s(%d) to %s(%d) FIXME: disabled" % (startuser[0],startuser[2],runasuser[0],runasuser[2]))
            
            except KeyError:
                pass
        if os.getuid() == 0:
            self.log("### Run as root is not recommend ### set user in pywiregate.conf",'warn')
        
        ## Mainloop only checking for Watchdog
        while True:
            time.sleep(5)
            self._checkwatchdog()


    ## always looping watchdog checker
    def _checkwatchdog(self):
        for obj in self.watchdoglist.keys():
            if time.time() > self.watchdoglist[obj]:
                    self.log("\n\nInstanz %s reagiert nicht\n\n" % obj,'error')
                    try:
                        self.connectors[obj].shutdown()
                    except:
                        pass
                    del self.watchdoglist[obj]
    
    ## set Watchdog
    def watchdog(self,instance,wtime):
        self.watchdoglist[instance] = time.time()+wtime


    def shutdown(self):
        #for dobj in self.DATASTORE.dataobjects.keys():
        #    print dobj+": "+str(self.DATASTORE.dataobjects[dobj].getValue())
        self.log("### Shutdown WireGated ###")
        
        self.SCHEDULER.shutdown()
        for instance in self.connectors.keys():
            try:
                self.connectors[instance].shutdown()
            except:
                pass
                
        ## now save Datastore
        self.DATASTORE.shutdown()

    
    ## Handle Errors
    def errorlog(self,msg=False):
        try:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tback = traceback.extract_tb(exc_traceback)
        except:
            exc_value = ""
            exc_type = ""
            tback = ""
            pass
        if msg:
            self.ErrorLOGGER.error(repr(msg))
        errmsg = "%r %r %r" % (exc_type, exc_value,tback)
        self.ErrorLOGGER.error(errmsg)
    

        
    ## TODO: Check COnfig for seperate Logfiles and min level for logging
    def createLog(self,instance):
        if instance in self.config:
            loglevel = self.config[instance].get('loglevel',False)
            filename = self.config[instance].get('logfile',False)
        else:
            loglevel = self.config['WireGate'].get('loglevel',False)
            filename = self.config['WireGate'].get('logfile',False)

        return self.__createLog(instance,filename=filename,maxlevel=loglevel)

    ## Create the Loginstance
    def __createLog(self,instance,filename=False,maxlevel=False):
        if not maxlevel:
            maxlevel = self.config['WireGate']['loglevel']
        if not filename:
            filename = self.config['WireGate']['logfile']
        LEVELS = {'debug': log.logging.DEBUG,'info': log.logging.INFO,'notice': log.logging.NOTICE,'warning': log.logging.WARNING,'error': log.logging.ERROR,'critical': log.logging.CRITICAL}
        level = LEVELS.get(maxlevel, log.logging.NOTSET)
        # create logger

        formatter = log.logging.Formatter('%(asctime)s %(name)-12s: %(levelname)-8s %(message)s')
        logger = log.logging.getLogger(instance)
        logger.setLevel(level)
        if filename:
            ## python handle logrotating
            handler = log.logging.handlers.TimedRotatingFileHandler(filename,'MIDNIGHT',encoding='UTF-8',backupCount=7)
            
            ## Handler if logrotate handles Logfiles
            #handler = logging.handlers.WatchedFileHandle(filename)
            handler.setFormatter(formatter)
            handler.setLevel(level)
            logger.addHandler(handler)


        # create console handler and set level to debug
        if self.REDIRECTIO:
            #console = logging.StreamHandler()
            console = log.isoStreamHandler()
            console.setFormatter(formatter)            
            logger.addHandler(console)
        return logger

    ## Logger for all instances that check/create logger based on Configfile
    def log(self,msg,severity="info",instance="WireGate"):
        try:
            self.LoggerCreateLock.acquire()
            try:
                logger = self.LOGGER[instance]
            except KeyError:
                logger = self.LOGGER[instance] = self.createLog(instance)
                pass
        finally:
            self.LoggerCreateLock.release()
        try:
            if severity=="debug":
                logger.debug(msg)
            elif severity=="info":
                logger.info(msg)
            elif severity=="notice":
                logger.notice(msg)
            elif severity=="warning":
                logger.warning(msg)
            elif severity=="warn":
                #print "SEVERITY: %r " % logging._levelNames

                logger.warning(msg)
            elif severity=="error":
                logger.error(msg)
            elif severity=="critical":
                logger.critical(msg)
            else:
                logger.info(msg)
        except:
            ## logging shouldnt break execution
            #pass
            raise


    def debug(self,msg):
        self.log(msg,"debug")

    ## Decouple from dir to avoid unmount troubles
    def decouple(self):
        os.chdir("/")
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



