from django.db import models
from django.utils import timezone

class iptvProxy(models.Model):
    name = models.CharField(primary_key=True, verbose_name='Proxy Name', max_length=255)
    internal_url = models.CharField(verbose_name='Internal URL', help_text='URI + hostname target to control the stream server, e.g. "http://myhost.mydomain.net"', max_length=255, default='http://localhost')
    internal_port = models.PositiveSmallIntegerField(verbose_name='Internal Port', default=8089)
    url = models.CharField(verbose_name='External URL', help_text='URI + hostname to use as prefix in playlists and EPGs, e.g. "http://myhost.mydomain.net"', max_length=255)
    port = models.PositiveSmallIntegerField(verbose_name='External Port', default=8089)

    class Meta:
        verbose_name = 'Upstream - Proxy Server'
        verbose_name_plural = 'Upstream - Proxy Servers'

    def __str__(self):
        return(self.name)

class iptvUserAgent(models.Model):
    name = models.CharField(verbose_name='Name', max_length=255)
    ua_string = models.CharField(verbose_name='User Agent String', help_text='User agent string to send when requesting upstream resources', max_length=255, blank=True, default='')

    class Meta:
        verbose_name = 'Upstream - User Agent String'
        verbose_name_plural = 'Upstream - User Agent Strings'

    def __str__(self):
        return(self.name)

class iptvUpstreamPlaylist(models.Model):
    enabled = models.BooleanField(verbose_name='Enabled', default=True)
    name = models.CharField(verbose_name='Name', max_length=255)
    group_filter = models.TextField(verbose_name='Group filters', help_text='Exclude these groups from further processing', blank=True, null=True)
    user_agent = models.ForeignKey(iptvUserAgent, verbose_name='User Agent', help_text='User agent string to send if requesting an upstream EPG', on_delete=models.PROTECT, max_length=255, blank=True, null=True)
    path = models.CharField(verbose_name='Path / URL', help_text='The location of the playlist', max_length=255)
    is_local = models.BooleanField(verbose_name='Is local', help_text='This playlist is a local file', default=False)
    update_interval = models.PositiveSmallIntegerField(default=24)
    last_update = models.DateTimeField(editable=False, blank=True, null=True)
    max_conns = models.SmallIntegerField(verbose_name='Max concurrent streams', default=0, null=False)
    in_use = models.SmallIntegerField(verbose_name='Active streams', default=0, null=False, editable=True)
    num_filtered_groups = models.SmallIntegerField(verbose_name='Filtered groups', help_text='Amount of filtered groups', null=False)

    class Meta:
        verbose_name = 'Upstream - Playlist'
        verbose_name_plural = 'Upstream - Playlists'
        constraints = [
            models.UniqueConstraint(fields = ['name', 'path'], name = 'unique_upstream')
        ]

    def __str__(self):
        return(self.name)

    def save(self, *args, **kwargs):
        self.num_filtered_groups = len(self.group_filter.split('\n')) if not self.group_filter == '' else 0
        super(iptvUpstreamPlaylist, self).save(*args, **kwargs)

class iptvDownstreamPlaylist(models.Model):
    FILTER_MODE_CHOICES = [
        ('A', 'Any'),
        ('E', 'Exact'),
        ('P', 'Prefix'),
        ('S', 'Suffix'),
    ]
    filter_mode = models.CharField(
        verbose_name='Filter mode',
        max_length=1,
        choices=FILTER_MODE_CHOICES,
        default='A',
    )
    enabled = models.BooleanField(verbose_name='Enabled', default=True)
    name = models.CharField(max_length=255)
    groups = models.TextField(verbose_name='Playlist channel groups', help_text='Channel groups to include in this playlist', blank=True, null=True)
    channel_filter = models.TextField(verbose_name='Channel filters', help_text='Additionally filtered out channels', blank=True, null=True)
    proxy = models.ForeignKey(iptvProxy, verbose_name='Proxy', help_text='Streaming proxy to use for playlist entries', on_delete=models.PROTECT, max_length=255, blank=False, null=False)

    class Meta:
        verbose_name = 'Downstream - Playlist'
        verbose_name_plural = 'Downstream - Playlists'

    def __str__(self):
        return(self.name)

class iptvEPG(models.Model):
    enabled = models.BooleanField(verbose_name='Enabled', default=True)
    name = models.CharField(verbose_name='Name', max_length=255)
    user_agent = models.ForeignKey(iptvUserAgent, verbose_name='User Agent', help_text='User agent string to send if requesting an upstream EPG', on_delete=models.PROTECT, max_length=255, blank=True, null=True)
    path = models.CharField(verbose_name='Path / URL', help_text='The location of the EPG file', max_length=255)
    is_local = models.BooleanField(verbose_name='Is local', default=False)
    last_download = models.DateTimeField(editable=False, blank=True, null=True)
    update_interval = models.PositiveSmallIntegerField(default=24)

    class Meta:
        verbose_name = 'Upstream - EPG'
        verbose_name_plural = 'Upstream - EPG\'s'

    def __str__(self):
        return(self.name)

class iptvGroup(models.Model):
    enabled = models.BooleanField(verbose_name='Enabled', default=True)
    name = models.CharField(verbose_name='Group', max_length=255)
    upstream = models.ForeignKey(iptvUpstreamPlaylist, verbose_name='Playlist', on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = 'IPTV - Group'
        verbose_name_plural = 'IPTV - Groups'
        constraints = [
            # Make sure we allow for the same group from different upstream playlists and the same channel in different groups
            models.UniqueConstraint(fields = ['name', 'upstream', ], name = 'unique_group')
        ]

    def __str__(self):
        return(self.name)

class iptvIcon(models.Model):
    url = models.CharField(primary_key=True, max_length=1024)
    name = models.CharField(editable=False, max_length=1024, blank=True, null=True)
    file_type = models.CharField(editable=False, max_length=255, blank=True, null=True)
    file_size_byte = models.PositiveSmallIntegerField(verbose_name='File size (kB)', editable=False, blank=True, null=True)

    class Meta:
        verbose_name = 'IPTV - Logo'
        verbose_name_plural = 'IPTV - Logos'

    def __str__(self):
        return(self.url)

class iptvChannel(models.Model):
    enabled = models.BooleanField(verbose_name='Enabled', default=True)
    name = models.CharField(max_length=255)
    url = models.CharField(max_length=1024)
    tvg_id = models.CharField(verbose_name='EPG ID', max_length=255, blank=True, null=True)
    tvg_name = models.CharField(verbose_name='EPG Name', max_length=255, blank=True, null=True)
    tvg_logo = models.ForeignKey(iptvIcon, verbose_name='Logo', on_delete=models.SET_NULL, blank=True, null=True)
    group_title = models.ForeignKey(iptvGroup, verbose_name='Group', on_delete=models.SET_NULL, blank=True, null=True)
    upstream = models.ForeignKey(iptvUpstreamPlaylist, verbose_name='Playlist', on_delete=models.CASCADE, null=False)
    last_seen = models.DateTimeField(verbose_name='Last import', editable=False, blank=True, null=True)
    added_on = models.DateTimeField(verbose_name='First import', auto_now_add=True, editable=False)
    extra_info = models.TextField(verbose_name='Additional info', max_length=255, blank=True, null=True)
    protected = models.BooleanField(verbose_name='Keep status', blank=False, default=False)

    class Meta:
        verbose_name = 'IPTV - Channel'
        verbose_name_plural = 'IPTV - Channels'
        constraints = [
            # Make sure we allow for the same channel from different upstream playlists and the same channel in different groups
            models.UniqueConstraint(fields = ['name', 'url', 'group_title', 'upstream', 'extra_info'], name = 'unique_channel')
        ]

    def save(self, *args, **kwargs):
        self.last_seen = timezone.now()
        super(iptvChannel, self).save(*args, **kwargs)

    def __str__(self):
        return(self.name)

class iptvSession(models.Model):
    name = models.CharField(verbose_name='Internal Session ID', max_length=1280, editable=False) # Must hold URL + '|' + IP (used to allow several channels at once per IP/client)
    client_ip = models.CharField(verbose_name='Client', max_length=15, editable=False)
    user_agent = models.ForeignKey(iptvUserAgent, on_delete=models.DO_NOTHING)
    start_time = models.DateTimeField(verbose_name='Stream start time', auto_now_add=True, editable=False)
    channel = models.ForeignKey(iptvChannel, on_delete=models.CASCADE)
    proxy = models.ForeignKey(iptvProxy, verbose_name='Routed via', on_delete=models.CASCADE)
    url = models.CharField(max_length=1024, editable=False)

    class Meta:
        verbose_name = 'Upstream - Proxy Session'
        verbose_name_plural = 'Upstream - Proxy Sessions'

    def __str__(self):
        return(self.client_ip)

# TODO: Find better type for accumulated times
class iptvStat(models.Model):
    channel = models.ForeignKey(iptvChannel, on_delete=models.CASCADE)
    client_ip = models.CharField(verbose_name='Client IP', max_length=15, editable=False)
    streamtime = models.CharField(verbose_name='Total stream time', max_length=15, editable=False)
    last_streamtime = models.CharField(verbose_name='Last stream duration', max_length=15, editable=False)
    last_access = models.DateTimeField(auto_now=True, verbose_name='Last streamed', editable=False)

    class Meta:
        verbose_name = 'Downstream - Stat'
        verbose_name_plural = 'Downstream - Stats'
        constraints = [
            models.UniqueConstraint(fields = ['channel', 'client_ip'], name = 'channel_client_pair')
        ]

    def __str__(self):
        return(self.channel.name)