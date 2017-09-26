#!/usr/bin/env python

'''
module for modifying crontab entries

minute   hour   day of month   month   day of week   command
*        *      *              *       *             echo hello world!

       @reboot    :    Run once, at startup.
       @yearly    :    Run once a year, ie.  "0 0 1 1 *".
       @annually  :    Run once a year, ie.  "0 0 1 1 *".
       @monthly   :    Run once a month, ie. "0 0 1 * *".
       @weekly    :    Run once a week, ie.  "0 0 * * 0".
       @daily     :    Run once a day, ie.   "0 0 * * *".
       @hourly    :    Run once an hour, ie. "0 * * * *".


       # use /bin/sh to run commands, no matter what /etc/passwd says
       SHELL=/bin/sh
       # mail any output to ~paul~, no matter whose crontab this is
       MAILTO=paul
       #
       # run five minutes after midnight, every day
       5 0 * * *       $HOME/bin/daily.job >> $HOME/tmp/out 2>&1
       # run at 2:15pm on the first of every month -- output mailed to paul
       15 14 1 * *     $HOME/bin/monthly
       # run at 10 pm on weekdays, annoy Joe
       0 22 * * 1-5   mail -s "It~s 10pm" joe%Joe,%%Where are your kids?%
       23 0-23/2 * * * echo "run 23 minutes after midn, 2am, 4am ..., everyday"
       5 4 * * sun     echo "run at 5 after 4 every sunday"

*     *   *   *    *  command to be executed
-     -    -    -    -
|     |     |     |     |
|     |     |     |     +----- day of week (0 - 6) (Sunday=0)
|     |     |     +------- month (1 - 12)
|     |     +--------- day of month (1 - 31)
|     +----------- hour (0 - 23)
+------------- min (0 - 59)

min  	hour  	day/month  	month  	day/week  	 Execution time
30 	0 	1 	1,6,12 	* 	-- 00:30 Hrs  on 1st of Jan, June & Dec.

0 	20 	* 	10 	1-5 	--8.00 PM every weekday (Mon-Fri) only in Oct.

0 	0 	1,10,15 	* 	* 	-- midnight on 1st ,10th & 15th of month

5,10 	0 	10 	* 	1 	-- At 12.05,12.10 every Monday & on 10th of every month


can also be used at the command line
see crontab.py -h for help

'''

import os
import string
from subprocess import *
import tempfile
import warnings

STAR = '*'
REBOOT = '@reboot'
YEARLY = '@yearly'
ANNUALLY = '@annually'
MONTHLY = '@monthly'
WEEKLY = '@weekly'
DAILY = '@daily'
HOURLY = '@hourly'

class crontab(list):

    def __init__(self):

        list.__init__(self)
                
        self.read()

        '''
        no permission to open the file directly
        and probably not portable on different cron installations
        
        f = open('/var/spool/cron/%s' % os.environ['USER'])
        for line in f:
            print line
        f.close()
        '''

    def __repr__(self):

        s = ['------------------------------------------------']
        s.append('Crontab:')
        for line in self:
            s.append(line)
        s.append('------------------------------------------------')
        return string.join(s,'\n')


    def read(self):
        '''
        read in the current crontab
        '''
        p = Popen(['crontab', '-l'],
                  stdin=PIPE,
                  stdout=PIPE,
                  close_fds=True,
                  cwd=os.getcwd())
        
        poutput,pinput = p.communicate()
        status = p.wait()

        if status == 0:

            for line in poutput.split('\n'):
                if line != '':
                    self.append(line)
        else:
            raise Exception,'Could not read the crontab file'
            

    def update(self):
        '''
        write any changes to the crontab file
        and install it.
        '''
        tf = tempfile.NamedTemporaryFile()                 
        for line in self:
            #we have to add the \n here because it is removed by the
            #split command in read
            tf.write(line + '\n')
                    
        # this is necessary to make the file contain the output before
        # I write it back out.
        tf.flush() 

        p = Popen(['crontab', tf.name],
                  stdin=PIPE,
                  stdout=PIPE,
                  close_fds=True,
                  cwd=os.getcwd())

        poutput,pinput = p.communicate()
        status = p.wait()
        tf.close() # this automatically deletes the file
        
        if status != 0:
            print 'output = '
            print poutput

            print '============'
            print 'self = '
            print self
                
            raise Exception,'Crontab update exited with non-zero status'

    def _createentry(self, **kwargs):
        '''       
        Several syntaxes are allowed:

        1. c.add(cmd='/path/to/script')
        this will run the script every minute!

        2. c.add(cmd='path/to/script',frequency='@daily')

        3. c.add(cmd='path/to/script',minutes=30)
        runs script every hour on the half hour

        4. c.add(cmd='path/to/script',hour=6,minutes=30,month=1)
        runs script at 6:30 every day in January

        5. c.add(cmd='path/to/script',hour=0,minutes=0,monthday='1,10,15')
        midnight on 1st ,10th & 15th of month

        c.add(cmd='path/to/script',hour=0,minutes='5,10',monthday=10,weekday=1)
        At 12.05,12.10 every Monday & on 10th of every month

        6. c.add(entry='*        *      *              *       *             echo hello world!')
        directly adds an entry to the crontab
        
        the following kwargs are recognized:
        frequency - should be a string like @daily, @hourly, @yearly, @reboot

        minutes = the minute field
        hour
        monthday
        month
        weekday

        any keyword not specified is set to *
        '''

        if 'entry' in kwargs:
            entry = kwargs['entry']
            
        elif 'cmd' in kwargs:
            if 'frequency' in kwargs:
                entry = '%s %s' % (kwargs['frequency'],kwargs['cmd'])
            else:
                #check for particular args, set default value to *
                d = {}
                d['cmd']=kwargs['cmd']

                for key in ['minutes','hour','monthday','month','weekday']:
                    d[key] =  kwargs.get(key,STAR)
            
                entry = '%(minutes)s %(hour)s %(monthday)s %(month)s %(weekday)s %(cmd)s' % d
        else:
            raise Exception,'You must specify a cmd or an entry'
            

        return entry

        
    def delete(self, **kwargs):
        '''
        delete all lines that match the cmd
        '''
        
        entry = self._createentry(**kwargs)

        try:
            while True:
                self.remove(entry)
                self.update()
                
        except ValueError:
            #this means there was nothing to remove
            pass
            
        
    def add(self, **kwargs):
        '''
        add a line to crontab.

        '''

        entry = self._createentry(**kwargs)

        if entry not in self:
            self.append(entry)

            self.update()
        else:
            print 'That job is already in your crontab'
        
    

if __name__ == '__main__':

    os.system('crontab mycron')
    c = crontab()
    

    c.add(cmd='ls',frequency='@hourly')


    c.add(cmd='du -hs > logfile', minutes=30)

    print c
##     print c

    c.delete(cmd='ls',frequency='@hourly')
    c.delete(cmd='du -hs > logfile', minutes=30)
    print c

    c.add(entry='30 * * * * du -hs > logfile')
    print c

    print c._createentry(cmd='path/to/script',hour=6,minutes='30-45',month=1)
##     print c._createentry('path/to/script',hour=0,minutes='5,10',monthday=10,weekday=1)

##     #23 0-23/2 * * * echo "run 23 minutes after midn, 2am, 4am ..., everyday"
##     c.add('path/to/script',minutes=23,hour='0-23/2')
##     print c
    '''
    in a script that would automatically add entries and delete
    entries I would do this:

    c = Crontab()

    #on initialization
    c.add('/path/to/script',frequency='@hourly')


    #when done
    if done:
        c.delete('/path/to/script',frequency='@hourly')
   '''
    
##     import sys
##     from optparse import OptionParser
    
##     parser = OptionParser(usage='crontab.py -a/-r --frequency=string cmd',
##                           version='0.1')
    
##     parser.add_option('-a',
##                       nargs=0,
##                       help = 'add a command or entry to your crontab')

##     parser.add_option('-r',
##                       nargs=0,
##                       help = 'delete a command to your crontab')
    
##     parser.add_option('-l',
##                       nargs=0,
##                       help = 'list your crontab')
    
##     parser.add_option('--frequency',
##                       nargs=1,
##                       help='''specify frequency. must be '@hourly', etc...''')
                      
##     options,args = parser.parse_args()
    
##     #print 'options: ', options
    
    
##     #print 'args'
##     #print args
    
##     c = crontab()
    
##     # you can not add and remove a command, only one
##     if ((options.a is not None) and (options.r is not None)):
##         raise Exception,'you can not add and remove a command, choose -a or -r'


##     if options.a is not None:
##         for cmd in args:
##             if options.frequency is None:
##                 frequency = '@hourly'
##             else:
##                 frequency = options.frequency
                
##             c.add(cmd=cmd,frequency=frequency)

##     if options.r is not None:
##         for cmd in args:
##             c.delete(entry=cmd)

##     if options.l is not None:
##         print c
        


    

      
       
