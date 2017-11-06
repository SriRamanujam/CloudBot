from datetime import datetime, timezone
import re
import math
import random
import asyncio
import functools
import urllib.parse
from html.parser import HTMLParser

from sqlalchemy import Table, Column, String, DateTime, PrimaryKeyConstraint
from sqlalchemy.sql import select
from sqlalchemy.orm import mapper

import requests

from cloudbot import hook
from cloudbot.util import timeformat, formatting, database


reddit_re = re.compile(r'.*(((www\.)?reddit\.com/r|redd\.it)[^ ]+)', re.I)

base_url = "http://reddit.com/r/{}/.json"
top_url = "http://reddit.com/r/{}/top/.json?t={}"
short_url = "http://redd.it/{}"

subreddit_cache = []

table = Table(
    'reddit',
    database.metadata,
    Column('connection', String(25)),
    Column('channel', String(25)),
    Column('subreddit', String(100)),
    Column('latest', DateTime),
    PrimaryKeyConstraint('channel', 'subreddit')
)

class Reddit(object):
    def __init__(self, connection, channel, subreddit, latest):
        self.connection = connection
        self.channel = channel
        self.subreddit = subreddit
        self.latest = latest

    def __repr__(self):
        return "/r/{}, active in channel {} on connection {}, latest post at {}".format(self.subreddit, self.channel, self.connection, self.latest)

mapper(Reddit, table)

@asyncio.coroutine
@hook.periodic(120, initial_interval=120)
def check_subreddits(bot, async, db, loop):
    """
    type db: sqlalchemy.orm.Session
    """
    headers = {'User-Agent': bot.user_agent}

    for subreddit in db.query(Reddit).all():
        print("REDDIT: processing subreddit {}".format(subreddit))
        url = 'https://reddit.com/r/{}/new/.json'.format(subreddit.subreddit)
        try:
            # Again, identify with Reddit using an User Agent, otherwise get a 429
            inquiry = yield from loop.run_in_executor(None, functools.partial(requests.get, url, headers=headers))
            data = inquiry.json()
        except Exception as e:
            print("REDDIT: we couldn't do fetching: {}".format(e))
            continue
        new_posts = [item for item in data["data"]["children"] if datetime.fromtimestamp(item['data']['created_utc']) > subreddit.latest]

        print("REDDIT: new posts: {}".format(new_posts))

        if len(new_posts) > 0:
            conn = bot.connections[subreddit.connection]

            # we have new posts
            subreddit.latest = datetime.fromtimestamp(new_posts[0]['data']['created_utc'])

            print("REDDIT: printing {} posts now to channel {}....".format(len(new_posts), subreddit.channel))
            print("REDDIT: latest post is {}".format(subreddit.latest))

            for post in new_posts:
                conn.message(subreddit.channel, format_output(post['data'], prefix='New submission to \x02r/{}\x02 \x037|\x03 '.format(subreddit.subreddit)))
            db.add(subreddit)
            yield from async(db.commit)


def format_output(item, show_url=False, prefix=None):
    """ takes a reddit post and returns a formatted string"""
    item['prefix'] = prefix if prefix is not None else ''
    raw_time = datetime.fromtimestamp(int(item['created_utc']))
    item['timesince'] = timeformat.time_since(raw_time, count=1, simple=True)
    if item['is_self'] is False or show_url is True:
        item['link'] = short_url.format(item['id'])
    else:
        item['link'] = ''

    item['title'] = HTMLParser().unescape(item['title'])
    item['comments'] = formatting.pluralize(item['num_comments'], 'comment')
    item['upvotes'] = formatting.pluralize(item['score'], 'upvote')

    if item['over_18']:
        item['warning'] = ' \x037|\x03 \x02NSFW\x02'
    else:
        item['warning'] = ''

    return '{prefix}{title} by \x02u/{author}\x02 \x037|\x03 {upvotes}, {comments} \x037|\x03 Submitted {timesince} ago \x037|\x03 {link} \x037|\x03 {url}{warning}'.format(**item)


@hook.regex(reddit_re)
def reddit_url(match, bot):
    url = match.group(1)
    if "redd.it" in url:
        url = "http://" + url
        response = requests.get(url)
        url = response.url + "/.json"
    if not urllib.parse.urlparse(url).scheme:
        url = "http://" + url + "/.json"

    # the reddit API gets grumpy if we don't include headers
    headers = {'User-Agent': bot.user_agent}
    r = requests.get(url, headers=headers)
    data = r.json()
    item = data[0]["data"]["children"][0]["data"]

    return format_output(item)


@asyncio.coroutine
@hook.command('reddit', 'r', autohelp=False)
def reddit(text, bot, loop):
    """<subreddit>:[n]:<time> - for time period <time>, gets a random post from <subreddit>, or gets the [n]th post in the subreddit"""
    id_num = None
    time_period = ''
    prefix=None
    parts = []
    headers = {'User-Agent': bot.user_agent}

    if text:
        # clean and split the input
        parts = text.lower().strip().split(':')

        # find the requested post number and time period (if any)
        if len(parts) > 1:
            try:
                id_num = int(parts[1]) - 1
            except ValueError:
                return "Invalid post number."

            url = base_url.format(parts[0].strip())
            try:
                time_period = parts[2].strip()
                if time_period not in ['hour', 'day', 'week', 'month', 'year', 'all']:
                    return "Invalid time period."
                url = top_url.format(parts[0].strip(), time_period)
            except IndexError:
                pass
        else:
            url = base_url.format(parts[0].strip())
    else:
        url = "http://reddit.com/.json"

    try:
        # Again, identify with Reddit using an User Agent, otherwise get a 429
        inquiry = yield from loop.run_in_executor(None, functools.partial(requests.get, url, headers=headers))
        data = inquiry.json()
    except Exception as e:
        return "Error: " + str(e)

    # filter out stickies
    data = [item for item in data["data"]["children"] if item['data']['stickied'] is not True]

    if id_num is not None:
        try:
            item = data[id_num]["data"]
        except IndexError:
            return "Invalid post number. Number must be between 1 and {}.".format(len(data))
    else:
        item = data[0]["data"]

    if id_num is None:
        id_num = 0

    ordinal = lambda n: " %d%s" % (n,"tsnrhtdd"[(math.floor(n/10)%10!=1)*(n%10<4)*n%10::4])
    prefix = 'Top{} reddit post in \x02r/{}\x02'.format(ordinal(id_num + 1) if id_num != 0 else '', parts[0].strip())
    if time_period == 'all':
        prefix += ' of all time'
    elif time_period != '':
        prefix += ' in the past {}'.format(time_period)
    prefix += ' \x037|\x03 '

    return format_output(item, show_url=True, prefix=prefix)

