#!/usr/bin/env python

# copied from Lei Chen (Leo) and modified by me

from __future__ import unicode_literals
import itchat, logging, time, sys, json
from itchat.content import *
from logging.handlers import TimedRotatingFileHandler

logger = logging.getLogger("get_waiting_list.log")
logger.setLevel(logging.DEBUG)


# login
# itchat.auto_login()


def get_lrsg_rooms(chatrooms):
    # read group1 and group2 chatroom name
    with open('room_names.json') as f:
        lrsg_room_names = json.load(f)
    logger.debug(json.dumps(lrsg_room_names, indent=2, ensure_ascii=False).encode('utf8'))

    # find lrsg chatroom 1 and 2
    r1 = None
    r2 = None
    for room in chatrooms:
        if room['NickName'] == lrsg_room_names['r1']:
            r1 = room
            logger.debug("found r1")
            continue

        if room['NickName'] == lrsg_room_names['r2']:
            r2 = room
            logger.debug("found r2")
            continue

    if not r1 or not r2:
        logger.error(
            "Not found both lrsg room 1 and 2 in the chatroom list, try send or receive a msg in the room to have it appear in the chatroom list, r1 = %s, r2 = %s" % (
            r1, r2))
        return None
    return [r1, r2]


def get_waiting_list():
    # get live chatroom list
    chatrooms = itchat.get_chatrooms()
    logger.debug(json.dumps([room['NickName'] for room in chatrooms], indent=2, ensure_ascii=False).encode('utf8'))

    lrsg_rooms = get_lrsg_rooms(chatrooms)

    # room member list could be empty, which needs to call update_chatroom
    need_refresh = False
    for room in lrsg_rooms:
        if len(room['MemberList']) == 0:
            logger.info("room %s has empty MemberList, need to update_chatroom" % room['NickName'])
            need_refresh = True
            itchat.update_chatroom(room['UserName'])

    if need_refresh:
        logger.info("get_chatrooms again after update")
        chatrooms = itchat.get_chatrooms()
        lrsg_rooms = get_lrsg_rooms(chatrooms)

    # username is the reliable way to distinguish users
    r1_username_list = [member['UserName'] for member in lrsg_rooms[0]['MemberList']]
    logger.debug("len(r1_username_list) = %s" % (len(r1_username_list)))

    # waiting list are the members that are in r2 and not in r1
    waiting_list = [member for member in lrsg_rooms[1]['MemberList'] if member['UserName'] not in r1_username_list]
    logger.debug("len(waiting_list) = %s" % (len(waiting_list)))

    # write waiting list to a json file
    with open('waiting_list.json', 'w', encoding='utf-8') as f:
        json.dump(["%s(%s)" % (member['NickName'], member['DisplayName']) for member in waiting_list], f,
                  ensure_ascii=False, indent=2)
        logger.info("waiting list is written to waiting_list.json")
