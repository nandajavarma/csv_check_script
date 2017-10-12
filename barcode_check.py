#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os
import re
import csv
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# MAKE SURE THE FOLLOWING VALUES ARE PROPERLY CONFIGURED BEFORE RUNNING
# THE SCRIPT

# The email template file. If this is not correct it will look in the
# current directory. If it still cannot find, it will error out

EMAIL_TEMPLATE = "/tmp/email.html"

# Information for sending the email
TO = "test@test.com"
SMTP_SERVER = "smtp.sendmail.org:123"
FROM = "test@mailhelp.org"
PASSWORD = "supersecretsmtppassword"

# specify how many latest pick up-delivery file pairs should be parsed
FILE_PAIR_COUNT = 5


def get_file_path(basedir, filename):
    # Just to get the relative paths of the files
    return os.path.join(os.path.realpath(basedir), filename)

def get_pickup_delivery_file_pairs(filepath):
    # Returns lists of (pickupfile, deliveryfile) tuple
    file_pairs = []
    all_files = os.listdir(filepath)
    sorted_files = sorted(all_files, key=os.path.getctime,
                reverse=True)
    pickup_files = [f for f in sorted_files if
            re.match(r'.*pickup.*\.csv', f)]

    # Just takes into account FILE_PAIR_COUNT number of file pairs from
    # the directory
    pickup_files = pickup_files if (len(pickup_files) <
            FILE_PAIR_COUNT) else pickup_files[:FILE_PAIR_COUNT]

    for pf in pickup_files:
        pickup_reg = re.match('(\w*)pickup(\d+)\.csv', pf)
        deliv_file = pickup_reg.group(1) + 'deliv' + pickup_reg.group(2) + '.csv'
        if deliv_file not in all_files:
            print("Delivery file corresponding to {} missing".format(pf))
        else:
            file_pairs.append((get_file_path(filepath, pf),
                    get_file_path(filepath, deliv_file)))

    return file_pairs

def compare_bar_codes(files):
    # Returns the details of the picked up but not delivered items as a
    # list of lists
    missed_delivery_info = []
    (pickup_file, delivery_file) = files
    with open(pickup_file, 'r') as pickup:
        pickup_info = dict((r[2], r) for i, r in
                enumerate(csv.reader(pickup)))

    with open(delivery_file, 'r') as deliver:
        delivered_barcodes = [r[0] for i, r in enumerate(csv.reader(deliver))]


    # Creates a list of missing entries from the delivery file
    for barcode, pickedup_data in pickup_info.items():
        if barcode not in delivered_barcodes:
            missed_delivery_info.append(pickedup_data)
        else:
            delivered_barcodes.remove(barcode)

    # Creates a list of missing entries from the pickup file
    if delivered_barcodes:
        missed_pickup_info = delivered_barcodes


    return (missed_delivery_info, missed_pickup_info)

def format_missdeliv_info(info):
    #Format the missing delivery barcodes into html table format
    if not info:
        return ''

    style= "font-family: sans-serif; "\
             "font-size: 14px; vertical-align: top; padding-bottom: 15px;"
    pickup_data =  """
                   <td style="{0}">Order Number</td>
                   <td style="{0}">Route Number</td>
                   <td style="{0}">Barcode Number</td>
                   <td style="{0}">PULocation</td>
                   """.format(style)
    for each in info:
        pickup_data = pickup_data + '<tr>'
        for field in each:
            pickup_data = pickup_data + ('<td >{}</td>'.format(field))
        pickup_data = pickup_data + '</tr>'
    return pickup_data

def format_misspick_info(info):
    #Format the missing pickup barcodes into html table format
    if not info:
        return ''

    style= "align: center; font-family: sans-serif; "\
             "font-size: 14px; vertical-align: top; padding-bottom: 15px;"
    deliv_data =  """
                   <tr>
                   <td style="{}">Barcode Number</td>
                   </tr>""".format(style)
    for each in info:
        deliv_data = deliv_data + ('<tr><td style="{}">{}</td></tr>').format(style, each)
    return deliv_data


def get_email_content(missed_delinfo, missed_pickinfo):
    #Inserts the formatted pickup and delivery data to an html email template

    # If the hardcoded value for html template file is not correct it
    # will check in the current directory

    if not os.path.isfile(EMAIL_TEMPLATE):
        if not os.path.isfile("email.html"):
            print("\nError: Email template file not found.")
            return
        email_template = "email.html"

    style = 'style="font-family: sans-serif; font-size: 14px; '\
            'font-weight: normal; margin: 0; Margin-bottom: 15px;"'


    with open(email_template, "r") as html:
        email_content = ''.join(html.read().split("\n"))
        if missed_delinfo:
            warning = "<p %s>Please check all relevant cars and all tote "\
                    "bags for these barcodes. If you find something or not, "\
                    "please email info@foo.com.</p><br/>"
            msg = "<p {}>{}</p>".format(style, missed_delinfo)
            email_content = re.sub(r'<missing_deliv_info>', msg,
                    email_content)
            email_content = re.sub(r'<warning>', warning, email_content)
        else:
            msg = "<i {}>No missing barcode scans.</i>".format(style)
            email_content = re.sub(r'<missing_deliv_info>', msg,
                    email_content)
            email_content = re.sub(r'<warning>', '<br/>', email_content)

        if missed_pickinfo:
            msg = "<p {}>{}</p>".format(style, missed_pickinfo)
            email_content = re.sub(r'<missing_pickup_info>', msg,
                email_content)
        else:
            msg = "<i {}>No missing barcode scans.</i>".format(style)
            email_content = re.sub(r'<missing_pick_info>', msg,
                email_content)
    return email_content

def send_email(email_content):
    # Sends the mail using smtplib
    subject = "Missing barcode scan offs {}".format(
            datetime.date.today().strftime("%m/%d/%Y"))
    # Replace with the sender email address

    message = MIMEMultipart('alternative')
    message['subject'] = subject
    message['To'] = TO
    message['From'] = FROM

    # Record the MIME type text/html.
    html_body = MIMEText(email_content, 'html')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    message.attach(html_body)

    # The actual sending of the e-mail
    server = smtplib.SMTP(SMTP_SERVER)

    # Credentials (if needed) for sending the mail

    server.starttls()
    server.login(FROM, PASSWORD)
    server.sendmail(FROM, [TO], message.as_string())
    server.quit()

if __name__ == "__main__":
    # If the directory is not provided as cmdline arg, it runs in the
    # current dir
    if len(sys.argv) == 1:
        filepath = '.'
    else:
        # when the path is provided relative or absolute
        filepath = sys.argv[1]

    filepairs = get_pickup_delivery_file_pairs(filepath)
    missed_delinfo, missed_pickinfo = [], []

    #creates two lists containing the missing delivery and pickup
    #barcode scans
    for afile in filepairs:
        missed_info = compare_bar_codes(afile)
        missed_delinfo.extend(missed_info[0])
        missed_pickinfo.extend(missed_info[1])

    if (missed_pickinfo or missed_delinfo):
        email_content = get_email_content(format_missdeliv_info(missed_delinfo), format_misspick_info(missed_pickinfo))
        if email_content:
            send_email(email_content)
    else:
        print("No data missing from any files")
