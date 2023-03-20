import os
import logging
import base64
import re

from django.conf import settings
from manager.models import iptvUpstreamPlaylist, iptvChannel, iptvGroup

from lib.upstream_playlist_helper import UpstreamPlaylistHelper

__playlist_dir__ = f'{settings.STATIC_ROOT}/playlists'
__downstream_playlist_dir__ = f'{__playlist_dir__}/downstream'
if not (os.path.isdir(__downstream_playlist_dir__)):
    if not (os.path.isdir(__playlist_dir__)):
        os.mkdir(__playlist_dir__)
    os.mkdir(__downstream_playlist_dir__)

logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DownstreamPlaylistHelper():

    playlist = None
    playlist_name = ''
    playlist_filename = '' 
    playlist_filepath = ''
    playlist_filter = ''
    playlist_filtermode = ''
    
    def __init__(self, playlist):
        self.playlist = playlist
        self.playlist_name = playlist.name
        self.playlist_proxy_url = playlist.proxy.url
        self.playlist_proxy_port = playlist.proxy.port        
        self.playlist_filename = base64.b64encode(playlist.name.encode('utf-8')).decode('utf-8')
        self.playlist_filepath = f'{__downstream_playlist_dir__}/{self.playlist_filename}.m3u'
        self.playlist_filter = playlist.channel_filter
        self.playlist_filtermode = playlist.filter_mode

    def delete_playlist(self):
        logger.info(f'DOWNSTREAM {self.playlist.name}: Received delete request') 
        if os.path.exists(self.playlist_filepath):
            os.unlink(self.playlist_filepath)
            logger.info(f'DOWNSTREAM {self.playlist.name}: Downstream playlist deleted')
        else:
            logger.info(f'DOWNSTREAM {self.playlist.name}: Downstream playlist does not exist')

    def get_playlist(self):
        logger.info(f'DOWNSTREAM: Getting: {self.playlist_name}')   
        # TODO: Check time and redownload only if forced or after time
        self.update_downstream_playlist()
        with open(self.playlist_filepath, 'r') as input:
            content = input.read()
        return content      
        
    def update_downstream_playlist(self):
        """
        Writes a generate playlist with proxified URLs, based on selected groups
        """
        def generate_m3u_content(channels):
            logger.info(f'DOWNSTREAM: Generating playlist {self.playlist_name}') #\nChannel filters:\n{self.playlist_filter}')

            content = '#EXTM3U\n'
            for channel_group in channels:
                for channel in channel_group:
                    # TODO: Static URLs
                    logo_url_encoded = base64.b64encode(channel.tvg_logo.url.encode('utf-8')).decode('utf-8') if channel.tvg_logo else None
                    proxy_logo_url = f'{settings.MANAGEMENT_URL}:{settings.EXTERNAL_MANAGEMENT_PORT}/manager/get/icon/{logo_url_encoded}' if logo_url_encoded else ''
                    
                    channel_url_encoded = base64.b64encode(channel.url.encode('utf-8')).decode('utf-8')
                    proxy_channel_url = f'{self.playlist_proxy_url}:{self.playlist_proxy_port}/stream/start/{channel_url_encoded}'
                    content += f'#EXTINF:-1 tvg-id="{channel.tvg_id}" tvg-name="{channel.tvg_name}" tvg-logo="{proxy_logo_url}" group-title="{channel.group_title}",{channel.name}\n'
                    content += f'{proxy_channel_url}\n'

            logger.info(f'DOWNSTREAM {self.playlist.name}: Filter mode: {self.playlist_filtermode}')
            for channel_filter in self.playlist_filter.split(sep='\n'):
                if channel_filter:
                    channel_filter = re.escape(channel_filter.format(filter=channel_filter).rstrip('\r'))
                    # TODO: Find a better place for the RE
                    if self.playlist_filtermode == 'P':
                        filter_re = rf'(#EXTINF.*group-title=\".*?\",{channel_filter}.*?\n.*(\n|\Z))'
                    elif self.playlist_filtermode == 'S':
                        filter_re = rf'(#EXTINF.*group-title=\".*?\",.*?{channel_filter}\n.*(\n|\Z))'
                    elif self.playlist_filtermode == 'E':
                        filter_re = rf'(#EXTINF.*group-title=\".*?\",{channel_filter}\n.*(\n|\Z))'
                    else:
                        filter_re = rf'(#EXTINF.*group-title=\".*?\",.*?{channel_filter}.*?\n.*(\n|\Z))'

                    logger.info(f'DOWNSTREAM {self.playlist.name}: Filtering out channels matching: "{channel_filter}"')
                    content = re.sub(filter_re, '', content, flags=0)

            return content
        
        logger.info(f'DOWNSTREAM: Updating/importing all upstream playlists')
        upstreams = iptvUpstreamPlaylist.objects.all()
        for upstream in upstreams:
            helper = UpstreamPlaylistHelper(upstream)
            helper.update_upstream_playlist()
        logger.info(f'DOWNSTREAM: Updating: {self.playlist_name}')
        channels_queryset = []
        playlist_groups = self.playlist.groups.split(sep='\r\n')
        logger.info(f'DOWNSTREAM: Playlist groups: {playlist_groups}')

        for group in playlist_groups:
            logger.info(f'DOWNSTREAM: Processing group: {group}')
            try:
                group_id = iptvGroup.objects.filter(name=group, enabled=True)[0]
                # TODO: Alphabetical sorting implied for now inside of groups
                if group_id:
                    channels_queryset.append(iptvChannel.objects.filter(group_title=group_id, enabled=True).order_by('name'))
                else:
                    logger.warning(f'DOWNSTREAM: No groups to add to playlist, skipping...')
                    
                #logger.info(f'DOWNSTREAM: Channel queryset: {channels_queryset}')
            except Exception as err:
                logger.info(f'ERROR DOWNSTREAM: Probably proxy playlist "{self.playlist.name}" group "{group}" has not been imported yet: {err}')

        content = generate_m3u_content(channels_queryset)
        try:
            os.makedirs(os.path.dirname(self.playlist_filepath), exist_ok=True)
            with open(self.playlist_filepath, 'w') as output:
                output.write(content)
                logger.info(f'DOWNSTREAM: Saved as {self.playlist_filepath}')
        except Exception as err:
            raise Exception(f'ERROR DOWNSTREAM: Could not write output file/directory: {err}\n')
