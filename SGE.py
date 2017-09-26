#!/usr/bin/env python
import os,string,sys
import xml.sax
import re

from subprocess import *        

        
class Reader(xml.sax.ContentHandler):
    def __init__(self,list, name, state):
        self.list = list
        self.name = name
        self.state = state
        self.grid = {}
        xml.sax.handler.ContentHandler.__init__(self)
        'jobid priority name state queue owner slots'
        self.jobdict = Job()

        self.jobs = []

    def Read(self, string):
        xml.sax.parseString(string, self)
        
        return self.jobs
            
    def characters(self, data):
        self.data = data
            
    def endElement(self, name):
        if name == 'JB_job_number':
            self.jobdict['jobid'] = int(self.data)
        if name == 'queue_name':
            if not self.jobdict.get('queuename'):
                self.jobdict['queuename'] = self.data.split('.')[0]
        if name == 'state':
            self.jobdict['state'] = self.data
            if self.data == 'qw':
                pout = os.popen(('qstat -j %i | grep hard_queue_list'  % self.jobdict['jobid']))
                doutput = pout.readlines()
                pout.close()
                if len(doutput) > 0:
                    doutput = doutput[-1]
                    self.jobdict['queuename'] = doutput.split()[-1]
                else:
                    self.jobdict['queuename'] = None
                '''
                alternatively, this xml parser could be used.
                I think the method above is somewhat faster though.
                '''
                #print 'queued job'
                #print 'qstat -xml -j %i' % self.jobdict['jobid']
                #pout = os.popen('qstat -xml -j %i' % self.jobdict['jobid'])
                #doutput = string.join(pout.readlines(),'')
               # pout.close()

                #dreader = DetailedReader([],[],[])
                #dreader.Read(doutput)
                #self.jobdict['queuename'] = dreader.queuename
                
        if  name == 'JAT_prio':
            self.jobdict['priority'] = float(self.data)
        if name == 'JB_name':
            self.jobdict['name'] = self.data
        if name == 'slots':
            self.jobdict['slots'] = self.data
        if name == 'JB_owner':
            self.jobdict['owner'] = self.data

        if name == 'job_list':
            
            
            self.jobs.append(self.jobdict)

            self.jobdict=Job()


class DetailedReader(xml.sax.ContentHandler):
    '''
    for getting information from qstat -xml -j jobid
    '''
    
    def __init__(self,list, name, state):
        self.list = list
        self.name = name
        self.state = state
        self.grid = {}
        xml.sax.handler.ContentHandler.__init__(self)

    def Read(self, string):
        xml.sax.parseString(string, self)
        
    def characters(self, data):
        self.data = data
            
    def endElement(self, name):
        if name == 'QR_name':
            self.queuename = self.data
            exit


class SunGridEngine:
    '''
    holds a list of dictionaries for each job in the queue
    '''
    def __init__(self):
        
        self.poll()
        
    def __str__(self):
        s = []
        s.append('jobid  priority       Jobname      status  owner  slots   Queue')
        s.append('=======================================================================')
        for job in self.jobs:
            s.append('%(jobid)6i %(priority)5.2f %(name)23.20s %(state)2s %(owner)10s %(slots)2s   %(queuename)10.15s' % job)

        return string.join(s,'\n')

    def __len__(self):
        return len(self.jobs)
    
    def poll(self):
        'refresh the list of jobs'
        pout = os.popen('qstat -xml')
        output = string.join(pout.readlines(),'')
        pout.close()
        reader = Reader([],[],[])
        self.jobs = reader.Read(output)

    def kill(self,jobid):
        pout = os.popen('qdel %i' % jobid)
        print pout.readlines()
        pout.close()
        
        
    def FindJobs(self,**kwargs):
        '''
        sge.FindJobs(owner='kitchin')
        
        name, jobid, owner, slots, state, queuename
        '''

        foundjobs = []
        #now look through all the jobs
        for job in self.jobs:
            #for each job, make sure all the keys match
            # assume it matches
            match = True
            for key in kwargs.keys():
                if job[key] != kwargs[key]:
                    match = False
            #now if you get here and match = true, then it is a job you
            #are looking for.
            if match:
                foundjobs.append(job)

        return foundjobs

    def findjobs(self,**kwargs):
        return self.FindJobs(**kwargs)


    
    def Submit(self,jobtosubmit):
        '''
        jobtosubmit can be a script, which will be submitted directly

        '''

        if os.path.exists(jobtosubmit):
            '''
            submit the file as is.

            i am using this new subprocess module. it seems
            to prevent the defunct qsub zombies i was getting
            with the popen2 method.
            '''            

            p  = Popen(['qsub',jobtosubmit],
                       stdin=PIPE,
                       stdout=PIPE,
                       close_fds=True,
                       cwd=os.getcwd())

            joboutput,jobinput = p.communicate()
            status = p.wait()

            #pin,pout = os.popen2('qsub %s' % jobtosubmit)
            #pin.close()
            #joboutput = pout.readlines()
            #pout.close()
            
            if len(joboutput) < 1:
                print 'Probably something is wrong'
                print joboutput
                jobid = None
            else:
                #get the jobid
                print joboutput
                jobidre = re.compile('\d+')
                m = jobidre.search(joboutput)
                jobid = m.group()
            
        # if it was not a file, then it must be a string of commands
        # assume that the header is already in the script
        else:
            p  = Popen(['qsub'],
                       stdin=PIPE,
                       stdout=PIPE,
                       close_fds=True,
                       cwd=os.getcwd())

            joboutput,jobinput = p.communicate(jobtosubmit)
            status = p.wait()
                                     
            #pin,pout = os.popen2('qsub')
            #pin.writelines(jobtosubmit)
            #pin.close()
            #joboutput = pout.readlines()
            #pout.close()
            
            if len(joboutput) < 1:
                print 'Probably something is wrong'
                print joboutput
                jobid = None
            else:
                #get the jobid
                jobidre = re.compile('\d+')
                m = jobidre.search(joboutput)
                jobid = m.group()

                if jobid is not None:
                    f = open('sge.%i.script' % int(jobid),'w')
                    f.writelines(jobtosubmit)
                    f.close()

        if jobid is not None:
            self.poll()

        return jobid

    def submit(self,jobtosubmit):
        return self.Submit(jobtosubmit)
                    

class Job(dict):
    def __init__(self):
        dict.__init__(self)

    def __str__(self):
        s = ['']
        s.append('jobid     = %(jobid)i' % self)
        s.append('priority  = %(priority)f' % self)
        s.append('name      = %(name)s' % self)
        s.append('state     = %(state)s' % self)
        s.append('owner     = %(owner)s' % self)
        s.append('slots     = %(slots)s' % self)
        s.append('queuename = %(queuename)s' % self)
        return string.join(s,'\n')

if __name__ == '__main__':

    sge = SunGridEngine()

    #print sge
    #print len(sge.jobs)

    for job in sge.FindJobs(owner='kitchin'): print job

    print len(sge.FindJobs(owner='kitchin'))
    
    #print sge.Submit('test.sh')

    #for job in sge.FindJobs(owner='kitchin'): print job

    script = '''#!/bin/tcsh
#$ -cwd 
#$ -j y 
#$ -notify 
#$ -m ae 
#$ -N test
#$ -V 
#$ -q crasp8 

sleep 55 

# end'''

    print  sge.Submit(script)
    sge.kill(27981)
##    print len(sge)

##    print 'crud' ,sge.Submit('jtkdaj')
