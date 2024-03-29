import base64
import logging
import datetime
#import asyncio
import mimetypes
from enum import Enum

from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect
from django.utils import timezone

from .models import iptvUpstreamPlaylist, iptvDownstreamPlaylist, iptvEPG, iptvChannel, iptvIcon, iptvSession, iptvGroup, iptvUserAgent, iptvProxy, iptvStat

from lib.downstream_playlist_helper import DownstreamPlaylistHelper
from lib.upstream_playlist_helper import UpstreamPlaylistHelper
from lib.icon_helper import IconHelper
from lib.epg_helper import EPGHelper

_divider = '|'
_session_id_string = '{path}' + _divider + '{client}'
_status_string = '{current}' + _divider + '{pl_max}'
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

# TODO: Hardcoded separator for group to upstream link
def get_groups(request):
    response = ''
    for group in iptvGroup.objects.all():
        log_view(LogLevel.DEBUG, request, f'Got group "{group}"')
        response = f'{response}{group}@{group.upstream}\n'
    log_view(LogLevel.INFO, request, 'Transferred group list')
    return HttpResponse(response,content_type='text/plain')

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
    log_view(LogLevel.INFO, request, f'URL: {url}')
    decoded = base64.b64decode(url.encode('utf-8') + b'==').decode('utf-8')
    log_view(LogLevel.INFO, request, f'Decoded: {decoded}')
    url = decoded.split(_divider)[0]
    client = request.headers['client']
    session_id = _session_id_string.format(path=url, client=client)

    ua_string = request.headers['user-agent']
    # TODO: add a prefix to the url that indicates the channel's parent upstream to allow for non-unique URLs
    channel = iptvChannel.objects.get(url=url)
    action = request.headers['action']
    proxy_name = request.headers['proxy-name']
    proxy_url_internal = request.headers['proxy-url-internal']
    proxy_port_internal = request.headers['proxy-port-internal']
    proxy_url_external = request.headers['proxy-url-external']
    proxy_port_external = request.headers['proxy-port-external']

    log_view(LogLevel.INFO, request, f'Received {action} report for session {session_id}')
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
        # increase usage counter
        channel.upstream.in_use += 1
        channel.upstream.save()
        log_view(LogLevel.INFO, request, f'Increased connection count for {channel.upstream}, new value: {channel.upstream.in_use}')
        #asyncio.run(iptvSession.objects.acreate(name=session_id, client_ip=client, user_agent=user_agent, start_time=datetime.datetime.now(), channel=channel, url=decoded, proxy=proxy))
        iptvSession.objects.create(name=session_id, client_ip=client, user_agent=user_agent, start_time=datetime.datetime.now(), channel=channel, url=decoded, proxy=proxy)
        log_view(LogLevel.INFO, request, f'Added session {session_id}')
    if action == _reportActionEnd:
        # decrease usage counter
        channel.upstream.in_use += - 1
        channel.upstream.save()
        log_view(LogLevel.INFO, request, f'Decreased connection count for {channel.upstream}, new value: {channel.upstream.in_use}')

        sess = iptvSession.objects.filter(name=session_id, user_agent=user_agent, proxy=proxy)
        if iptvStat.objects.filter(channel=sess[0].channel, client_ip=sess[0].client_ip).exists():
            old_sess = iptvStat.objects.filter(channel=sess[0].channel, client_ip=sess[0].client_ip)
            prev_run_time = old_sess[0].streamtime
        else:
            prev_run_time = '0:00:00.000000'

        run_time = timezone.now() - sess[0].start_time

        t = datetime.datetime.strptime(prev_run_time, "%H:%M:%S.%f")
        prev_run_time = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
        new_run_time = prev_run_time + run_time

        #stat, created = asyncio.run(iptvStat.objects.aupdate_or_create(channel=channel, client_ip=client))
        stat, created = iptvStat.objects.update_or_create(channel=channel, client_ip=client)
        stat.streamtime = str(new_run_time)
        stat.last_streamtime = run_time
        stat.save()
        if sess:
            #asyncio.run(sess.adelete())
            sess.delete()
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

# TODO: Set different results for different conditions
def get_upstream_playlist_status(request, url):
    try:
        decoded_url = base64.b64decode(url).decode('utf-8')
        channel = iptvChannel.objects.get(url=decoded_url)
        playlist = channel.upstream

        current = playlist.in_use
        pl_max = playlist.max_conns
        lines_available = (pl_max == 0 or current < pl_max)
        log_view(LogLevel.INFO, request, f'Upstream lines available for "{playlist}": {lines_available} ({current} / {pl_max})')

        pl_active = playlist.enabled
        log_view(LogLevel.INFO, request, f'Upstream playlist enabled status for "{playlist}": {pl_active}')

        channel_active = channel.enabled
        log_view(LogLevel.INFO, request, f'Channel "{channel}" enabled: {channel_active}')

        # TODO: Figure out how to reliably check if channel's groups have been disabled once they have been split into individual ones
        group_active = channel.group_title.enabled
        log_view(LogLevel.INFO, request, f'Channel group of "{channel}" enabled: {group_active}')

        result = lines_available and pl_active and channel_active and group_active
        log_view(LogLevel.INFO, request, f'Upstream status of "{playlist}": {result}')
    except Exception as err:
        log_view(LogLevel.WARNING, request, f'Upstream get status error:\n{err}')
        return HttpResponseServerError(f'Upstream get status error:\n{err}')
    return HttpResponse(result)

def get_channel_opts(request, url):
    try:
        decoded_url = base64.b64decode(url).decode('utf-8')
        channel = iptvChannel.objects.get(url=decoded_url)
        log_view(LogLevel.INFO, request, f'Upstream get channel opts for channel: {channel}')
        opts = channel.extra_info
        log_view(LogLevel.INFO, request, f'Upstream opts for "{channel}": {opts}')
        response = HttpResponse(opts)
    except Exception as err:
        response = HttpResponseServerError(f'Upstream get opts error:\n{err}')
        log_view(LogLevel.WARNING, request, f'Upstream get opts error:\n{err}')
    return response