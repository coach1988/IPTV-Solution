# IPTV-Solution

## What is it?

A Django-based web-UI to manage IPTV streaming playlists (M3U) + EPG's (XMLTV), upstream and downstream. It is basically my first Django project and it is one of only few of my projects that have a real use and that others get to see, so please bear with me if the code is not very pythonic;-)

It is split up into a management service (Django based, port 8088) and a streaming proxy (Flask based, port 8089).

PS: Yes, the name is not very creative.

## Features:

- [x] Fully responsive web UI
- [x] Multi-Client/Playlist/Proxy
- [x] Complete docker-compose stack
- [x] Distributed architecture
- [x] (Basic) Session handling
- [x] Channel icon cache and management

## Impressions

Here are some pictures:
- https://pasteboard.co/tgCR6zdVqiid.png
- https://pasteboard.co/qhEQno73k8Ty.png
- https://pasteboard.co/cIaUbT6eZtuP.png
- https://pasteboard.co/MsNCJs84tOYO.png

## How does it work?

The setup currently works like this:

1. You define upstream user agents; These strings will be sent to upstream servers when downloading files
2. You define upstream playlists; These can origin from local files or a http(s) URL's. They use the user agents defined in the first step and can be further filtered before their channels and icons will be imported. 
    - The filters apply to the "group-title" attribute within M3U files and filter out all channels that belong to groups with these names (one group per line)
    - Tip: Trigger a manual download and import via the actions above the list to populate your channels, icons and groups
3. You define upstream proxy servers: These have an internal and external URL and port. If you are hosting the management server and the streaming proxy on the same host, you will leave the internal URL's pointing to the localhost and the default port, unless you've changed these settings. The external URL and port should match the URL's of the proxy servers and their ports. 
    - The information you're using for the internal network connection will be used only by the management server to connect to the proxy in case you want to drop a running streaming session
    - The information for the external network connection will be inserted as a proxy for URL-entries in M3U's and XML's (for EPG's)
4. You define downstream playlists; These will be assigned an upstream proxy created in the third step and will be dynamically assembled from the groups you enter here 
    - Tip: There is a "Get group list" button on the top right of the group admin page that returns all known groups as a text to copy &amp; paste
    - You can eventually also filter out further channels based on their names
5. (Optional): Define upstream EPG's: You can proxy local or remote XMLTV files

Each defined downstream playlist and each EPG is available via individual URL's.

It is meant to allow you to import the set of channel groups you are interested in from your upstream, leaving out all the groups that you don't want anyways. You then define a playlist for each one of your clients by defining a set of channel groups they will receive. If these groups still contain individual channels you don't want them to receive, you can filter them out. You can also disable channel groups, channels and playlists individually to exclude them from playlists/downloads.

## URL's and login

(Adjust the hostname, port and URI scheme according to your settings)

Web admin UI (default username: **admin**, default password: **password**)

```
http://localhost:8088/admin
```

URL for EPG (replace "&lt;name&gt;" with your EPG's name)

```
http://localhost:8088/manager/get/epg/<name>
```

URL for downstream playlist (replace "&lt;name&gt;" with your playlist's name)

```
http://localhost:8088/manager/get/playlist/<name>
```

## Known issues

- Code quality: I am no coder, especially not for Django. Expect a lot of dirty code. But what can i say? It works for me;)
- Encodings: I am bad at encodings, I am bad at http-headers and I am bad at writing files; I am sure that you will run into issues with more exotic characters and encodings
- Security: I am aware of a lot of conceptual security issues; This solution was designed to be deployed inhouse for my wife (and no, she would not know how to spoof anything or get around the firewall)
- Webserver: Right now, everything is based on the Django's and Flask's webservers; I would like to give interested parties at least the option to deploy this solution with their own webservers, but I don't know enough about WSGI and ASGI for that yet
- Dropping of sessions currently only works from the overview, but not from a session's details page 
    - It can also take up to ~45 seconds before the stream stalls
- Many more (especially as I have only one concurrent upstream connection to test with)
- Mean exceptions when dropping a stream;)

## Why Django's *AND* Flask's webserver?

I wanted to use Django as a management UI once i learned about it and I had this plan for a rewrite of a proxy for a long time. I unfortunately had to find out that Django is not really streaming friendly, so I had to fall back to Flask for that. But hey, at laest we've gained support for distributed setups:)

## ToDo's

- Overwrite handling: Allow for a convenient way to replace things such as channel name, channel groups, etc.
- Service files: Ship it with some systemd units
- User session limits: Implement some enforcement of concurrency limits for upstream playlists
- It is far from complete, so probably many additional things

## How to run

### docker-compose:

1. Clone the git repository:  
    ```
    git clone https://github.com/coach1988/IPTV-Solution.git
    ```
2. Edit the docker-compose.yml with the editor of your choice
3. Build the docker images  
    ```
    docker-compose build
    ```
4. Run the stack  
    ```
    docker-compose up -d
    ```

The docker container for the manager uses two volumes, one for the database, one for static files (icons, epg and playlists).


### manual execution:

1. Clone the git repository:  
    ```
    git clone https://github.com/coach1988/IPTV-Solution.git
    ```
2. Edit the proxy.env and manager.env with the editor of your choice
3. Create a venv for, activate it and install the requirements (for both programs)  
    ```
    python3 -m venv venv
    source venv/bin/activate
    python3 -m pip install -r requirements.txt
    ```
4. Run the manager process  
    ```
    manager/run_local.sh
    ```
5. Run the proxy process  
    ```
    proxy/run_local.sh
    ```

## Variables

#### Manager

<table border="1" id="bkmrk-name-default-usage-a" style="border-collapse: collapse; width: 100%; border-width: 1px; height: 275.8px;"><colgroup><col style="width: 29.5426%;"></col><col style="width: 20.3006%;"></col><col style="width: 50.1567%;"></col></colgroup><tbody><tr style="height: 29.8px;"><td style="border-width: 1px; height: 29.8px;">Name  
</td><td style="border-width: 1px; height: 29.8px;">Default  
</td><td style="border-width: 1px; height: 29.8px;">Usage  
</td></tr><tr style="height: 29.8px;"><td style="border-width: 1px; height: 29.8px;">ALLOWED_HOSTS</td><td style="border-width: 1px; height: 29.8px;">['*']</td><td style="border-width: 1px; height: 29.8px;">Django's list of allowed hosts  
</td></tr><tr style="height: 63.4px;"><td style="border-width: 1px; height: 63.4px;">TIME_ZONE</td><td style="border-width: 1px; height: 63.4px;">UTC  
</td><td style="border-width: 1px; height: 63.4px;">Timezone to use for Django

(see [https://en.wikipedia.org/wiki/List\_of\_tz\_database\_time\_zones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones))

</td></tr><tr style="height: 46.6px;"><td style="border-width: 1px; height: 46.6px;">DJANGO_SUPERUSER_USERNAME</td><td style="border-width: 1px; height: 46.6px;">admin</td><td style="border-width: 1px; height: 46.6px;">Default admin login  
</td></tr><tr style="height: 46.6px;"><td style="border-width: 1px; height: 46.6px;">DJANGO_SUPERUSER_EMAIL</td><td style="border-width: 1px; height: 46.6px;">admin@admin.com</td><td style="border-width: 1px; height: 46.6px;">Default admin email address  
</td></tr><tr style="height: 29.8px;"><td style="border-width: 1px; height: 29.8px;">DJANGO_SUPERUSER_PASSWORD</td><td style="border-width: 1px; height: 29.8px;">password  
</td><td style="border-width: 1px; height: 29.8px;">Default admin password  
</td></tr><tr style="height: 29.8px;"><td style="border-width: 1px; height: 29.8px;">SECRET_KEY</td><td style="border-width: 1px; height: 29.8px;"><strong>Fill me in!</strong>  
</td><td style="border-width: 1px; height: 29.8px;">Some secret key for Django, e.g. from https://djecrety.ir/</td></tr><tr><td style="border-width: 1px;">DEBUG</td><td style="border-width: 1px;">True  
</td><td style="border-width: 1px;">Enable Django debugging; <strong>Should be set to "True" unless you want to deal with the static file management</strong>
</td></tr><tr><td style="border-width: 1px;">LOGLEVEL</td><td style="border-width: 1px;">DEBUG  
</td><td style="border-width: 1px;">Set log level, see <a href='https://docs.python.org/3/howto/logging.html#logging-levels>this list</a>
</td></tr><tr><tr><td style="border-width: 1px;">ALLOWED_URL_SCHEMES</td><td style="border-width: 1px;">['http', 'https', 'mmsh', 'mmst', 'mmsu', 'mms', 'rtmp', 'rtsp']  
</td><td style="border-width: 1px;">Disable any channel on first import that does not use one of these URL schemes  
</td></tr><tr><tr><td style="border-width: 1px;">BLOCKED_PATH_TYPES</td><td style="border-width: 1px;">['.m3u', '.m3u8', '.mpd']  
</td><td style="border-width: 1px;">Disable any channel on first import that has a path ending with one of these suffixes  
</td></tr><tr><tr><td style="border-width: 1px;">BLOCKED_URL_REGEXS</td><td style="border-width: 1px;">['output=playlist.m3u[8]?', 'www.youtube.com/', ]
</td><td style="border-width: 1px;">Disable any channel on first import that has a URL matching one of these RegEx's  
</td></tr><tr><td style="border-width: 1px;">SOCKET_ADDRESS</td><td style="border-width: 1px;">0.0.0.0  
</td><td style="border-width: 1px;">The IP to bind the socket to</td></tr><tr><td style="border-width: 1px;">MANAGEMENT_URL</td><td style="border-width: 1px;">http://localhost  
</td><td style="border-width: 1px;">Used during M3U and EPG generation for icon URL prefixes</td></tr><tr><td style="border-width: 1px;">INTERNAL_MANAGEMENT_PORT</td><td style="border-width: 1px;">8088  
</td><td style="border-width: 1px;">Used for the socket setup</td></tr><tr><td style="border-width: 1px;">EXTERNAL_MANAGEMENT_PORT</td><td style="border-width: 1px;">8088  
</td><td style="border-width: 1px;">Used during M3U and EPG generation for icon URL prefixes</td></tr><tr><td style="border-width: 1px;">INTERNAL_TIMEOUT</td><td style="border-width: 1px;">1  
</td><td style="border-width: 1px;">Timeout in seconds for internal control connections</td></tr><tr><td style="border-width: 1px;">USER_AGENT_STRING</td><td style="border-width: 1px;">Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36)</td><td style="border-width: 1px;">The User Agent string to use for communication to upstream playlist, epg and icon urls</td></tr><tr><td style="border-width: 1px;">PLAYLIST_TIMEOUT</td><td style="border-width: 1px;">120  
</td><td style="border-width: 1px;">Download timeout for playlist files  
</td></tr><tr><td style="border-width: 1px;">EPG_TIMEOUT</td><td style="border-width: 1px;">120  
</td><td style="border-width: 1px;">Download timeout for EPG files  
</td></tr><tr><td style="border-width: 1px;">ICON_TIMEOUT</td><td style="border-width: 1px;">15  
</td><td style="border-width: 1px;">Download timeout for icon files  
</td></tr></tbody></table>

#### Proxy

<table border="1" id="bkmrk-name-default-usage-d" style="border-collapse: collapse; width: 100%;"><colgroup><col style="width: 22.9913%;"></col><col style="width: 27.6763%;"></col><col style="width: 49.3324%;"></col></colgroup><tbody><tr><td>Name  
</td><td>Default  
</td><td>Usage  
</td></tr><tr><td>DEBUG  
</td><td>True  
</td><td>Flask debugging  
</td></tr><tr><td>SOCKET_ADDRESS</td><td>0.0.0.0  
</td><td>Streaming proxy server's IP to bind the socket to</td></tr><tr><td>REPORTING_URL</td><td>http://localhost</td><td>Reporting (Management) server URL</td></tr><tr><td>REPORTING_PORT</td><td>8088  
</td><td>Reporting service port</td></tr><tr><td>REPORTING_TIMEOUT</td><td>5  
</td><td>Used for reporting connections</td></tr><tr><td>PROXY_NAME</td><td>IPTV-Proxy  
</td><td>Name to use when registering with the management server</td></tr><tr><td>INTERNAL_PROXY_URL</td><td>http://localhost</td><td>Internal URL to use when registering with the management server (to receive connection control/drop requests from the server) </td></tr><tr><td>INTERNAL_PROXY_PORT</td><td>8089  
</td><td>Internal port to use when registering with the management server (to receive connection control/drop requests from the server)</td></tr><tr><td>EXTERNAL_PROXY_URL</td><td>http://localhost</td><td>External URL to use when registering with the management server (for URL's inside of playlists and EPG's)</td></tr><tr><td>EXTERNAL_PROXY_PORT</td><td>8089  
</td><td>External port to use when registering with the management server (for URL's inside of playlists and EPG's)</td></tr><tr><td>USER_AGENT_STRING</td><td>Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36)</td><td>Defines the User Agent string to use for communication to upstream playlist, epg and icon urls</td></tr><tr><td>STREAM_TIMEOUT</td><td>15  
</td><td>Seconds before connections to upstream sources time out and a server error is reported to the client </td></tr></tbody></table>
