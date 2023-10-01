import os
import re
import base64
import datetime
import logging
import asyncio

from requests import get
from http import HTTPStatus
from urllib.parse import urlparse

from django.conf import settings
from django.utils import timezone
from manager.models import iptvChannel, iptvGroup, iptvIcon

__playlist_dir__ = f'{settings.STATIC_ROOT}/playlists'
__upstream_playlist_dir__ = f'{__playlist_dir__}/upstream'
if not (os.path.isdir(__upstream_playlist_dir__)):
    if not (os.path.isdir(__playlist_dir__)):
        os.mkdir(__playlist_dir__)
    os.mkdir(__upstream_playlist_dir__)

logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=settings.LOGLEVEL)
logger = logging.getLogger(__name__)

class UpstreamPlaylistHelper():
    playlist = None
    playlist_name = ''
    playlist_filename = ''
    playlist_filepath = ''
    playlist_filepath_filtered = ''

    name_re = re.compile(r'#[\s\S]+\",(.*)\n')
    logo_re = re.compile(r'tvg-logo=\"([\S]*)\"')
    group_re = re.compile(r'group-title=\"([\S\s]*?)\"')
    tvg_id_re = re.compile(r'tvg-id=\"([\S\s]*?)\"')
    tvg_name_re = re.compile(r'tvg-name=\"([\S\s]*?)\"')

    def __init__(self, playlist):
        self.playlist = playlist
        self.playlist_name = playlist.name
        self.playlist_update_interval = playlist.update_interval
        self.playlist_filename = base64.b64encode(playlist.name.encode('utf-8')).decode('utf-8')
        self.playlist_filepath = f'{__upstream_playlist_dir__}/{self.playlist_filename}.m3u'
        self.playlist_filepath_filtered = f'{__upstream_playlist_dir__}/{self.playlist_filename}_filtered.m3u'

    def download_upstream_playlist(self):
        logger.info(f'UPSTREAM {self.playlist.name}: Downloading upstream playlist')
        headers = {
            "User-Agent": self.playlist.user_agent.ua_string,
            "Accept": '*/*',
            "Connection": 'close'
        }

        response = get(self.playlist.path, headers=headers, timeout=settings.PLAYLIST_TIMEOUT)
        if response.status_code != HTTPStatus.OK:
            raise Exception(
                f"UPSTREAM {self.playlist.name}: While getting response from {self.playlist.path}: {response.text}\n")

        logger.info(f"UPSTREAM {self.playlist.name}: Received playlist")
        content = response.text
        logger.info(f"UPSTREAM {self.playlist.name}: Saving playlist")

        try:
            os.makedirs(os.path.dirname(self.playlist_filepath), exist_ok=True)
            with open(self.playlist_filepath, "w") as output:
                output.write(content)
                logger.info(f"UPSTREAM {self.playlist.name}: Wrote unfiltered {self.playlist_name}")
        except Exception as err:
            raise Exception(
                f"UPSTREAM {self.playlist.name}: Could not write output file/directory self.playlist_filepath: {err}\n")

    def filter_channels(self):
        logger.info(f'UPSTREAM {self.playlist.name}: Filtering channels')
        content = ''
        with open(self.playlist_filepath, 'r') as playlist:
            content = playlist.read()

        for channel_filter in self.playlist.group_filter.splitlines():
            logger.info(f'UPSTREAM {self.playlist.name}: Filtering out group "{channel_filter}"')
            channel_filter = re.escape(channel_filter.strip())
            content = re.sub(rf'#EXTINF.*group-title="{channel_filter}".*\n.*(\n|\Z)', '', content,flags=re.UNICODE)

        try:
            os.makedirs(os.path.dirname(self.playlist_filepath), exist_ok=True)
            with open(self.playlist_filepath_filtered, 'w') as output:
                output.write(content)
                logger.info(
                    f'UPSTREAM {self.playlist.name}: Wrote filtered playlist "{self.playlist_filepath_filtered}"')
        except Exception as err:
            raise Exception(
                "UPSTREAM {self.playlist.name}: Could not write output file/directory \"{self.playlist_filepath_filtered}\", error:\n{err}")

    def import_channels(self):
        logger.info(f'UPSTREAM {self.playlist.name}: Importing channels and logos...')
        if self.playlist.group_filter != '' :
            logger.info(f'UPSTREAM {self.playlist.name}: Importing filtered playlist')
            fpath = self.playlist_filepath_filtered
        else:
            logger.info(f'UPSTREAM {self.playlist.name}: Importing unfiltered playlist')
            fpath = self.playlist_filepath

        with open(fpath, 'r') as playlist:
            # Remove headers
            content = ''
            pos = None
            while not content.startswith('#EXTINF:'):
                pos = playlist.tell()
                content = playlist.readline()
            playlist.seek(pos)

            while True:
                channel_meta = playlist.readline()
                channel_extra = ''
                if not channel_meta:
                    break  # EOF
                while not channel_meta.startswith('#EXTINF:'):
                    logger.warning(f'UPSTREAM {self.playlist.name}: Unrecognized channel metadata "{channel_meta}"')
                    # TODO: Utilize tag info
                    channel_extra = channel_extra + '\n' + channel_meta
                    channel_meta = playlist.readline()

                url = playlist.readline().rstrip()
                while url.startswith('#'): # Skip other headers
                    logger.warning(f'UPSTREAM {self.playlist.name}: Unrecognized channel tag "{url}"')
                    channel_extra = channel_extra + '\n' + url
                    url = playlist.readline().rstrip()

                name = self.name_re.search(channel_meta)
                if name is not None:
                    name = name[1]
                else:
                    logger.warning(f'UPSTREAM {self.playlist.name}: Channel name not found for url "{url}"')
                    name = '<UNKNOWN>'

                tmp = self.logo_re.search(channel_meta)
                if tmp is not None:
                    logo = tmp[1]
                else:
                    logo = None

                tmp = self.group_re.search(channel_meta)
                if tmp is not None:
                    group = tmp[1]
                else:
                    group = '<NONE>'

                tmp = self.tvg_name_re.search(channel_meta)
                if tmp is not None:
                    tvg_name = tmp[1]
                else:
                    tvg_name = None

                tmp = self.tvg_id_re.search(channel_meta)
                if tmp is not None:
                    tvg_id = tmp[1]
                else:
                    tvg_id = None

                # TODO: Make sure group and icon creation finishes before channel creation!
                #fk_group, created = iptvGroup.objects.update_or_create(name=group, upstream=self.playlist)
                fk_group, created = asyncio.run(iptvGroup.objects.aupdate_or_create(name=group, upstream=self.playlist))
                if logo is not None and logo != '':
                    logger.info(f'UPSTREAM {self.playlist.name}: Importing logo "{logo}"')
                    #fk_logo, created = iptvIcon.objects.update_or_create(url=logo)
                    fk_logo, created = asyncio.run(iptvIcon.objects.aupdate_or_create(url=logo))
                else:
                    fk_logo = None

                logger.info(f'UPSTREAM {self.playlist.name}: Importing channel "{name}"')

                # Keep enabled status upon re-import/update
                if iptvChannel.objects.filter(name=name, url=url, group_title=fk_group, upstream=self.playlist, extra_info=channel_extra).exists():
                    create_enabled = iptvChannel.objects.get(name=name, url=url, group_title=fk_group, upstream=self.playlist, extra_info=channel_extra).enabled
                else:
                    parsed_url = urlparse(url)

                    ALLOWED_URL_SCHEMES = settings.ALLOWED_URL_SCHEMES
                    if not isinstance(ALLOWED_URL_SCHEMES, list):
                        ALLOWED_URL_SCHEMES = eval(settings.ALLOWED_URL_SCHEMES)
                    matched_allowed_scheme = parsed_url.scheme in ALLOWED_URL_SCHEMES
                    if not matched_allowed_scheme:
                        logger.warning(f'UPSTREAM: {self.playlist.name}: Disabling channel "{name}" by default due to a channel scheme filter')

                    BLOCKED_URL_REGEXS = settings.BLOCKED_URL_REGEXS
                    if not isinstance(BLOCKED_URL_REGEXS, list):
                        BLOCKED_URL_REGEXS = eval(settings.BLOCKED_URL_REGEXS)
                    matched_blocked_regex = any(re.compile(regex.strip()).match(url) for regex in BLOCKED_URL_REGEXS)
                    if matched_blocked_regex:
                        logger.warning(f'UPSTREAM: {self.playlist.name}: Disabling channel "{name}" by default due to a channel regex filter')

                    BLOCKED_PATH_TYPES = settings.BLOCKED_PATH_TYPES
                    if not isinstance(BLOCKED_PATH_TYPES, list):
                        BLOCKED_PATH_TYPES = eval(settings.BLOCKED_PATH_TYPES)
                    matched_blocked_type = any(parsed_url.path.endswith(s) for s in BLOCKED_PATH_TYPES)
                    if matched_blocked_type:
                        logger.warning(f'UPSTREAM: {self.playlist.name}: Disabling channel "{name}" by default due to a channel type filter')

                    create_enabled = (matched_allowed_scheme) and not (matched_blocked_type) and not (matched_blocked_regex) # Set disabled for possibly redirected channels

                asyncio.run(iptvChannel.objects.aupdate_or_create(name=name, url=url, upstream=self.playlist, tvg_id=tvg_id, tvg_name=tvg_name, tvg_logo=fk_logo, group_title=fk_group, extra_info=channel_extra, defaults={'enabled':create_enabled}))
                #iptvChannel.objects.update_or_create(name=name, url=url, upstream=self.playlist, tvg_id=tvg_id, tvg_name=tvg_name, tvg_logo=fk_logo, group_title=fk_group, extra_info=channel_extra, defaults={'enabled':create_enabled})

    def get_playlist(self):
        logger.info(f'UPSTREAM: Getting: {self.playlist_name}')
        # TODO: Check time and redownload only if forced or after time
        with open(self.playlist_filepath, 'r') as input:
            content = input.read()
        return content

    def get_playlist_filtered(self):
        logger.info(f'UPSTREAM: Getting: {self.playlist_name}')
        # TODO: Check time and redownload only if forced or after time
        with open(self.playlist_filepath_filtered, 'r') as input:
            content = input.read()
        return content

    def delete_file(self):
        if os.path.exists(self.playlist_filepath):
            os.unlink(self.playlist_filepath)
            logger.info(f'UPSTREAM {self.playlist.name}: Upstream playlist deleted')
        else:
            logger.info(f'UPSTREAM {self.playlist.name}: Upstream playlist does not exist')

    def delete_filtered_file(self):
        logger.info(f'UPSTREAM {self.playlist.name}: Received delete filtered file request')
        if os.path.exists(self.playlist_filepath_filtered):
            os.unlink(self.playlist_filepath_filtered)
            logger.info(f'UPSTREAM {self.playlist.name}: Filtered upstream playlist deleted')
        else:
            logger.info(f'UPSTREAM {self.playlist.name}: Filtered upstream playlist does not exist')

    def delete_playlist(self):
        logger.info(f'UPSTREAM {self.playlist.name}: Received delete request')
        self.delete_file()
        self.delete_filtered_file()

    def update_upstream_playlist(self):
        """
        Downloads the m3u / loads the m3u and adds channels, icons and groups into db
        """
        logger.info(f'UPSTREAM {self.playlist.name}: Upstream playlist update requested')
        if not self.playlist.is_local:
            # Check age of existing playlist to determine if download is necessary
            if os.path.exists(self.playlist_filepath):
                logger.info(f'UPSTREAM {self.playlist.name}: File already exists, checking if download is required...')
                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(self.playlist_filepath))
                now = datetime.datetime.now()
                age = now - mod_time
                if (age.seconds / 60 / 60) < self.playlist_update_interval:
                    logger.info(
                        f'UPSTREAM {self.playlist.name}: File is {age.seconds / 60 / 60} hours old, download skipped...')
                else:
                    logger.info(
                        f'UPSTREAM {self.playlist.name}: File is {age.seconds / 60 / 60} hours old, download required...')
                    self.download_upstream_playlist()
            else:
                logger.info(f'UPSTREAM {self.playlist.name}: File does not exist, downloading...')
                self.download_upstream_playlist()

        if self.playlist.group_filter:
            self.filter_channels()

        if self.playlist.last_update:
            logger.info(f'UPSTREAM {self.playlist_name}: Playlist\'s last import was {self.playlist.last_update}')
            last_update = self.playlist.last_update
        else:
            logger.warning('UPSTREAM {self.playlist_name}: Playlist has not been imported before')
            last_update = timezone.now() - timezone.timedelta(days=365)  # initially assume 1 year old data
        now = timezone.now()
        #mod_time = timezone.datetime.fromtimestamp(os.path.getmtime(self.playlist_filepath))

        age = now - last_update

        if age > timezone.timedelta(
                hours=self.playlist_update_interval):  # TODO OR if the playlist object has been altered after the file, e.g. filters removed, last_change > mod_time
            logger.info(f'UPSTREAM {self.playlist.name}: Last import was {self.playlist.last_update} (age: {age}), interval: {self.playlist_update_interval}, importing...')
            self.import_channels()
            self.playlist.last_update = timezone.datetime.now()
        else:
            logger.info(f'UPSTREAM {self.playlist.name}: Last import was {self.playlist.last_update} ({age / 60 / 60}h ago), interval: {self.playlist_update_interval}, skipped...')
        self.playlist.save()