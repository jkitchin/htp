#!/usr/bin/env python

import commands
import exceptions
import os, string

class SSHerror(exceptions.Exception):
    def __init__(self,args=None):
        self.args = args
    def __str__(self):
        return string.join(self.args,'')


def ssh(cmds,
        host,
        SSH='ssh -x'):
    '''
    run cmds remotely on host

    cmds can be a single string or an iterable object that yields
    strings like a tuple, list, etc...

    host should be something like:
    beowulf.cheme.cmu.edu
    jkitchin@beowulf.cheme.cmu.edu
    '''

    SSH = 'ssh -x'
    
    # case 1. a single command is given
    if isinstance(cmds,str):
        SSHcmd = SSH + ' ' + host + ''' "%s"''' % cmds
        (status,output) = commands.getstatusoutput(SSHcmd)
        
        if status != 0:
            print
            print SSHcmd
            print
            print output
            raise SSHerror,'ssh had non-zero status. the command may not have worked'

        return status,output

    #case 2, several commands are given
    else:
        cmd = string.join(cmds,'; ')
        
        SSHcmd = SSH + ' ' + host + ''' "%s"''' % cmd
        (status,output) = commands.getstatusoutput(SSHcmd)
            
        if status != 0:
            print SSHcmd
            print
            print output
            print
            print os.strerror(status)
            raise SSHerror,'ssh had non-zero status. the command may not have worked'

        return status,output

            
    

if __name__ == '__main__':
    print ssh('ls -al','beowulf')

    print ssh(['ls','df'],'beowulf')
    

    
