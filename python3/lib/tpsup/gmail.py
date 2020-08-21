import smtplib
import tpsup.lock


def send_mail(From:str, From_password:str, To:str, Subject:str, Body:str):
    """
    https://www.youtube.com/watch?v=Bg9r_yLk7VY&list=WL&index=56
    :return:
    """

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.ehlo()

    server.login(From, From_password)

    msg = f"Subject: {Subject}\n\n{Body}"

    server.sendmail(From, To, msg)


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

    send_mail(from_addr, password, to_addr, "test subject", "test content")

    print(f"sent from {from_addr} to {to_addr}")


if __name__ == '__main__':
    main()


