#!/usr/bin/env python

import os
import smtplib
import string
'''
Mail module - contains convenience functions for sending emails from
python.
'''

def smptmail(toaddrs,
             subject=None,
             message='',
             fromaddr='',
             mailserver=None):
    '''
    toaddrs is either a string or list of email addresses

    mailserver is a string defining your mailserver hostname
    '''

    if type(toaddrs) is str:
        to = toaddrs
    else:
        to = string.join(toaddrs,',')
        
    # Add the From: and To: headers at the start!
    msg = ("From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n"
           % (fromaddr, to, subject))
    
    msg=msg+message
    server = smtplib.SMTP(MAILSERVER)
    server.set_debuglevel(0)
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()


from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders

def mail_attachment(fromaddr=None,
                    toaddrs=None,
                    subject='[mail_attachment]: ',
                    msgtext='',
                    attachment=None,
                    mailserver=None):
    '''
    attachment is a path to a file you want to attach
    '''

    for toaddr in toaddrs:
        msg = MIMEMultipart()    
        msg['From'] = fromaddr
        msg['To'] = toaddr
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = subject
	
        msg.attach(MIMEText(msgtext))
        if attachment is not None:
            part = MIMEBase('application',"octet-stream")
            part.set_payload(open(attachment,'rb').read())
            Encoders.encode_base64(part)
            part.add_header('Content-Disposition','attachment; filename = "%s"' % os.path.basename(attachment))
            msg.attach(part)
    
        server = smtplib.SMTP(mailserver)
        server.sendmail(fromaddr,toaddr,msg.as_string())
        server.quit()
	
