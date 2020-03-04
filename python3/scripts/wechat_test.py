#!/usr/bin/env python3
#from __future__ import unicode_literals

import itchat
import time

print('扫一扫')
print('on linux use "display /tmp/QR.png" to pop up the QR code image')

#itchat.auto_login(hotReload=True)
itchat.auto_login()
friend_remarkName = input("please enter friend name (eg HelenFeng): ")
print(f'friend="{friend_remarkName}"')
#friend_wechatName = itchat.search_friends(remarkName=friend_remarkName)[0]['UserName']
friend_wechatName = itchat.search_friends(name=friend_remarkName)[0]['UserName']

while True:
    message = input("please enter your message: ")
    itchat.send_msg(msg=message, toUserName=friend_wechatName)
