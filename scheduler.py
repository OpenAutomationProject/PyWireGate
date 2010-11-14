# -*- coding: iso8859-1 -*-
## -----------------------------------------------------
## Cycler
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

import time
import sys
from datetime import datetime
try:
    from apscheduler.scheduler import Scheduler as apscheduler
except ImportError:
    print >> sys.stderr, "apt-get install python-apscheduler"
    sys.exit(1)



class scheduler:
    def __init__(self,parent):
        self._parent = parent
        if parent:
            self.WG = parent.WG
        self.SCHEDULER = apscheduler()

    def start(self):
        self.load()
        self.log("SCHEDULER starting up")
        self.SCHEDULER.start()

    def load(self):
        schedules = filter(lambda x: x.startswith("SCHEDULER:"),self.WG.DATASTORE.dataobjects.keys())
        for shed in schedules:
            obj = self.WG.DATASTORE.dataobjects[shed]
            if 'cron' in obj.config:
                kwargs = {}
                
                ## change config from unicode to str
                for uoption in obj.config['cron'].keys():
                    kwargs[str(uoption)] = str(obj.config['cron'][uoption])
                
                self.debug("Adding %s - %s" % (shed,obj))
                setattr(obj.sendConnected.im_func,'__name__',"%s" % shed.encode('UTF-8'))
                self.SCHEDULER.add_cron_job(self.WG.DATASTORE.dataobjects[shed].sendConnected,**kwargs)

    def shutdown(self):
        self.debug("shutdown Scheduler\n%s" % self.SCHEDULER.dump_jobs())
        self.SCHEDULER.shutdown()
        
    def debug(self,msg):
        self.log(msg,'debug')
        
    
    ## Central logging
    def log(self,msg,severity='info',instance=False):
        self.WG.log(msg,severity,"scheduler")
        
        
if __name__ == '__main__':
    s = scheduler(False)
    time.sleep(155)
    s.shutdown()
    
    
##   "SHEDULER:cron_job-001": {
##      "config": { 
##          "cron" : {
##              "day_of_week" : "mon-fri",
##              "hour" : "8",
##              "minute" : "30"
##          }
##      
##      }, 
##      "connected": [ "KNX:14/1/50" ], 
##      "id": "cron_job-001", 
##      "lastupdate": 0, 
##      "name": "Test Cronjob weekday 8:30", 
##      "value": 1
##   }
    