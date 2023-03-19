import base64
import logging
import datetime
import asyncio
import mimetypes
from enum import Enum

from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect

from .models import iptvUpstreamPlaylist, iptvDownstreamPlaylist, iptvEPG, iptvChannel, iptvIcon, iptvSession, iptvGroup, iptvUserAgent, iptvProxy

from lib.downstream_playlist_helper import DownstreamPlaylistHelper
from lib.upstream_playlist_helper import UpstreamPlaylistHelper
from lib.icon_helper import IconHelper
from lib.epg_helper import EPGHelper

_session_id_divider = '|'
_session_id_string = '{path}' + _session_id_divider + '{client}'
_reportActionBegin = 'Begin'
_reportActionEnd = 'End'

logger = logging.getLogger(__name__)

LogLevel = Enum('LogLevel', ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'EXCEPTION'])

def log_view(level, request, message):
    action = request.environ['PATH_INFO']
    fstring = f'views.py: {action} ---> {message}'
    if level == LogLevel.DEBUG:
        logger.debug(fstring)
    elif level == LogLevel.INFO:
        logger.info(fstring)
    elif level == LogLevel.WARNING:
        logger.warning(fstring)
    elif level == LogLevel.ERROR:
        logger.error(fstring)
    else:
        logger.critical(fstring)

def get_groups(request):
    response = ''
    for group in iptvGroup.objects.all():
        log_view(LogLevel.DEBUG, request, f'Got group "{group}"')
        response = f'{response}{group}<br />'
    log_view(LogLevel.INFO, request, 'Transferred group list')
    return HttpResponse(response)

def purge_channels(request):
    iptvChannel.objects.all().delete()
    log_view(LogLevel.INFO, request, 'Purged channels')
    return HttpResponseRedirect(request.headers['Referer'])

def purge_icons(request):
    for icon in iptvIcon.objects.all():
        log_view(LogLevel.DEBUG, request, f'Deleting file for icon "{icon}"')
        icon_helper = IconHelper(icon)
        icon_helper.delete_icon_file()
    iptvIcon.objects.all().delete()
    log_view(LogLevel.INFO, request, 'Purged icons')
    return HttpResponseRedirect(request.headers['Referer'])
    
def purge_groups(request):
    iptvGroup.objects.all().delete()
    log_view(LogLevel.INFO, request, 'Purged groups')
    return HttpResponseRedirect(request.headers['Referer'])

def delete_icon(request, icon):
    icon_helper = IconHelper(icon)
    icon_helper.delete_icon_file()
    icon.delete()
    log_view(LogLevel.INFO, request, f'Deleted icon {icon}')
    return HttpResponseRedirect(request.headers['Referer'])

def report_stream_session(request):
    url = request.headers['url'].removeprefix('/stream/').split('/')[1] # Remove leading "/stream/<action>/"
    decoded = base64.b64decode(url.encode('utf-8')).decode('utf-8')
    url = decoded.split(_session_id_divider)[0]
    client = request.headers['client']
    session_id = _session_id_string.format(path=url, client=client)

    ua_string = request.headers['user-agent']
    channel = iptvChannel.objects.get(url=url)
    action = request.headers['action']
    proxy_name = request.headers['proxy-name']
    proxy_url_internal = request.headers['proxy-url-internal']
    proxy_port_internal = request.headers['proxy-port-internal']
    proxy_url_external = request.headers['proxy-url-external']
    proxy_port_external = request.headers['proxy-port-external']

    log_view(LogLevel.INFO, request, f'Received report for session {session_id}')
    if iptvUserAgent.objects.filter(ua_string=ua_string).count() == 0:  # Create a User Agent entry on the fly if unknown
        iptvUserAgent.objects.create(name=f'[REPORTED] {client}/{datetime.datetime.now()}', ua_string=ua_string)
        log_view(LogLevel.WARNING, request, f'Registered previously unknown user agent {ua_string}')
    user_agent = iptvUserAgent.objects.get(ua_string=ua_string)
    
    proxy_defaults = {
        'internal_url':proxy_url_internal, 
        'internal_port':proxy_port_internal, 
        'url':proxy_url_external, 
        'port':proxy_port_external
    }
    proxy, created = iptvProxy.objects.update_or_create(name=proxy_name, defaults=proxy_defaults)    
    if created:
        log_view(LogLevel.WARNING, request, f'Registered previously unknown proxy {proxy_name}')

    # This might fail if not ordered under heavy load, as we cannot guarantee that the create report is received before the creation on heavy channel zapping (need queue)
    if action == _reportActionBegin:
        asyncio.run(iptvSession.objects.acreate(name=session_id, client_ip=client, user_agent=user_agent, start_time=datetime.datetime.now(), channel=channel, url=decoded, proxy=proxy))
        log_view(LogLevel.INFO, request, f'Added session {session_id}')
    if action == _reportActionEnd:        
        sess = iptvSession.objects.filter(name=session_id, user_agent=user_agent, proxy=proxy)
        if sess:
            asyncio.run(sess.adelete())
            log_view(LogLevel.INFO, request, f'Removed session {session_id}')
        else:
            log_view(LogLevel.WARNING, request, f'Tried removing non-existing session {session_id}')
    return HttpResponse()

def get_icon(request, name):
    try:
        decoded_url = base64.b64decode(name).decode('utf-8')
        icon = iptvIcon.objects.get(url=decoded_url)
        icon_helper = IconHelper(icon)
        icon_file = icon_helper.get_icon() 
        response = HttpResponse(icon_file, content_type=f'{mimetypes.guess_type(icon_helper.icon_filename)}')
        response['Content-Disposition'] = f'attachment; filename="{icon_helper.icon_filename}"'
        log_view(LogLevel.INFO, request, f'Transferred icon {name}')
    except Exception as err:
        response = HttpResponseServerError(f'Icon get error:\n{err}')
        log_view(LogLevel.WARNING, request, f'Icon get error:\n{err}')
    return response

def get_epg(request, name):
    try:
        epg = iptvEPG.objects.get(name=name, enabled=True)
        epg_helper = EPGHelper(epg)
        response = HttpResponse(epg_helper.get_epg(), content_type=f'application/xml; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{epg_helper.epg_name}.xml"'
        log_view(LogLevel.INFO, request, f'Transferred EPG {name}')
    except Exception as err:
        response = HttpResponseServerError(f'EPG get error:\n{err}')
        log_view(LogLevel.WARNING, request, f'EPG get error:\n{err}')
    return response        

def get_unfiltered_upstream_playlist(request, name):
    try:
        playlist = iptvUpstreamPlaylist.objects.get(name=name, enabled=True)
        upstream_playlist_helper = UpstreamPlaylistHelper(playlist)
        response = HttpResponse(upstream_playlist_helper.get_playlist(), content_type='application/x-mpegurl; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="upstream-{name}-unfiltered.m3u"'
        log_view(LogLevel.INFO, request, f'Transferred unfiltered upstream playlist {name}')
    except Exception as err:
        response = HttpResponseServerError(f'Unfiltered upstream get error:\n{err}')
        log_view(LogLevel.WARNING, request, f'Unfiltered upstream get error:\n{err}')
    return response

def get_filtered_upstream_playlist(request, name):
    try:
        playlist = iptvUpstreamPlaylist.objects.get(name=name, enabled=True)
        upstream_playlist_helper = UpstreamPlaylistHelper(playlist)
        response = HttpResponse(upstream_playlist_helper.get_playlist_filtered(), content_type='application/x-mpegurl; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="upstream-{name}-filtered.m3u"'
        log_view(LogLevel.INFO, request, f'Transferred filtered upstream playlist {name}')
    except Exception as err:
        response = HttpResponseServerError(f'Filtered upstream get error:\n{err}')
        log_view(LogLevel.WARNING, request, f'Filtered upstream get error:\n{err}')
    return response

def get_downstream_playlist(request, name):
    try:
        playlist = iptvDownstreamPlaylist.objects.get(name=name, enabled=True)
        downstream_playlist_helper = DownstreamPlaylistHelper(playlist)
        response = HttpResponse(downstream_playlist_helper.get_playlist(), content_type='application/x-mpegurl; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="downstream-{name}.m3u"'
        log_view(LogLevel.INFO, request, f'Transferred downstream playlist {name}')
    except Exception as err:
        response = HttpResponseServerError(f'Downstream get error:\n{err}')
        log_view(LogLevel.WARNING, request, f'Downstream get error:\n{err}')
    return response