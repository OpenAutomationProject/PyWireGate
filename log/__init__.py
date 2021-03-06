# -*- coding: iso8859-1 -*-

## add notice as loglevel

import logging
import logging.handlers
import sys

logging._acquireLock()
## redefine logging
# Change the default levels to include NOTICE in
# the proper order of priority
logging.FATAL = logging.CRITICAL = FATAL = CRITICAL = 60
logging.ERROR = ERROR = 50
logging.WARN = logging.WARNING = WARN = WARNING = 40
logging.NOTICE = NOTICE = 30

# insert the levels with all the redefined values
# anything below NOTICE we don't have to add back in, its
# not getting redefined above with a new value
logging.addLevelName(NOTICE, 'NOTICE')
logging.addLevelName(WARNING, 'WARNING')
logging.addLevelName(WARN, 'WARN')
logging.addLevelName(ERROR, 'ERROR')
logging.addLevelName(FATAL, 'FATAL')
logging.addLevelName(CRITICAL, 'CRITICAL')

# define a new logger function for notice
# this is exactly like existing info, critical, debug...etc
def Logger_notice(self, msg, *args, **kwargs):
    """
    Log 'msg % args' with severity 'NOTICE'.

    To pass exception information, use the keyword argument exc_info
with
    a true value, e.g.

    logger.notice("Houston, we have a %s", "major disaster", exc_info=1)
    """
    if self.manager.disable >= NOTICE:
        return
    if NOTICE >= self.getEffectiveLevel():
        apply(self._log, (NOTICE, msg, args), kwargs)

# make the notice function known in the system Logger class
logging.Logger.notice = Logger_notice

# define a new root level notice function
# this is exactly like existing info, critical, debug...etc
def root_notice(msg, *args, **kwargs):
    """
    Log a message with severity 'NOTICE' on the root logger.
    """
    if len(root.handlers) == 0:
        basicConfig()
    apply(root.notice, (msg,)+args, kwargs)

# make the notice root level function known
logging.notice = root_notice

# add NOTICE to the priority map of all the levels
logging.handlers.SysLogHandler.priority_map['NOTICE'] = 'notice'

logging._releaseLock()

class isoStreamHandler(logging.StreamHandler):
    def emit(self,record):
        #record.message = record.message.decode('utf-8').encode('iso-8859-15')
        record.message = record.message.encode(sys.stderr.encoding)
        logging.StreamHandler.emit(self,record)



