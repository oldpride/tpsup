#!/usr/bin/env python

# as of 2020/03/03, wechat blocked most users's web interface. itchat doesn't work anymore.

#from __future__ import unicode_literals

import itchat
import os
import pprint
import sys

from pathlib import Path
home = str(Path.home())

os.chdir(home)

print('扫一扫')
print(f'on linux use "display {home}/QR.png" to pop up the QR code image')
print(f'on windows, the image should pop up by itself. the file is at "{home}/QR.png"')

#itchat.auto_login(hotReload=True)
itchat.auto_login()

# Your wechat account may be LIMITED to log in WEB wechat, error info:
# <error><ret>1203</ret><message>为了你的帐号安全，此微信号不能登录网页微信。你可以使用Windows微信或Mac微信在电脑端登录。
# Windows微信下载地址：https://pc.weixin.qq.com  Mac微信下载地址：https://mac.weixin.qq.com</message></error>
# not working any more
# https://www.cnblogs.com/fby698/p/11515470.html

friends = itchat.get_friends()
pprint.pprint(friends)
chatrooms = itchat.get_chatrooms()
pprint.pprint(chatrooms)

sys.exit(0)

#friend_remarkName = input("please enter friend name (eg HelenFeng): ")
#print(f'friend="{friend_remarkName}"')
#friend_wechatName = itchat.search_friends(remarkName=friend_remarkName)[0]['UserName']
#friend_wechatName = itchat.search_friends(name=friend_remarkName)[0]['UserName']
# while True:
#     message = input("please enter your message: ")
#     itchat.send_msg(msg=message, toUserName=friend_wechatName)
