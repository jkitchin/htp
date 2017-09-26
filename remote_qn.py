#!/usr/bin/env python
'''
this script will submit a job on the remote system to run qn_relax
on a remote queue. This module works with Jacapo and ase3.

you need to have the same versions of ase and Jacapo installed locally
and remotely.

I use exceptions a lot in these modules. Basically anytime a job is
not complete, some kind of exception is raised.

Use this in a script like this:
from Jacapo import *
from htp.remote_qn import *

Jacapo.calculate = remoteQN
remoteQN.qnrelax_tags = [0,1,2]
remoteQN.qsuboptions = '-l cput=168:00:00,mem=1200mb -l nodes=3 -joe'

I am a little torn on whether this module belongs in htp or Jacapo. It
relies on many modules within htp, that do not make sense to be in
Jacapo. That is the main reason it is here right now.

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

USER = os.environ['USER']
REMOTE_HOST = 'beowulf.cheme.cmu.edu'

if REMOTE_HOST is None:
    raise Exception, 'You need to define REMOTE_HOST in remote_qn.py'

SERVER = '%s@%s' % (USER,REMOTE_HOST)

class DacapoSubmitted(exceptions.Exception):
    def __init__(self,args=None):
        self.args = args
    def __str__(self):
        return string.join(self.args,'')
                
class DacapoRunning(exceptions.Exception):
    def __init__(self,args=None):
        self.args = args
    def __str__(self):
        return string.join(self.args,'')
    
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
    
class ForcesNotConverged(exceptions.Exception):
    def __init__(self,args=None):
        self.args = args 
    def __str__(self):
        return string.join(self.args,'')
    
def Converged(atoms,fmax=0.05):
    '''
    return True if the maxforce on a free atom is less than fmax
    otherwise return False

    note: we have to be consistent with the notion of converged here
    and in the QuasiNewton dynamics. There, converged means that the
    force in any particular direction is less than fmax, NOT the rms
    force on an atom
    '''   
    calc = atoms.get_calculator()
    
    if len(atoms) == 1 and calc.status == 'finished':
        #it does not make sense to ask this question of an atom.
        # do this after checking if the atom has a force on it.
        return True

    mask = [atom.get_tag() in calc.qnrelax_tags for atom in atoms]
    atoms.set_constraint(FixAtoms(mask=mask))

    '''
    this causes a recursion error
    f = atoms.get_forces()
    maxforce = (f**2).sum(axis=1).max()
    if maxforce < fmax**2:
        calc.set_status('finished')
        return True
    else:
        return False
    '''
    
    nc = NetCDFFile(calc.get_nc(),'r')
    if 'DynamicAtomForces' in nc.variables:
        allf = nc.variables['DynamicAtomForces'][:][-1]
    else:
        allf = None
    nc.close()
    if allf is None:
        return False

    tags = atoms.get_tags()
    for i,atom in enumerate(atoms):
        if tags[i] not in calc.qnrelax_tags:
            allf[i] = [0.0, 0.0, 0.0] #set forces on frozen atoms to 0
    
    f_sqr = (allf**2).sum(axis=1)

    maxforcesqr = f_sqr.max()
    if (maxforcesqr <= fmax**2):
        calc.set_status('finished')
        return True
    else:
        print 'maxforce = ',maxforcesqr**0.5
        return False
    
def remoteQN(self,*args,**kwargs):
    '''
    this will replace the calculate method of the Jacapo Calculator
    and run a job remotely. if the job is done it copies the results
    back

    it would be nice to find a way to pass tags into this function to
    specify which atoms to relax. right now it only works on atoms
    tagged with a 1
    '''

    CWD = os.getcwd()
            
    wholencfile = self.get_nc()

    basepath,ncfile = os.path.split(wholencfile)

    atoms = Jacapo.read_atoms(wholencfile)
    self = atoms.get_calculator()
    
    if Converged(atoms):
        return True
    else:
        print 'local ncfile exists, but is not converged.'
        print 'it may be running or aborted. checking next'
            
    #the ncfile is what will be used on the remote dir, not the whole path
    NCFILE = ncfile
    basename,ext = os.path.splitext(NCFILE)

    # now, lets change into the basepath and do everything from there
    if basepath != '': #in case basepath is the cwd
        os.chdir(basepath)

    # this is the script to run on the remote node
    tagstring = string.join([str(x) for x in self.qnrelax_tags],',')
    DACAPOCMDe = 'qn_relax -t %s %s' % (tagstring,NCFILE)
    
    #scriptname for the remote job
    JOBFILE = basename + '.job_sh'
    
    job = '''\
#!/bin/tcsh

cd $PBS_O_WORKDIR

%s

#end
''' % DACAPOCMDe

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
        pbs.qsub(QSUB='qsub -j oe %s' % self.qsuboptions,
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
    
    # now check for Convergence
    atoms = Jacapo.read_atoms(NCFILE)
    self = atoms.get_calculator()
    
    if Converged(atoms):
        if __debug__:
            print 'atoms have converged'
        pass
    else:
        os.chdir(CWD)
        print ncfile
        print 'Atoms Converged = (new?)',Converged(atoms)
        raise ForcesNotConverged

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

    # now delete some nuisance files
    if os.path.exists('hessian.pickle'):
        os.unlink('hessian.pickle')

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
    

    

        

        





        





