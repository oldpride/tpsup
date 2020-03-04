#!/usr/bin/env python

import itchat

import time

print('扫一扫 ')

itchat.auto_login(HotReload=True)
friend_remarkName = input("please enter friend name:")
friend_wechatName = itchat.search_friends(remarkName=friend_name)[0]['UserName']


while True:
    messag=input("please enter your message: ")
    itchat.send_msg(msg=msg, toUserName=friend_wechatName)


