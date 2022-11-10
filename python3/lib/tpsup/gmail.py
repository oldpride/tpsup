import time

import re

import sys

import smtplib, ssl, os
import tpsup.lock
from typing import List, Dict, Optional
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_mail(From:str, From_password:str, To:str, Subject:str, Body:str, CC:str = None, BCC:str = None,
              Attachments:Optional[List[Dict]]=None):
    """
    https://www.youtube.com/watch?v=Bg9r_yLk7VY&list=WL&index=56
    in particular set up google app password. see notes/google.txt

    https://realpython.com/python-send-email/#transactional-email-services
    this has example about attachments
    :return:
    """

    if Attachments:
        message = MIMEMultipart()
        message["From"] = From
        message["To"] = To
        message["Subject"] = Subject
        # message["Bcc"] = receiver_email  # Recommended for mass emails

        message.attach(MIMEText(Body, "plain"))

        for a in Attachments:
            path = a['path']

            if 'filename' in a:
                filename = a['filename']
            else:
                filename = os.path.basename(path)

            # open file in binary mode
            with open(path, 'rb') as fh:
                # Add file as application/octet-stream
                # Email client can usually download this automatically as attachment
                if 'type' in a:
                    app, format = a['type'].split('/', 2)
                    part = MIMEBase(app, format)
                else:
                    part = MIMEBase("application", "octet-stream")

                part.set_payload(fh.read())

            # Encode file in ASCII characters to send by email
            encoders.encode_base64(part)

            # Add header as key/value pair to attachment part
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {filename}",
            )

            # Add attachment to message and convert message to string
            message.attach(part)

        text = message.as_string()
    else:
        text = f"Subject: {Subject}\n\n{Body}"

    # Log in to server using secure context and send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(From, From_password)
        server.sendmail(From, To, text)

    # Dev Ed in the youtube link used the following, also works.
    #
    # server = smtplib.SMTP('smtp.gmail.com', 587)
    # server.ehlo()
    # server.starttls()
    # server.ehlo()
    #
    # server.login(From, From_password)
    #
    # server.sendmail(From, To, msg)


def main():
    """
    set up ~/.tpsup/book.csv
        key,user,encoded,commandpattern,setting,comment
        gmailtest_From,xxx,...,^/usr/bin/curl,,gmail test From
        gmailtest_pass,xxx,...,^/usr/bin/curl,,gmail test password
        gmailtest_To,xxx,...,^/usr/bin/curl,,gmail test To
    :return:
    """
    entryBook = tpsup.lock.EntryBook()
    from_addr = entryBook.get_entry_by_key('gmailtest_From')['decoded']
    password = entryBook.get_entry_by_key('gmailtest_pass')['decoded']
    to_addr = entryBook.get_entry_by_key('gmailtest_To')['decoded']

    print(f"test simple mail")
    send_mail(from_addr, password, to_addr, "test subject", "test content")
    print(f"sent from {from_addr} to {to_addr}")

    time.sleep(1)

    print(f"\ntest attachments, multiple addresses")
    attachments = [
        { 'path':f'{os.path.join(".", "csvtools_test.csv")}', 'type':'text/csv' },
        { 'path':f'{os.path.join(os.environ.get("TPSUP"), "python3", "lib", "tpsup", "csvtools_test.csv.gz")}',
          'filename':'test.gz'},
    ]


    # A nice feature of Gmail is that you can use the + sign to add any modifiers to your email address, right before
    # the @ sign. For example, mail sent to my+person1@gmail.com and my+person2@gmail.com will both arrive at
    # my@gmail.com. When testing email functionality, you can use this to emulate multiple addresses that all point
    # to the same inbox.
    to_addr_list = [ from_addr.replace('@', f'+person{i}@') for i in range(1,3)]
    to_addr = ';'.join(to_addr_list)

    send_mail(from_addr, password, to_addr, "test attachment", "test attachment", Attachments=attachments)
    print(f"sent from {from_addr} to {to_addr}")

if __name__ == '__main__':
    main()


