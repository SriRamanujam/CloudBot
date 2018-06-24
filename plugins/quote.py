import urllib.parse
import datetime
import random
import re
import time

import requests
from cloudbot import hook
from cloudbot.util import database

from sqlalchemy import select
from sqlalchemy import Table, DateTime, Column, String, PrimaryKeyConstraint, Text
from sqlalchemy.orm import mapper
import sqlalchemy.sql

table = Table(
    'quote',
    database.metadata,
    Column('chan', String(25)),
    Column('add_nick', String(25)),
    Column('msg', Text),
    Column('time', DateTime),
    PrimaryKeyConstraint('chan', 'msg')
)

class Quote(object):
    def __init__(self, chan, add_nick, msg, time):
        self.chan = chan
        self.add_nick = add_nick
        self.msg = msg
        self.time = time

    def __repr__(self):
        return "Quote by {}, added by {} at {}: {}".format(self.chan, self.add_nick, self.time, self.msg)


mapper(Quote, table)

@hook.command('qadd')
def qadd(text, nick, chan, db, notice):
    db.add(Quote(chan, nick, text, sqlalchemy.sql.func.now()))
    db.commit()
    num_quotes = db.query(Quote).filter(Quote.chan==chan).count()
    notice("Quote {} added!".format(num_quotes))


@hook.command('qlist', autohelp=False)
def list_quotes(db, reply, chan):
    """.qlist - Gives you a link to the full quote list for this channel"""
    query = db.query(Quote).filter(Quote.chan==chan).order_by(Quote.time)
    td = datetime.datetime.now().strftime("%B %d, %Y %X")
    lines = "===================================Quote list for channel " + chan + " as of " + td + " Eastern===================================\n"

    for index, quote in enumerate(query.all()):
        lines = lines + urllib.parse.quote("Quote {} : {}".format(
                index + 1, quote.msg))

    req = requests.post('http://sprunge.us', 'sprunge={}'.format(lines))
    try:
        req.raise_for_status()
    except requests.exceptions.HTTPError:
        # try ix.io as a backup
        req = requests.post('http://ix.io', 'f:1={}'.format(lines))
        try:
            req.raise_for_status()
        except requests.exceptions.HTTPError:
            reply('Could not upload quote list. :(')
            return

    url = req.content.decode('utf-8')

    reply('Quote list: {}'.format(url))


@hook.command('q', 'quote', autohelp=False)
def quote(text, nick, chan, db, message, reply):
    """.quote [#] - fetch quote from channel."""
    query = db.query(Quote).filter(Quote.chan==chan).order_by(Quote.time) # start building query object

    sub_dict = {
        'total': query.count(),
        'qnum': None,
        'qtext': None
    }

    quotes = query.all()
    if text:
        try:
            qnum = int(text)
            # specific number quote
            sub_dict['qnum'] = qnum
            try:
                sub_dict['qtext'] = quotes[qnum - 1].msg
            except IndexError:
                reply("Quote with that number doesn't exist.")
                return
        except ValueError:
            # treat text like a search phrase
            reply("Quote searching will come along eventually, once I decide how to do it. In the meantime, use .qlist to find your quote.")
            return
    else:
        # random quote
        sub_dict['qnum'] = qnum = random.randint(0, sub_dict['total'] - 1)
        sub_dict['qtext'] = quotes[qnum].msg

    message("Quote \x02{qnum}/{total}\x02 \x02\x036|\x03\x02 {qtext}".format(**sub_dict))

