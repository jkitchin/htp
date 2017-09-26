'''
htp - High Throughput module

this module exists to facilitate high-throughput computing including
automated remote job submission and monitoring.

Importing the htp module controls some behavior in the Torque/PBS
queue system.

1) it changes the working directory to $PBS_O_WORKDIR

2) if it is
imported first, it sets the backend of matplotlib to Agg, so no gui
windows are produced.

Submodules available:
======================
ssh - python interface to send remote commands by ssh
rsync - python interface to rsync
crontab - create and delete crontab entries from python
remote_qn - modifies Jacapo.calculate to use the torque queue

examples:
1. using a timeout signal to prevent hanging
'''

import os

if 'PBS_O_WORKDIR' in os.environ:
    os.chdir(os.environ['PBS_O_WORKDIR'])

    #use a non-X requiring background
    import matplotlib
    matplotlib.use('Agg')

if 'PBS_DEBUG' in os.environ:
    from printlocalsetup import *
    
#end
