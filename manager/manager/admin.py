import base64
import logging
from enum import Enum
from requests import get

from django.conf import settings
from django.contrib import admin, messages
from django.utils.translation import ngettext

from manager import views

from .models import iptvUpstreamPlaylist
from .models import iptvDownstreamPlaylist
from .models import iptvEPG
from .models import iptvChannel
from .models import iptvIcon
from .models import iptvGroup
from .models import iptvSession
from .models import iptvStat
from .models import iptvUserAgent
from .models import iptvProxy

from lib.icon_helper import IconHelper
from lib.epg_helper import EPGHelper
from lib.upstream_playlist_helper import UpstreamPlaylistHelper
from lib.downstream_playlist_helper import DownstreamPlaylistHelper

LogLevel = Enum('LogLevel',['DEBUG', 'INFO', 'WARNING', 'ERROR', 'EXCEPTION'])

_session_id_divider = '|'
_session_id_string = '{path}' + _session_id_divider + '{client}'

logging.basicConfig(format='\[%(asctime)s\] [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
logger = logging.getLogger(__name__)

admin.site.site_header = 'IPTV Proxy Manager'

def log_admin(level, instance, request, queryset, message):
    inst_classname = type(instance).__name__
    action = request.POST['action']
    objects = queryset.values('name')
    tmp = ''
    for object in objects:
        tmp += f'\n\t- {object["name"]}'
    objects = tmp

    fstring = f'{inst_classname}:\n{action}:{objects}\n{inst_classname}: {action} ---> {message}'
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

class iptvProxyAdmin(admin.ModelAdmin):
    list_display = ('name', 'internal_url', 'internal_port', 'url', 'port')
    fieldsets = [
        ('Basic information', {'fields': ['name',]}),
        ('Session Control / Internal Network information', {'fields': ['internal_url', 'internal_port']}),
        ('Streaming Proxy / External Network information', {'fields': ['url', 'port']}),
    ]
    save_as = True

class iptvUpstreamPlaylistAdmin(admin.ModelAdmin):
    @admin.action(description='Enable upstream playlist(s)')
    def enable_upstream_playlists(self, request, queryset):
        count = queryset.update(enabled=True)
        self.message_user(request, ngettext(
            f'{count} upstream playlist enabled.',
            f'{count} upstream playlists enabled.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    @admin.action(description='Disable upstream playlist(s)')
    def disable_upstream_playlists(self, request, queryset):
        count = queryset.update(enabled=False)
        self.message_user(request, ngettext(
            f'{count} upstream playlist disabled.',
            f'{count} upstream playlists disabled.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    @admin.action(description='Delete original upstream file(s)')
    def delete_original_playlists(self, request, queryset):
        count = queryset.count()
        for upstream_playlist in queryset:
            upstream_playlist_helper = UpstreamPlaylistHelper(upstream_playlist)
            upstream_playlist_helper.delete_file()
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Deleted original playlist "{upstream_playlist}"')
            self.message_user(request, ngettext(
                f'{count} unfiltered playlist file deleted.',
                f'{count} unfiltered playlist files deleted.',
                count,
            ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    @admin.action(description='Delete filtered upstream file(s) only')
    def delete_filtered_playlists(self, request, queryset):
        count = queryset.count()
        for upstream_playlist in queryset:
            upstream_playlist_helper = UpstreamPlaylistHelper(upstream_playlist)
            upstream_playlist_helper.delete_filtered_file()
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Deleted filtered playlist "{upstream_playlist}"')
            self.message_user(request, ngettext(
                f'{count} filtered playlist file deleted.',
                f'{count} filtered playlist files deleted.',
                count,
            ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    @admin.action(description='Download upstream playlist(s) to server')
    def download_upstream_playlists(self, request, queryset):
        count = queryset.count()
        for upstream_playlist in queryset:
            upstream_playlist_helper = UpstreamPlaylistHelper(upstream_playlist)
            upstream_playlist_helper.download_upstream_playlist()
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Downloaded playlist "{upstream_playlist}"')
            self.message_user(request, ngettext(
                f'{count} upstream playlist file downloaded.',
                f'{count} upstream playlist files downloaded.',
                count,
            ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    @admin.action(description='Filter upstream playlist(s)')
    def filter_upstream_playlists(self, request, queryset):
        count = queryset.count()
        for upstream_playlist in queryset:
            upstream_playlist_helper = UpstreamPlaylistHelper(upstream_playlist)
            upstream_playlist_helper.filter_channels()
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Filtered playlist "{upstream_playlist}"')
            self.message_user(request, ngettext(
                f'{count} upstream playlist file filtered.',
                f'{count} upstream playlist files filtered.',
                count,
            ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    @admin.action(description='Import upstream playlist(s)')
    def import_upstream_playlists(self, request, queryset):
        count = queryset.count()
        for upstream_playlist in queryset:
            upstream_playlist_helper = UpstreamPlaylistHelper(upstream_playlist)
            upstream_playlist_helper.import_channels()
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Imported playlist "{upstream_playlist}"')
            self.message_user(request, ngettext(
                f'{count} upstream playlist file imported.',
                f'{count} upstream playlist files imported.',
                count,
            ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    @admin.action(description='Download, filter and import upstream playlist(s)')
    def update_upstream_playlists(self, request, queryset):
        count = queryset.count()
        for upstream_playlist in queryset:
            upstream_playlist_helper = UpstreamPlaylistHelper(upstream_playlist)
            upstream_playlist_helper.download_upstream_playlist()
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Downloaded playlist "{upstream_playlist}"')
            upstream_playlist_helper.filter_channels()
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Filtered playlist "{upstream_playlist}"')
            upstream_playlist_helper.import_channels()
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Imported playlist "{upstream_playlist}"')
            self.message_user(request, ngettext(
                f'{count} upstream playlist file imported.',
                f'{count} upstream playlist files imported.',
                count,
            ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    @admin.action(description='Download original playlist(s) to client')
    def download_local_upstream_playlists(self, request, queryset):
        count = queryset.count()
        for playlist in queryset:
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Downloaded unfiltered playlist "{playlist}" to client')
            return views.get_unfiltered_upstream_playlist(request, playlist.name)
        self.message_user(request, ngettext(
            f'{count} unfiltered upstream playlist file downloaded locally.',
            f'{count} unfiltered upstream playlist files downloaded locally.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    @admin.action(description='Download filtered playlist(s) to client')
    def download_local_upstream_playlists_filtered(self, request, queryset):
        count = queryset.count()
        for playlist in queryset:
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Downloaded filtered playlist "{playlist}" to client')
            return views.get_filtered_upstream_playlist(request, playlist.name)
        self.message_user(request, ngettext(
            f'{count} filered upstream playlist file downloaded locally.',
            f'{count} filtered upstream playlist files downloaded locally.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    def delete_queryset(self, request, queryset):
        count = queryset.count()
        for playlist in queryset:
            playlist_helper = UpstreamPlaylistHelper(playlist)
            playlist_helper.delete_playlist()
            playlist.delete()
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Deleted playlist "{playlist}"')
        self.message_user(request, ngettext(
            f'{count} upstream playlist deleted.',
            f'{count} upstream playlists deleted.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    def channel_count(self, obj):
        if iptvChannel.objects.filter(upstream=obj).exists():
            return iptvChannel.objects.filter(upstream=obj).count()
        else:
            return 0

    def group_count(self, obj):
        if iptvGroup.objects.filter(upstream=obj).exists():
            return iptvGroup.objects.filter(upstream=obj).count()
        else:
            return 0

    #channel_count.admin_order_field = 'channel_count'
    channel_count.integer = True
    channel_count.short_description = 'Imported channels'
    group_count.integer = True
    group_count.short_description = 'Imported groups'

    list_display = ('name', 'enabled', 'is_local', 'max_conns', 'in_use', 'path', 'user_agent', 'group_count', 'num_filtered_groups', 'channel_count', 'update_interval', 'last_update')
    actions = ['enable_upstream_playlists', 'disable_upstream_playlists', 'delete_original_playlists', 'delete_filtered_playlists', 'download_upstream_playlists', 'filter_upstream_playlists', 'import_upstream_playlists', 'update_upstream_playlists', 'download_local_upstream_playlists', 'download_local_upstream_playlists_filtered']
    list_filter = ('enabled', 'is_local', 'user_agent', )
    readonly_fields = ('last_update', 'num_filtered_groups')
    fieldsets = [
        ('Basic information', {'fields': ['enabled', 'name', 'is_local', 'update_interval', 'max_conns', 'in_use']}),
        ('Network information', {'fields': ['path', 'user_agent']}),
        ('Filters', {'fields': ['group_filter']}),
    ]
    save_as = True

class iptvDownstreamPlaylistAdmin(admin.ModelAdmin):
    @admin.action(description='Enable downstream playlist(s)')
    def enable_downstream_playlists(self, request, queryset):
        count = queryset.update(enabled=True)
        self.message_user(request, ngettext(
            f'{count} downstream playlist enabled.',
            f'{count} downstream playlists enabled.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    @admin.action(description='Disable downstream playlist(s)')
    def disable_downstream_playlists(self, request, queryset):
        count = queryset.update(enabled=False)
        self.message_user(request, ngettext(
            f'{count} downstream playlist disabled.',
            f'{count} downstream playlists disabled.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    @admin.action(description='Download downstream playlist(s)')
    def download_downstream_playlists(self, request, queryset):
        count = queryset.count()
        for playlist in queryset:
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Downloaded playlist "{playlist}"')
            return views.get_downstream_playlist(request, playlist.name)
        self.message_user(request, ngettext(
            f'{count} downstream playlist downloaded.',
            f'{count} downstream playlists downloaded.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    def delete_queryset(self, request, queryset):
        count = queryset.count()
        for playlist in queryset:
            playlist_helper = DownstreamPlaylistHelper(playlist)
            playlist_helper.delete_playlist()
            playlist.delete()
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Deleted playlist "{playlist}"')
        self.message_user(request, ngettext(
            f'{count} downstream playlist deleted.',
            f'{count} downstream playlists deleted.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    def has_filters(self, obj):
        return obj.channel_filter != ''

    def group_count(self, obj):
        if obj.groups != '':
            return len(obj.groups.strip().split('\n'))
        else:
            return 0

    has_filters.boolean = True
    has_filters.short_description = 'Has filters'
    group_count.integer = True
    group_count.short_description = 'Included groups'

    list_display = ('name', 'enabled', 'proxy', 'group_count', 'has_filters')
    actions = ['enable_downstream_playlists', 'disable_downstream_playlists', 'download_downstream_playlists']
    list_filter = ('enabled', 'proxy__name')
    search_fields = ['name', 'proxy__name', 'groups']
    fieldsets = [
        ('Basic information', {'fields': ['enabled', 'name', 'proxy']}),
        ('Channels', {'fields': ['groups', 'filter_mode', 'channel_filter']}),
    ]
    save_as = True

class iptvEPGAdmin(admin.ModelAdmin):
    @admin.action(description='Enable EPG(s)')
    def enable_epgs(self, request, queryset):
        count = queryset.update(enabled=True)
        self.message_user(request, ngettext(
            f'{count} EPG enabled.',
            f'{count} EPG\'s enabled.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    @admin.action(description='Disable EPG(s)')
    def disable_epgs(self, request, queryset):
        count = queryset.update(enabled=False)
        self.message_user(request, ngettext(
            f'{count} EPG disabled.',
            f'{count} EPG\'s disabled.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    @admin.action(description='Download EPG(s)')
    def download_epgs(self, request, queryset):
        count = queryset.count()
        for epg in queryset:
            epg_helper = EPGHelper(epg)
            epg_helper.download_epg()
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Downloaded EPG "{epg}"')
            epg_helper.replace_icon_urls()
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Replaced EPG icons for "{epg}"')
        self.message_user(request, ngettext(
            f'{count} EPG downloaded.',
            f'{count} EPG\'s downloaded.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    @admin.action(description='Download EPG(s) to client')
    def get_epgs(self, request, queryset):
        count = queryset.count()
        for epg in queryset:
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Transferred EPG {epg} to client')
            return views.get_epg(request, epg.name)
        self.message_user(request, ngettext(
            f'{count} EPG transferred.',
            f'{count} EPG\'s transferred.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, f'Transferred EPG\'s {queryset} to client')

    def delete_queryset(self, request, queryset):
        count = queryset.count()
        for epg in queryset:
            epg_helper = EPGHelper(epg)
            epg_helper.delete_epg()
            epg.delete()
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Deleted EPG "{epg}"')
        self.message_user(request, ngettext(
            f'{count} EPG deleted.',
            f'{count} EPG\'s deleted.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    list_display = ('name', 'enabled', 'is_local', 'path', 'user_agent', 'update_interval', 'last_download')
    list_filter = ('enabled', 'is_local', 'user_agent')
    actions = ['enable_epgs', 'disable_epgs', 'download_epgs', 'get_epgs']
    readonly_fields = ('last_download', )
    fieldsets = [
        ('Basic information', {'fields': ['enabled', 'name', 'update_interval']}),
        ('Source information', {'fields': ['is_local', 'path', 'user_agent']}),
    ]
    save_as = True

class iptvChannelAdmin(admin.ModelAdmin):
    @admin.action(description='Enable channel(s)')
    def enable_channels(self, request, queryset):
        count = queryset.update(enabled=True)
        self.message_user(request, ngettext(
            f'{count} channel enabled.',
            f'{count} channels enabled.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    @admin.action(description='Disable channel(s)')
    def disable_channels(self, request, queryset):
        count = queryset.update(enabled=False)
        self.message_user(request, ngettext(
            f'{count} channel disabled.',
            f'{count} channels disabled.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    def group_disabled(self, obj):
        if obj.group_title:
            return obj.group_title.enabled

    def upstream_disabled(self, obj):
        if obj.upstream:
            return obj.upstream.enabled

    def has_logo(self, obj):
        return bool(obj.tvg_logo)

    def url_preview(self, obj):
        return obj.url[0:50] + '...'

    group_disabled.boolean = True
    group_disabled.short_description = ''
    upstream_disabled.boolean = True
    upstream_disabled.short_description = ''
    has_logo.boolean = True
    has_logo.short_description = 'Logo'
    url_preview.string = True
    url_preview.short_description = 'URL'

    #list_display = ('name', 'enabled', 'url', 'tvg_id', 'tvg_name', 'tvg_logo', 'group_title', 'group_disabled', 'upstream', 'upstream_disabled', 'last_seen', 'extra_info')
    list_display = ('name', 'enabled', 'url_preview', 'tvg_id', 'tvg_name', 'has_logo', 'group_title', 'group_disabled', 'upstream', 'upstream_disabled', 'last_seen')
    actions = ['enable_channels', 'disable_channels']
    change_list_template = 'admin/iptvChannel/change_list.html'
    list_filter = ('enabled', 'group_title', 'upstream')
    search_fields = ['name', 'url', 'tvg_id','tvg_name', 'tvg_logo__url', 'group_title__name', 'extra_info']
    readonly_fields = ('last_seen', 'added_on', 'upstream')
    fieldsets = [
        ('Base information', {'fields': ['enabled', 'name', 'url', 'extra_info', 'upstream']}),
        ('EPG information', {'fields': ['tvg_id', 'tvg_name', 'tvg_logo', 'group_title']}),
        ('History', {'fields': ['added_on', 'last_seen']}),
    ]
    save_as = True

class iptvIconAdmin(admin.ModelAdmin):
    @admin.action(description='Download and import channel icon(s)')
    def download_icons(self, request, queryset):
        count_success = 0
        count_fail = 0
        for icon in queryset:
            icon_helper = IconHelper(icon)
            try:
                icon_helper.download_icon()
                count_success += 1
                log_admin(LogLevel.DEBUG, self, request, queryset.none(), f'Downloaded icon "{icon}"')
            except Exception as err:
                count_fail += 1
                log_admin(LogLevel.WARNING, self, request, queryset.none(), f'Icon download failed for "{icon}"')
        self.message_user(request, ngettext(
            f'{count_success} icon downloaded.',
            f'{count_success} icons downloaded.',
            count_success,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')
        if count_fail > 0:
            self.message_user(request, ngettext(
                f'{count_fail} icon download failed.',
                f'{count_fail} icons downloads failed.',
                count_fail,
            ), messages.ERROR)
            log_admin(LogLevel.WARNING, self, request, queryset.none(), f'{count_fail} failure(s)')

    def delete_queryset(self, request, queryset):
        count = queryset.count()
        for icon in queryset:
            return views.delete_icon(request, icon)
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Deleted icon "{icon}"')
        self.message_user(request, ngettext(
            f'{count} icon deleted.',
            f'{count} icons deleted.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    #def get_changelist(self, request):
    #    return iptvIconChangeList

    list_display = ('url', 'file_type', 'file_size_byte')
    change_list_template = 'admin/iptvIcon/change_list.html'
    list_filter = ('file_type', )
    actions = ['download_icons', ]
    readonly_fields = ('file_type', 'file_size_byte', 'name')
    search_fields = ['url', 'name', 'file_type']
    save_as = True

class iptvGroupAdmin(admin.ModelAdmin):
    @admin.action(description='Enable channel group(s)')
    def enable_channel_groups(self, request, queryset):
        count = queryset.update(enabled=True)
        self.message_user(request, ngettext(
            f'{count} channel group enabled.',
            f'{count} channel groups enabled.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    @admin.action(description='Disable channel group(s)')
    def disable_channel_groups(self, request, queryset):
        count = queryset.update(enabled=False)
        self.message_user(request, ngettext(
            f'{count} channel group disabled.',
            f'{count} channel groups disabled.',
            count,
        ), messages.SUCCESS)
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    def parent_status(self, obj):
        return obj.upstream.enabled

    def channel_count(self, obj):
        if iptvChannel.objects.filter(group_title=obj).exists():
            return iptvChannel.objects.filter(group_title=obj).count()
        else:
            return 0

    def active_channel_count(self, obj):
        if iptvChannel.objects.filter(group_title=obj, enabled=True).exists():
            return iptvChannel.objects.filter(group_title=obj).count()
        else:
            return 0

    parent_status.boolean = True
    parent_status.short_description = 'Playlist status'
    channel_count.integer = True
    channel_count.short_description = 'Channels included'
    active_channel_count.integer = True
    active_channel_count.short_description = 'Channels active'

    list_display = ('name', 'enabled', 'channel_count', 'active_channel_count', 'upstream', 'parent_status', )
    actions = ['enable_channel_groups', 'disable_channel_groups']
    change_list_template = 'admin/iptvGroup/change_list.html'
    list_filter = ('enabled', 'upstream', )
    search_fields = ['name', 'upstream', ]
    save_as = True

class iptvUserAgentAdmin(admin.ModelAdmin):
    list_display = ('name', 'ua_string')
    save_as = True

class iptvStatAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    list_display = ('channel', 'client_ip', 'last_access', 'last_streamtime', 'streamtime')
    list_filter = ('client_ip',)
    readonly_fields = ('channel', 'client_ip', 'streamtime', 'last_access')

class iptvSessionAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def create_queryset(self, request, queryset):
        for session in queryset:
            path = session.url
            client = session.client_ip
            fno = session.fno
            session_id = _session_id_string.format(path=path, client=client, fno=fno)
            session.create(session_id=session_id)
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Created session "{session}"')
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    def delete_queryset(self, request, queryset):
        for session in queryset:
            # TODO: Static URL
            stream_server_stop_endpoint = f'{session.proxy.internal_url}:{session.proxy.internal_port}/stream/stop/'

            path = session.url
            client = session.client_ip
            ua_string = session.user_agent
            upstream = session.channel.upstream
            upstream.in_use = upstream.in_use - 1
            upstream.save()
            session_id = _session_id_string.format(path=path, client=client, ua_string=ua_string)
            session_id_b64 = base64.b64encode(session_id.encode('utf-8')).decode('utf-8')
            get(f'{stream_server_stop_endpoint}{session_id_b64}', allow_redirects=True, stream=True, timeout=settings.INTERNAL_TIMEOUT)
            session.delete()
            log_admin(LogLevel.DEBUG, self, request, queryset, f'Deleted session "{session}"')
        log_admin(LogLevel.INFO, self, request, queryset, 'Success')

    list_display = ('client_ip', 'channel', 'user_agent', 'start_time', 'proxy')
    list_filter = ('client_ip', 'user_agent', 'proxy')
    readonly_fields = ('client_ip', 'user_agent', 'channel', 'start_time', 'proxy')

admin.site.register(iptvProxy, iptvProxyAdmin)
admin.site.register(iptvUpstreamPlaylist, iptvUpstreamPlaylistAdmin)
admin.site.register(iptvDownstreamPlaylist, iptvDownstreamPlaylistAdmin)
admin.site.register(iptvEPG, iptvEPGAdmin)
admin.site.register(iptvChannel, iptvChannelAdmin)
admin.site.register(iptvIcon, iptvIconAdmin)
admin.site.register(iptvGroup, iptvGroupAdmin)
admin.site.register(iptvSession, iptvSessionAdmin)
admin.site.register(iptvStat, iptvStatAdmin)
admin.site.register(iptvUserAgent, iptvUserAgentAdmin)