#!/usr/bin/env python

try:
    import os
    import sys
    import time
    import atexit
    import resource
    from signal import SIGTERM,SIGHUP
except StandardError, e:
    import sys
    print "Error while loading libraries: "
    print e
    sys.exit()

class Daemon(object):
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, pidfile, REDIRECTIO=True):
        self.pidfile = pidfile
        self.REDIRECTIO = REDIRECTIO
        

    def daemonize(self):
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                time.sleep(.2)
                os._exit(0)
        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)" % (e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
        self.decouple()
        os.setsid()

        # do second fork
        try:

            pid = os.fork()
            if pid > 0:
                # exit from second parent, print eventual PID before
                self.log("Daemon PID %d" % pid)
                sys.stdout.flush()
                os._exit(0)

        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)" % (e.errno, e.strerror))
            os._exit(1)


        sys.stdout.flush()
        sys.stderr.flush()
        ## Cleanup
        if self.REDIRECTIO:
            maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
            if (maxfd == resource.RLIM_INFINITY):
                 maxfd = 1024
            # close all file descriptors.
            for fd in range(0, maxfd):
               try:
                  os.close(fd)
               except OSError:	# ERROR, fd wasn't open to begin with (ignored)
                  pass
                  
            os.open(os.devnull, os.O_RDWR)	# standard input (0)
            # Duplicate standard input to standard output and standard error.
            os.dup2(0, 1)			# standard output (1)
            os.dup2(0, 2)			# standard error (2)
        self.writepid()


    def writepid(self):
        pid = str(os.getpid())
        file(self.pidfile,'w+').write("%s\n" % pid)
        
        
    def __shutdown(self):
        self.shutdown()
        self.delpid()

        
    def isdaemon(self):
        """Overried with isdaemon"""

    def delpid(self):
        try:
            os.remove(self.pidfile)
        except OSError:
            pass

    def shutdown(self):
        """Override with shutdown"""

    def readpidfile(self):
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        return pid

    def logrotate(self):
        pid = self.readpidfile()
        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return # 
        os.kill(pid,SIGHUP)
        
    def stop(self):
        pid = self.readpidfile()
        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return # not an error in a restart

        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)

    def restart(self):
        self.stop()
        self.start()

    def decouple(self):
        os.chdir("/")
        os.setsid()
        os.umask(0)

    def start(self,rundaemon=True):
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            try:
                procfile = file("/proc/%d/status" % pid, 'r')
                procfile.close()
            except IOError:
                self.delpid()
            except TypeError:
                self.delpid()
            else:
                message = "pidfile %s already exist. Daemon already running?\n"
                sys.stderr.write(message % self.pidfile)
                sys.exit(1)
        if rundaemon:
            self.daemonize()
        else:
            self.writepid()
            self.decouple()
            
            
        atexit.register(self.__shutdown)
        self.isdaemon()
        self.run()

    def run(self):
        """Override while subclassing"""
        