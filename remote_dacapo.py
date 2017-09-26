#!/usr/bin/env python
'''
this script will submit a job on the remote system to run dacapo
on a remote queue. This module works with Jacapo and ase3.

you need to have the same versions of ase and Jacapo installed locally
and remotely.

I use exceptions a lot in these modules. Basically anytime a job is
not complete, some kind of exception is raised.

Use this in a script like this:
from ase import *
from ase.calculators.jacapo import *
from htp.remote_dacapo import *

Jacapo.calculate = remote_dacapo

author:: John Kitchin <jkitchin@andrew.cmu.edu>
'''

import exceptions

import commands, os, string, sys, time
from htp.torque import *
from htp.ssh import ssh
from htp.rsync import rsync

from ase import *
from ase.calculators.jacapo import *
from Scientific.IO.NetCDF import NetCDFFile
  
class DacapoAborted(exceptions.Exception):
    def __init__(self,args=None):
        self.args = args
    def __str__(self):
        return string.join(self.args,'')
    
class DacapoNotFinished(exceptions.Exception):
    def __init__(self,args=None):
        self.args = args
    def __str__(self):
        return string.join(self.args,'')
    

USER = os.environ['USER']
REMOTE_HOST = 'beowulf.cheme.cmu.edu'

if REMOTE_HOST is None:
    raise Exception, 'You need to define your REMOTE_HOST'

SERVER = '%s@%s' % (USER, REMOTE_HOST)

def remote_dacapo(self,*args,**kwargs):
    '''
    this will replace the calculate method of the Jacapo Calculator
    and run a job remotely. if the job is done it copies the results
    back
    '''

    CWD = os.getcwd()
            
    wholencfile = self.get_nc()

    basepath,ncfile = os.path.split(wholencfile)

    atoms = Jacapo.read_atoms(wholencfile)
    self = atoms.get_calculator()

    if self.get_status() == 'finished':
        return True
               
    #the ncfile is what will be used on the remote dir, not the whole path
    NCFILE = ncfile
    basename,ext = os.path.splitext(NCFILE)
    TXTFILE = basename + '.txt'

    # now, lets change into the basepath and do everything from there
    if basepath != '': #in case basepath is the cwd
        os.chdir(basepath)

    DACAPOCMDe = 'dacapo.run %s -out %s' % (NCFILE,TXTFILE)
    
    #scriptname for the remote job
    JOBFILE = basename + '.job_sh'
    
    job = '''\
#!/bin/tcsh

cd $PBS_O_WORKDIR

dacapo.run %s -out %s
stripnetcdf %s

#end
''' % (NCFILE,TXTFILE,NCFILE)

    f = open(JOBFILE,'w')
    f.write(job+'\n')
    f.close()
    os.chmod(JOBFILE,0777)

    rc = JOBFILE+'.rc'

    # get a queue object
    pbs = PBS(SERVER)

    #we try the qsub here because exceptions are raised if
    #the job has already been submitted or is running.

    try:
        #this will raise a variety of exceptions that we catch
        if hasattr(self,'qsuboptions'):
            qsuboptions = self.qsuboptions
        else:
            qsuboptions = ''
        pbs.qsub(QSUB='qsub -j oe %s' % qsuboptions,
                 jobfiles=[JOBFILE,NCFILE])
    except PBS_MemoryExceeded, e:
        # we create jobfile.rc so the job gets run with more
        # memory next time.
        #mem = int(e.mem * 1.25)
        #f = open(rc,'a')
        #f.write('QSUB_MEM = %i\n' % mem)
        #f.close()
        os.chdir(CWD)

        print 'Caught memory exception'
        #print 'next time it should run with %i kb memory' % mem
        print 'see rc: ',rc
        raise e

    except JobDone:
        # nothing here to do.
        pass
    
    except Exception,e:
        # pbs.submit can raise a lot of different exceptions
        # we need to change back to CWD, no matter what
        # and we re-raise the exception so we can see it
        os.chdir(CWD)
        print e
        raise e
    
    # now check if it finished correctly
    atoms = Jacapo.read_atoms(NCFILE)
    self = atoms.get_calculator()

    #check for dacapo errors
    TXTFILE = basename + '.txt'
    f = open(TXTFILE,'r')
    for line in f:
        if 'abort_calc' in line:
            f.close()
            raise DacapoAborted, line
        continue
    f.close()
    
    if not ('clexit: exiting the program' in line
            or 'PAR: msexit halting Master' in line):
        raise DacapoNotFinished, line

    stopfile = NCFILE + '.stop'
    if os.path.exists(stopfile):
        os.unlink(stopfile)

    runningfile =  NCFILE + '.running'
    if os.path.exists(runningfile):
        os.unlink(runningfile)

    #slave files from parallel runs
    import glob
    slvpattern = TXTFILE + '.slave*'
    for slvf in glob.glob(slvpattern):
        print 'deleting %s' % slv
        os.unlink(slvf)
        
    os.chdir(CWD)
    return 0
    

    

        

        





        





