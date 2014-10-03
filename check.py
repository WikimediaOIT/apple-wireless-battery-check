#!/usr/bin/python

"""
Simple python script to be run as a cron job to check battery levels of apple
bluetooth wireless keyboard and trackpads.

If the battery level is below a threshold, the program will send an email
(for example to a ticketing system) to alert that new batteries will soon be needed.
You must specify the delivery address and a smtp relay server for mail to work.

A lockfile is used to keep the program from agressively spamming the email account.
(default is to only send one email per 12 hours)

Wriiten By Consuelo Jimenez and Joel Krauska for the Wikimedia Foundation 2014

"""

import datetime
import time
import socket
import sys

import argparse

import subprocess
import smtplib
from email.mime.text import MIMEText

import os

# Parse command line options
parser = argparse.ArgumentParser(description="Blutetooth Battery Level Checker")
parser.add_argument('-e', '--email',
    help='Email address to send alert from and to')
parser.add_argument('-s', '--server',
    help='Email Relay Server (must be able to relay email)')
args = parser.parse_args()

# Warn if email settings are not set
if args.email is None or args.server is None:
    print 'WARNING: Email address and/or Email relay server not given - no email will be sent'
    args.email='bogus@example.com'
    args.server='mailrelay.example.com'
    parser.print_help()

# Send email when below this threshold
threshold_level = 40

# Apple device names
devicelist=[
    'AppleBluetoothHIDKeyboard',
    'BNBTrackpadDevice'
]

# Global variables
# By default, do NOT send an email
sendemail=False
mytext = ""

# Locking file to keep the program from sending an email alert every time it runs
lockfile = '/tmp/BatteryPercentage.lock'
holddown = 12 # hours to hold the lock

# For logging purposes
now      = datetime.datetime.now()
hostname = socket.gethostname()

# The MEAT
# Run this command to get output containing battery percentage tag of keyboard
#  eg.
#  ioreg -c AppleBluetoothHIDKeyboard


# Read output from ioreg
count=0
for device in devicelist:
    # Run command and capture output
    cmd = ['/usr/sbin/ioreg', '-c', device ]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
    out,err = p.communicate()

    # Parse output
    for line in out.split('\n'):

        # We only care about 'short' lines with 'BatteryPercent'
        if 'BatteryPercent' in line and len(line)<80:
            count+=1
            junk,percent=line.split('=')

            # Pretty output for a logfile
            print '%s - %s -  Battery Level -  %s - %s%%' % (now, hostname, device, int(percent))

            # Only send email when below threshold
            if int(percent) < threshold_level:
                print 'Below threshold!'
                sendemail=True
                mytext += "WARNING: Battery Level: %s\t%s%% -- under %s%% <br>" % (device, int(percent), threshold_level)

# Extra logging to show total devices founds
print '%s - %s -  Battery Level -  Devices Detected: %s' % (now, hostname, count)


# Only send mail if we need to and there's no recent lockfile
if sendemail:
    # Check to see if there's a lockfile
    if os.path.isfile(lockfile):
        # Check how old it is?
        st=os.stat(lockfile)
        modifiedtime=st.st_mtime

        # if it was modified less than 12 hours ago (60seconds * 60 minutes * holddown hours)
        if time.time() - modifiedtime > (60 * 60 * holddown):

            # rewrite to the lockfile to reset the modified time
            file = open(lockfile, "w")
            file.write("I am a lockfile to keep the BatteryPercentage app from sending too many emails!\n")
            file.close()
        else:
            # do nothing, because lockfile is still 'fresh'
            print 'Lockfile still fresh - exiting'
            sys.exit(1)
    else:
        # make a lockfile, it doens't exist yet...
        file = open(lockfile, "w")
        file.write("I am a lockfile to keep the BatteryPercentage app from sending too many emails!\n")
        file.close()

    print 'Sending email'

    # Build email structure
    sender    = args.email
    recipient = sender
    subject   = 'Bluetooth Battery Level Warning - Host:%s' % (hostname)

    headers = ["From: " + sender,
               "Subject: " + subject,
               "To: " + recipient,
               "mime-version: 1.0",
               "content-type: text/html"]
    headers = "\r\n".join(headers)
    headers += "\r\n\r\n"

    # Send the mail
    session = smtplib.SMTP(args.server)
    session.ehlo()
    session.sendmail(sender, recipient, headers + mytext)
    session.quit()


sys.exit()
