#!/usr/bin/env python

import commands
import exceptions
import os, string

class RSYNCerror(exceptions.Exception):
    def __init__(self,args=None):
        self.args = args
    def __str__(self):
        return string.join(self.args,'')
        
def rsync(src,
          dest,
          RSYNC='rsync -avz -e "ssh2 -x"'):
    '''
    src is a filename or an iterable object that yields filenames
    (e.g. a list, or tuple, or other iterable. These files will be
    copied to dest
    '''

    # case 1. a single filename is given
    if isinstance(src,str):
        RSYNCcmd = RSYNC + ' ' + src + ' ' + dest
        
        (status,output) = commands.getstatusoutput(RSYNCcmd)
        if status != 0:
            print RSYNCcmd
            print
            print output
            print
            print os.strerror(status)
            raise RSYNCerror, 'rsync exited with non-zero status.'

    # multiple filenames are given
    else:
        files = string.join(src, ' ')
        
        RSYNCcmd = RSYNC + ' ' + files + ' ' + dest

        (status,output) = commands.getstatusoutput(RSYNCcmd)
        if status != 0:
            print RSYNCcmd
            print
            print output
            print
            print os.strerror(status)
            raise RSYNCerror, 'rsync exited with non-zero status.'

    # everything worked, so return 0 for success
    return (status,output)
        


if __name__ == '__main__':

    print rsync('mycron','jkitchin@beowulf.cheme.cmu.edu:tmp/')
    
    print rsync(['mycron','sftp2.py'],'jkitchin@beowulf.cheme.cmu.edu:tmp/')
    
    print rsync(('mycron','sftp2.py'),'jkitchin@beowulf.cheme.cmu.edu:tmp/')
