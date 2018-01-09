import sys
import csv
import datetime
import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import smtplib

EMAIL_TEMPLATE = "/tmp/email.html"
MAIN_CONTENT = "Please find attached the files with updated barcodes"
SUBJECT = "Updated barcode data {}".format(
            datetime.date.today().strftime("%m/%d/%Y"))

# Information for sending the email
TO = ["test@test.com"]
SMTP_SERVER = "smtp.sendmail.org:123"
FROM = "test@mailhelp.org"
PASSWORD = "supersecretsmtppassword"


def get_email_content():
    if not os.path.isfile(EMAIL_TEMPLATE):
        if not os.path.isfile("email.html"):
            print("\nError: Email template file not found.")
            return
        email_template = "email.html"
    else:
        email_template = EMAIL_TEMPLATE

    style = 'style="font-family: sans-serif; font-size: 14px; '\
            'font-weight: normal; margin: 0; Margin-bottom: 15px;"'



    with open(email_template, "r") as html:
        email_content = ''.join(html.read().split("\n"))
        email_content = re.sub(r'<MAIN_CONTENT>', MAIN_CONTENT,
                email_content)

    return email_content

def send_email(email_content, files):
    # Sends the mail using smtplib

    message = MIMEMultipart('alternative')
    message['subject'] = SUBJECT
    message['To'] = ', '.join(TO)
    message['From'] = FROM

    # Record the MIME type text/html.
    html_body = MIMEText(email_content, 'html')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    message.attach(html_body)
    for path in files:
        part = MIMEBase('application', "octet-stream")
        with open(path, 'rb') as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="{0}"'.format(os.path.basename(path)))
        message.attach(part)

    # The actual sending of the e-mail

    # try:
    server = smtplib.SMTP(SMTP_SERVER)
    server.starttls()
    server.login(FROM, PASSWORD)
    server.sendmail(FROM, TO, message.as_string())
    server.quit()
    # except:
        # return sys.exc_info()
    return 0

def get_current_day_files(filepath):
    # Returns (pickupfile, deliveryfile) tuple matching to today's date
    file_pairs = []
    today = datetime.date.today().strftime("%m%d%y")

    all_files = sorted(os.listdir(filepath))
    todays_files = filter(lambda x:
            re.match(r'.*{}.csv'.format(today), x), all_files)
    return todays_files

def replace_barcode(column):
    return [x[6:11] if column.index(x) == 3 else x for x in column]

if __name__ == "__main__":
    if len(sys.argv) == 1:
        filepath = '.'
    else:
        filepath = sys.argv[1]

    files = get_current_day_files(filepath)
    filenames = list(files)
    if not files:
        print("INFO: No file pairs matching today's date were found. No "\
                "action taken.")
        sys.exit()
    for afile in filenames:
        replaced = []
        with open(afile, 'r') as content:
            data = csv.reader(content)
            for r in data:
                replaced.append(replace_barcode(r))
        with open(afile, 'w') as csvfile:
            writer = csv.writer(csvfile)
            for each in replaced:
                writer.writerow(each)

    email_content = get_email_content()
    send_email(email_content, filenames)
