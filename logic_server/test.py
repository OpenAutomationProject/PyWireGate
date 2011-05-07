#!/usr/bin/python
import LogicImportJSON
import TaskManager
import LogicCommander

import time

# Load logik.json
exec LogicImportJSON.get( 'logik.json' )
Logik1 = LogikClass

# Load logik2.json - and show code and diagram
exec LogicImportJSON.get( 'logik2.json', True, True )
Logik2 = LogikClass

t = TaskManager.TaskManager()
t.addInterval( 'Interval 1 - 75 ms Task', 0.075 )
t.addInterval( 'Interval 2 - 10 ms Task', 0.01  )
t.addTask( 'Interval 1 - 75 ms Task', 'Logik1', Logik1 )
t.addTask( 'Interval 2 - 10 ms Task', 'Logik2', Logik2 )
for i in range(10):
  t.addInterval( 'i%s' % i, 6.0 )
  t.addTask( 'i%s' % i, 'foo', Logik1 )
t.start()
time.sleep(6.5)
t.stop()
