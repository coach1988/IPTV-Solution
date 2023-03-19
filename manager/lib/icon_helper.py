import os
import base64
import logging

from requests import get
from requests.exceptions import ReadTimeout
from http import HTTPStatus

from django.conf import settings
from manager.models import iptvIcon

__icon_dir__ = f'{settings.STATIC_ROOT}/icons'
if not (os.path.isdir(__icon_dir__)):
    os.mkdir(__icon_dir__)   

logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
logger = logging.getLogger(__name__)

class IconHelper():

    icon = None
    icon_name = ''
    icon_filename = ''
    icon_filepath = ''
    icon_fileext = ''
    
    def __init__(self, icon):
        self.icon = icon
        self.icon_filename = base64.b64encode(icon.url.encode('utf-8')).decode('utf-8')
        self.icon_fileext = os.path.splitext(self.icon.url)[1].split('?',1)[0] # remove get parameter left by splitext
        self.icon_filepath = f'{__icon_dir__}/{self.icon_filename}{self.icon_fileext}'

    def scan_icon_file(self):
        try:
            self.icon.file_type = self.icon_fileext
            self.icon.file_size_byte = os.path.getsize(self.icon_filepath)
            self.icon.name = self.icon_filename
            self.icon.save()
        except Exception as err:
            logger.error(f'ICON: Exception while scanning icon file for {self.icon_filename}, error:\n{err}')
    
    def download_icon(self):
        headers = {
                'User-Agent': settings.USER_AGENT_STRING,
                'Accept':'/',
                'Connection': 'close'                
        }

        logger.info(f'ICON: Downloading icon {self.icon.url}')
        try:
            response = get(self.icon.url, headers=headers, timeout=settings.ICON_TIMEOUT)
        except ReadTimeout as err:
            #logger.warn(f'ICON: Download timed out for {self.icon.url}')
            raise Exception(f'ICON: Download timed out for {self.icon.url}, Error:\n{err}')
            #return False
            
        if response.status_code != HTTPStatus.OK:
            raise Exception(f'ICON: While getting response for {self.icon.url}: {response.text}\n')

        content = response.content
        
        try:
            os.makedirs(os.path.dirname(self.icon_filepath), exist_ok=True)
            with open(self.icon_filepath, 'wb') as output:
                output.write(content)
            self.scan_icon_file()
        except Exception as err:
            raise Exception('ICON: Icon download failed:\n{err}')
            
        logger.info(f'ICON: Received import request for {self.icon.url}') 
        if not os.path.exists(self.icon_filepath):
            self.download_icon()            
        if os.path.exists(self.icon_filepath):
            logger.info(f'ICON: Found icon {self.icon.url}')
            with open(self.icon_filepath, 'rb') as input:
                content = input.read()
            return content
        else:
            return None

    def get_icon(self):
        logger.info(f'ICON: Received get request for {self.icon.url}') 
        if not os.path.exists(self.icon_filepath):
            self.download_icon()            
        if os.path.exists(self.icon_filepath):
            #logger.info(f'ICON: Found icon {self.icon.url}')
            with open(self.icon_filepath, 'rb') as input:
                content = input.read()
            return content
        else:
            return None           
            
    def delete_icon_file(self):
        logger.info(f'ICON: Received delete request for {self.icon.url}') 
        if os.path.exists(self.icon_filepath):
            os.unlink(self.icon_filepath)
            logger.info(f'ICON: Icon deleted: {self.icon.url}')
        else:
            logger.info(f'ICON: Icon does not exist: {self.icon.url}')
