import os
import re
import base64
import datetime
import logging
import asyncio

from requests import get
from http import HTTPStatus

from django.conf import settings
from django.utils import timezone
from manager.models import iptvChannel, iptvGroup, iptvIcon

__playlist_dir__ = f'{settings.STATIC_ROOT}/playlists'
__upstream_playlist_dir__ = f'{__playlist_dir__}/upstream'
if not (os.path.isdir(__upstream_playlist_dir__)):
    if not (os.path.isdir(__playlist_dir__)):
        os.mkdir(__playlist_dir__)
    os.mkdir(__upstream_playlist_dir__)

logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
logger = logging.getLogger(__name__)

class UpstreamPlaylistHelper():
    playlist = None
    playlist_name = ''
    playlist_filename = ''
    playlist_filepath = ''
    playlist_filepath_filtered = ''

    name_re = re.compile(r'#[\s\S]*?\",([\s\S]*?)\n')
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
        with open(self.playlist_filepath, 'r') as playlist:
            content = playlist.read()

        for channel_filter in self.playlist.group_filter.split(sep='\n'):
            logger.info(f'UPSTREAM {self.playlist.name}: Filtering out group "{channel_filter}"')
            channel_filter = re.escape(channel_filter.rstrip('\r'))
            content = re.sub(rf'#EXTINF.*group-title=\"{channel_filter}\".*\n.*(\n|\Z)', '', content, flags=0)

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
        if self.playlist.group_filter:
            logger.info(f'UPSTREAM {self.playlist.name}: Importing filtered playlist')
            fpath = self.playlist_filepath_filtered
        else:
            logger.info(f'UPSTREAM {self.playlist.name}: Importing unfiltered playlist')
            fpath = self.playlist_filepath
        with open(fpath, 'r') as playlist:
            content = playlist.readline()  # Read/remove header line
            while True:
                channel_meta = playlist.readline()
                url = playlist.readline().rstrip()
                if not channel_meta:
                    break  # EOF
                name = self.name_re.search(channel_meta)[1]
                logo = self.logo_re.search(channel_meta)[1]
                group = self.group_re.search(channel_meta)[1]
                tvg_name = self.tvg_name_re.search(channel_meta)[1]
                tvg_id = self.tvg_id_re.search(channel_meta)[1]
                fk_group, created = iptvGroup.objects.update_or_create(name=group)
                if logo != '':
                    logger.info(f'UPSTREAM {self.playlist.name}: Importing logo "{logo}"')
                    fk_logo, created = iptvIcon.objects.update_or_create(url=logo)
                    logger.info(f'UPSTREAM {self.playlist.name}: Importing channel "{name}"')
                    asyncio.run(
                        iptvChannel.objects.aupdate_or_create(name=name, defaults={'url':url, 'tvg_id':tvg_id, 'tvg_name':tvg_name,'tvg_logo':fk_logo, 'group_title':fk_group}))
                else:
                    logger.info(f'UPSTREAM {self.playlist.name}: Importing channel "{name}"')
                    asyncio.run(
                        iptvChannel.objects.aupdate_or_create(name=name, url=url, tvg_id=tvg_id, tvg_name=tvg_name,
                                                              group_title=fk_group))

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
            logger.info(
                f'UPSTREAM {self.playlist.name}: Last import was {self.playlist.last_update} (age: {age}), interval: {self.playlist_update_interval}, importing...')
            self.import_channels()
            self.playlist.last_update = timezone.datetime.now()
        else:
            logger.info(
                f'UPSTREAM {self.playlist.name}: Last import was {self.playlist.last_update} ({age / 60 / 60}h ago), interval: {self.playlist_update_interval}, skipped...')
        self.playlist.save()
