import os
import base64
import datetime
import logging
import re
import asyncio

from requests import get
from http import HTTPStatus

from django.conf import settings
from django.utils import timezone
from django.utils.timezone import make_aware
from manager.models import iptvIcon

__epg_dir__ = f'{settings.STATIC_ROOT}/epg'
if not (os.path.isdir(__epg_dir__)):
    os.mkdir(__epg_dir__)

logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
logger = logging.getLogger(__name__)

class EPGHelper():

    epg = None
    epg_name = ''
    epg_filename = ''
    epg_filepath = ''
    
    def __init__(self, epg):
        self.epg = epg
        self.epg_name = epg.name
        self.epg_update_interval = epg.update_interval
        self.epg_filename = base64.b64encode(epg.name.encode('utf-8')).decode('utf-8')
        self.epg_filepath = f'{__epg_dir__}/{self.epg_filename}.xml'    
        self.epg_filepath_proxy = f'{__epg_dir__}/{self.epg_filename}_proxy.xml'

    def delete_epg(self):
        logger.info(f'EPG: Received delete request for {self.epg.name}') 
        if os.path.exists(self.epg_filepath):
            os.unlink(self.epg_filepath)
            logger.info(f'EPG: Upstream EPG deleted: {self.epg.name}')
        else:
            logger.info(f'EPG: Upstream EPG does not exist: {self.epg.name}')
            
        if os.path.exists(self.epg_filepath_proxy):
            os.unlink(self.epg_filepath_proxy)
            logger.info(f'EPG: Proxy EPG deleted: {self.epg.name}')
        else:
            logger.info(f'EPG: Proxy EPG does not exist: {self.epg.name}')            

    def get_epg(self):
        logger.info(f'EPG: {self.epg_name} requested')
        download_required = False
        replace_required = False
        if not os.path.exists(self.epg_filepath):
            download_required = True
            replace_required = True
            logger.info(f'EPG: {self.epg_name} does not exist, download required')
        else:
            mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(self.epg_filepath))
            now = datetime.datetime.now()
            age = now - mod_time
            if age.seconds / 60 / 60 > self.epg_update_interval:
                download_required = True
                replace_required = True
            else:
                logger.info(f'EPG: {self.epg_name} is too new, skipping download')
            
        if not os.path.exists(self.epg_filepath_proxy):
            replace_required = True
            logger.info(f'EPG: {self.epg_name}_filtered does not exist, replacing icons required')            
        
        if download_required:
            self.download_epg()
        if replace_required:
            self.replace_icon_urls()

        with open(self.epg_filepath_proxy, 'r') as input:
            content = input.read()
            logger.info(f'EPG: Read content into buffer')
        return content      

    def update_last_download(self):
        self.epg.last_download = make_aware(timezone.datetime.now())
        self.epg.save()

    def replace_icon_urls(self):
        logger.info(f'EPG {self.epg_name}: Replacing icon URL\'s')
        with open(self.epg_filepath, 'r') as epg:
            content = epg.read()        
        re_url = '<icon src=\"([\S]*)\"'
        for icon_url in re.findall(re_url, content, flags=0):
            #asyncio.run(iptvIcon.objects.aupdate_or_create(url=icon_url))
            iptvIcon.objects.update_or_create(url=icon_url)
            encoded_url = base64.b64encode(icon_url.encode('utf-8')).decode('utf-8')
            # TODO: Static URL
            proxy_url = f'{settings.MANAGEMENT_URL}:{settings.EXTERNAL_MANAGEMENT_PORT}/manager/get/icon/{encoded_url}'
            content = re.sub(rf'<icon src=\"([\S]*)\"',rf'<icon src="{proxy_url}"', content, flags=0)
            
        try:
            with open(self.epg_filepath_proxy, 'w') as output:
                output.write(content)
            logger.info(f'EPG {self.epg_name}: Saved proxified file as {self.epg_filepath_proxy}')
            self.update_last_download()  
        except Exception as err:
            logger.error(f'EPG {self.epg_name}: Could not write output file/directory, {err}\n')
            raise Exception(f'EPG {self.epg_name}: Could not write output file/directory, {err}\n')            

    def download_epg(self):
        logger.info(f'EPG {self.epg_name}: Downloading path {self.epg.path}')
        headers = {
                'User-Agent': self.epg.user_agent.ua_string,
                'Accept':'/',
                'Connection': 'close'                
        }
        try:
            response = get(self.epg.path, headers=headers, timeout=settings.EPG_TIMEOUT)
            if response.status_code != HTTPStatus.OK:
                logger.error(f'EPG {self.epg_name}: While getting response for {self.epg.path}: response.text\n')            
        except Exception as err:
            logger.error(f'[EPG]: Error during download, error: \n{err}')
            
        if response.status_code != HTTPStatus.OK:
            logger.error(f'EPG {self.epg_name}: While getting response for {self.epg.path}: response.text\n')
            raise Exception(f'EPG {self.epg_name}: While getting response for {self.epg.path}: response.text\n')

        logger.info(f'EPG {self.epg_name}: Received EPG from path "{self.epg.path}"')
        content = response.text
        try:
            os.makedirs(os.path.dirname(self.epg_filepath), exist_ok=True)
            with open(self.epg_filepath, 'w') as output:
                output.write(content)
                logger.info(f'EPG {self.epg_name}: Saved EPG as {self.epg_filepath}')
        except Exception as err:
            logger.error(f'EPG {self.epg_name}: Could not write output file/directory, {err}\n')
            raise Exception(f'EPG {self.epg_name}: Could not write output file/directory, {err}\n')

    def update_epg(self):
        """
        Downloads the xmltv / loads the xml and inserts information into db
        """
        logger.info(f'EPG {self.epg_name}: Update triggered: {self.epg.name}')
 
        # Acquire / Download
        if not self.epg.is_local:
            logger.info(f'EPG {self.epg_name}: EPG is remote, checking download requirement')
            # Check age of existing playlist to determine if download is necessary
            if os.path.exists(self.epg_filepath):
                logger.info(f'EPG {self.epg_name}: File already exists, checking if download is required...')
                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(self.epg_filepath))
                now = datetime.datetime.now()
                age = now - mod_time
                if age.seconds / 60 / 60 < self.epg.update_interval:
                    logger.info(f'EPG {self.epg_name}: File is {age.seconds / 60 / 60} hours old, download skipped...')
                else:
                    logger.info(f'EPG {self.epg_name}: File is {age.seconds / 60 / 60} hours old, download required...')
                    self.download_epg()
            else:
                logger.info(f'EPG {self.epg_name}: File does not exist, downloading...')
                self.download_epg()
        
        # Proxify + update timestamp once usable
        self.replace_icon_urls()
