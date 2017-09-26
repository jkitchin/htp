#!/usr/bin/env python
'''
this module will submit a job to the queue when a calculation is called.

Use this in a script like this:
from ase import *
from ase.calculators.jacapo import *
from htp.queue_dacapo import *
Jacapo.qsuboptions = '-l cput=23:00:00,mem=499mb -joe -p -1024'
Jacapo.calculation_required = calculation_required
Jacapo.calculate = queue_dacapo

author:: John Kitchin <jkitchin@andrew.cmu.edu>
'''

import exceptions

import commands, os, string, sys, time
from torque.torque import *

from ase import *
from ase.calculators.jacapo import *
  
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
    
def calculation_required(self, atoms=None, quantities=None):
    '''we need to overwrite this method so calculate always gets
    called. the calculate method will determine if a calculation is
    required.'''
    
    return True

def queue_dacapo(self,*args,**kwargs):
    '''
    this will replace the calculate method of the Jacapo Calculator
    and run a job through the queue.
    '''
    CWD = os.getcwd()

    wholencfile = self.get_nc()

    if not os.path.exists(wholencfile):
        self.write(wholencfile)

    basepath,NCFILE = os.path.split(wholencfile)
    basename,ext = os.path.splitext(NCFILE)
    TXTFILE = basename + '.txt'
    runningfile =  NCFILE + '.running'
    stopfile = NCFILE + '.stop'

    JOBFILE = basename + '.job_sh'
    JOBIDFILE = basename + '.jobid'

    if basepath != '':
        os.chdir(basepath)

    atoms = Jacapo.read_atoms(NCFILE)
    self = atoms.get_calculator()
        
    if self.get_status() == 'finished':
        #this means the job is done.
        #do some clean-up of unimportant files
        for jfile in [JOBFILE,
                      JOBIDFILE,
                      runningfile,
                      stopfile]:
            if os.path.exists(jfile):
                os.remove(jfile)
        #slave files from parallel runs
        import glob
        slvpattern = TXTFILE + '.slave*'
        for slvf in glob.glob(slvpattern):
            os.unlink(slvf)

        #exit so that we can move on.
        os.chdir(CWD)
        return True

    #Past here means we have to check if the calculation is running
    if os.path.exists(JOBIDFILE):
        JOBID = open(JOBIDFILE).readline()
    else:
        JOBID = None

    # get a queue object
    pbs = PBS() 
    pbs.fastpoll()

    if JOBID is not None:
        print JOBID
        #jobnumber,beowulf = JOBID.split('.')
        fields = JOBID.split('.')
        jobnumber = fields[0]
        print jobnumber
        
        #the job has been submitted before, and we need 
        #to find out what the status of the jobid is
        for job in pbs:

            if job['Job Id'] == jobnumber + '.gilgamesh':
                if job['job_state'] == 'R':
                    os.chdir(CWD)
                    raise JobRunning, job['job_state']
                elif job['job_state'] == 'Q':
                    os.chdir(CWD)
                    raise JobInQueue, job['job_state']
                elif  job['job_state'] == 'C':
                    os.chdir(CWD)
                    raise JobDone, job['job_state']
                else:
                    os.chdir(CWD)
                    raise UnknownJobStatus, job['job_state']
        # if you get here, the job is not in the queue anymore
        # getting here means the job was not finished, and is not in
        # the queue anymore.
        OUTPUTFILE = JOBFILE + '.o' + jobnumber
        #if os.path.exists(OUTPUTFILE):
        print open(OUTPUTFILE).readlines()


        if os.path.exists(TXTFILE): #sometimes a job may not even start and there is no txtfile
            #check output of Dacapo
            f = open(TXTFILE,'r')
            for line in f:
                if 'abort_calc' in line:
                    f.close()
                    os.chdir(CWD)
                    raise DacapoAborted, line
                continue
            f.close()

            #check last line for proper finish
            if not ('clexit: exiting the program' in line
                    or 'PAR: msexit halting Master' in line):
                os.chdir(CWD)
                raise DacapoNotFinished, line

            # something else must be wrong 
            raise Exception,'something is wrong with your job!'
        else:
            os.chdir(CWD)
            print '%s does not exist!' % TXTFILE
            raise Exception,'%s does not exist!' % TXTFILE

    #Past here, we need to submit a job.
    #check that the bands get set
    if self.get_nbands() is None:
        nelectrons = self.get_valence()
        nbands = int(nelectrons * 0.65 + 4)
        self.set_nbands(nbands)
        
    DACAPOCMDe = 'dacapo.run %s -out %s' % (NCFILE,TXTFILE)

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

    #now we know we have to submit our job
    cmd = 'qsub %s %s'  % (self.qsuboptions,JOBFILE)
    status,output = commands.getstatusoutput(cmd)

    if status == 0:
        f = open(JOBIDFILE,'w')
        f.write(output)
        f.close()
        os.chdir(CWD)
        raise JobSubmitted, output
    else:
        print status, output
        os.chdir(CWD)
        raise Exception, 'Something is wrong with the qsub output'


Jacapo.calculation_required = calculation_required
Jacapo.calculate = queue_dacapo
