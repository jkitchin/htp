#!/usr/bin/env python

import commands
import os, string, sys, tempfile

def sftp2_send(filenames,
               user=None,
               remotehost=None,
               remotedir='tmp'):
    '''
    filenames is an iterable that contains files or directories to copy over
    it could be a list, 
    '''
    
    batchfile = tempfile.NamedTemporaryFile()

    d = {'batchfile':batchfile.name,
         'user':user,
         'remotehost':remotehost}

    '''
    sftp is not very clever. it will not make directories that are
    nested so if I want to copy files to a directory that does not
    exist on the remote end I have to create it and all directories
    before it that do not exist.
    '''

    dirstocreate = remotedir.split(os.sep)
 
    dirpath = ''
    for f in dirstocreate:
        dirpath = os.path.join(dirpath,f)
        batchfile.write('mkdir -p %s\n' % dirpath)
        
    batchfile.write('cd %s\n' % remotedir)
    
    if isinstance(filenames,str):
        batchfile.write('put %s\n' % filenames)
        
    else:
        for f in filenames:
             batchfile.write('put %s\n' % f)

    batchfile.flush()

    sftp2cmd = 'sftp2 -B %(batchfile)s %(user)s@%(remotehost)s' % d

    (exitstatus, output) = commands.getstatusoutput(sftp2cmd)
            
    batchfile.close()

    if os.path.exists(batchfile.name):
        os.unlink(batchfile.name)
        
    if exitstatus != 0:
        print output
        raise Exception, 'sftp2 exited with non-zero status %s ' % exitstatus


if __name__ == '__main__ ':

    sftp2(filenames='../htp/testtough')
    sftp2_send(os.listdir('.'),remotedir='tmp/test')


