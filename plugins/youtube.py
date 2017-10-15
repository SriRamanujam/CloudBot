import re
import time

import isodate
import requests

from cloudbot import hook
from cloudbot.util import timeformat
from cloudbot.util.formatting import pluralize


youtube_re = re.compile(r'(?:youtube.*?(?:v=|/v/)|youtu\.be/|yooouuutuuube.*?id=)([-_a-zA-Z0-9]+)', re.I)
ytpl_re = re.compile(r'(.*:)//(www.youtube.com/playlist|youtube.com/playlist)(:[0-9]+)?(.*)', re.I)

base_url = 'https://www.googleapis.com/youtube/v3/'
api_url = base_url + 'videos?part=contentDetails%2C+snippet%2C+statistics&id={}&key={}'
search_api_url = base_url + 'search?part=id&maxResults=1'
playlist_api_url = base_url + 'playlists?part=snippet%2CcontentDetails%2Cstatus'
video_url = "http://youtu.be/%s"
err_no_api = "The YouTube API is off in the Google Developers Console."


def get_video_description(video_id, prefix=None):
    json = requests.get(api_url.format(video_id, dev_key)).json()

    if json.get('error'):
        if json['error']['code'] == 403:
            return err_no_api
        else:
            return

    data = json['items']
    snippet = data[0]['snippet']
    statistics = data[0]['statistics']
    content_details = data[0]['contentDetails']

    out = '\x02{}\x02 \x034|\x03 {}'.format(prefix if prefix else "Youtube", snippet['title'])

    if not content_details.get('duration'):
        return out

    length = isodate.parse_duration(content_details['duration'])
    out += ' \x034|\x03 {}'.format(timeformat.format_time(int(length.total_seconds()), simple=True))
    total_votes = float(statistics['likeCount']) + float(statistics['dislikeCount'])

    if total_votes != 0:
        # format
        percent = 100 * float(statistics['likeCount']) / total_votes
        out += ' \x034|\x03 \x02{:.1f}%\x02 likes'.format(percent)

    if 'viewCount' in statistics:
        views = int(statistics['viewCount'])
        out += ' \x034|\x03 {:,} view{}'.format(views, "s"[views == 1:])

    uploader = snippet['channelTitle']

    upload_time = time.strptime(snippet['publishedAt'], "%Y-%m-%dT%H:%M:%S.000Z")
    out += ' \x034|\x03 Uploaded by \x02{}\x02 on {}'.format(uploader,
                                                time.strftime("%Y.%m.%d", upload_time))

    if 'contentRating' in content_details:
        out += ' \x034|\x03 \x02NSFW\x02'

    return out


@hook.on_start()
def load_key(bot):
    global dev_key
    dev_key = bot.config.get("api_keys", {}).get("google_dev_key", None)


@hook.regex(youtube_re)
def youtube_url(match, message):
    message(get_video_description(match.group(1)))


@hook.command("youtube", "you", "yt", "y")
def youtube(text):
    """youtube <query> -- Returns the first YouTube search result for <query>."""
    if not dev_key:
        return "This command requires a Google Developers Console API key."

    json = requests.get(search_api_url, params={"q": text, "key": dev_key, "type": "video"}).json()

    if json.get('error'):
        if json['error']['code'] == 403:
            return err_no_api
        else:
            return 'Error performing search.'

    if json['pageInfo']['totalResults'] == 0:
        return 'No results found.'

    video_id = json['items'][0]['id']['videoId']

    out = get_video_description(video_id, 'Youtube search result')
    out += ' \x034|\x03 https://youtube.com/watch?v={}'.format(video_id)

    return out


@hook.regex(ytpl_re)
def ytplaylist_url (match, message):
    location = match.group(4).split("=")[-1]
    json = requests.get(playlist_api_url, params={"id": location, "key": dev_key}).json()

    if json.get('error'):
        if json['error']['code'] == 403:
            return err_no_api
        else:
            return 'Error looking up playlist.'

    data = json['items']
    snippet = data[0]['snippet']
    content_details = data[0]['contentDetails']

    title = snippet['title']
    author = snippet['channelTitle']
    num_videos = int(content_details['itemCount'])
    count_videos = '\x034|\x03 {:,} video{}'.format(num_videos, "s"[num_videos == 1:])
    message("YouTube playlist \x034|\x03 \x02{}\x02 {} \x034|\x03 Created by \x02{}\x02".format(title, count_videos, author))
