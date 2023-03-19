import os
import base64
import logging
import socket

from requests import get
from http import HTTPStatus
from flask import Flask, Response, request, copy_current_request_context

# TODO: Respect log levels / debug parameter
logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)
logger = logging.getLogger(__name__)

__app__ = Flask('IPTV Stream Proxy')
__active_sockets__ = {}

# General default settings
__DEFAULT_DEBUG = False
__DEFAULT_SOCKET_ADDRESS = '0.0.0.0'

# Reporting default settings
__DEFAULT_REPORTING_URL = 'http://localhost'
__DEFAULT_REPORTING_PORT = 8088
__DEFAULT_REPORTING_TIMEOUT = 5

# Proxy registration default settings
__DEFAULT_PROXY_NAME = 'IPTV-Proxy'
__DEFAULT_INTERNAL_PROXY_URL = 'http://localhost'
__DEFAULT_INTERNAL_PROXY_PORT = 8089
__DEFAULT_EXTERNAL_PROXY_URL = 'http://localhost'
__DEFAULT_EXTERNAL_PROXY_PORT = 8089

# Upstream connection default settings
__DEFAULT_USER_AGENT_STRING = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36)'
__DEFAULT_STREAM_TIMEOUT = 15

_reportActionBegin = 'Begin'
_reportActionEnd = 'End'
_session_id_divider = '|'
_session_id_string = '{path}' + _session_id_divider + '{client}'

debug = bool(os.environ['DEBUG']) if 'DEBUG' in os.environ else __DEFAULT_DEBUG
socket_address = os.environ['SOCKET_ADDRESS'] if 'SOCKET_ADDRESS' in os.environ else __DEFAULT_SOCKET_ADDRESS

reporting_url = os.environ['REPORTING_URL'] if 'REPORTING_URL' in os.environ else __DEFAULT_REPORTING_URL
reporting_port = int(os.environ['REPORTING_PORT']) if 'REPORTING_PORT' in os.environ else __DEFAULT_REPORTING_PORT
reporting_timeout = int(os.environ['REPORTING_TIMEOUT']) if 'REPORTING_TIMEOUT' in os.environ else __DEFAULT_REPORTING_TIMEOUT

proxy_name = os.environ['PROXY_NAME'] if 'PROXY_NAME' in os.environ else __DEFAULT_PROXY_NAME
internal_proxy_url = os.environ['INTERNAL_PROXY_URL'] if 'INTERNAL_PROXY_URL' in os.environ else __DEFAULT_INTERNAL_PROXY_URL
internal_proxy_port = os.environ['INTERNAL_PROXY_PORT'] if 'INTERNAL_PROXY_PORT' in os.environ else __DEFAULT_INTERNAL_PROXY_PORT
external_proxy_url = os.environ['EXTERNAL_PROXY_URL'] if 'EXTERNAL_PROXY_URL' in os.environ else __DEFAULT_EXTERNAL_PROXY_URL
external_proxy_port = os.environ['EXTERNAL_PROXY_PORT'] if 'EXTERNAL_PROXY_PORT' in os.environ else __DEFAULT_EXTERNAL_PROXY_PORT

user_agent_string = os.environ['USER_AGENT_STRING'] if 'USER_AGENT_STRING' in os.environ else __DEFAULT_USER_AGENT_STRING
stream_timeout = int(os.environ['STREAM_TIMEOUT']) if 'STREAM_TIMEOUT' in os.environ else __DEFAULT_STREAM_TIMEOUT

logger.info(f'DEBUG: {debug}')
logger.info(f'SOCKET_ADDRESS: {socket_address}')

logger.info(f'REPORTING_URL: {reporting_url}')
logger.info(f'REPORTING_PORT: {reporting_port}')
logger.info(f'REPORTING_TIMEOUT: {reporting_timeout}')

logger.info(f'PROXY_NAME: {proxy_name}')
logger.info(f'INTERNAL_PROXY_URL: {internal_proxy_url}')
logger.info(f'INTERNAL_PROXY_PORT: {internal_proxy_port}')
logger.info(f'EXTERNAL_PROXY_URL: {external_proxy_url}')
logger.info(f'EXTERNAL_PROXY_PORT: {external_proxy_port}')

logger.info(f'USER_AGENT_STRING: {user_agent_string}')
logger.info(f'STREAM_TIMEOUT: {stream_timeout}')


def report(action, client, ua_string, url):
    reporting_endpoint = 'manager/report/'
    try:
        headers = {
            'action': action,
            'client': client,
            'user-agent': ua_string,
            'url': url,
            'proxy-name': proxy_name,
            'proxy-url-internal': internal_proxy_url,
            'proxy-port-internal': str(internal_proxy_port),
            'proxy-url-external': external_proxy_url,
            'proxy-port-external': str(external_proxy_port),
        }
        url = request.environ['REQUEST_URI'].removeprefix('/stream/start/')
        path = base64.b64decode(url.encode('utf-8')).decode('utf-8')
        session_id = _session_id_string.format(path=path, client=client)
        logger.info(f'REPORT: Reporting {action} {session_id}')
        get(f'{reporting_url}:{reporting_port}/{reporting_endpoint}', headers=headers, stream=True, allow_redirects=True, timeout=reporting_timeout)  # Stream better for async?
    except Exception as err:
        logger.exception(f'REPORT: Error reporting {action}', err)


@__app__.route(f'/stream/start/<path:path>')
def start(path):
    global __active_sockets__
    global _session_id_string
    global _session_id_divider

    url = request.environ['REQUEST_URI'].removeprefix('/stream/start/')
    path = base64.b64decode(url.encode('utf-8')).decode('utf-8')
    client = request.environ['X_REAL_IP'] if 'X-Real-Ip' in request.environ else None
    if not client:
        client = request.environ['X_FORWARDED_FOR'] if 'X-Forwarded-For' in request.environ else request.environ['REMOTE_ADDR']
    ua_string = request.environ['HTTP_USER_AGENT']
    logger.info(f'START: Received stream start request for {path} from {client}')        

    # TODO: Make customizable
    request_headers = {
        'User-Agent': user_agent_string,
        'Accept': '*/*',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Connection': 'keep-alive'    
    }
    try:
        stream = get(path, headers=request_headers, stream=True, allow_redirects=True, timeout=stream_timeout)
        # Save stream's socket FD for later usage (forced disconnect)
        fno = stream.raw.fileno()
        session = _session_id_string.format(path=path, client=client)
        __active_sockets__[session] = fno
        
        logger.info(f'START: Socket {fno} created for {session}')
        logger.info(f'[START]: Created socket {fno} and added it to the global list, currently active sockets:\n{__active_sockets__}')
    except Exception as err:
        logger.warning(f'START: Error starting stream session {path}: {err}')
        return Response(status=HTTPStatus.GATEWAY_TIMEOUT)

    response_headers = {
        'Content-Type': stream.headers['Content-Type'],
#       'Transfer-Encoding': 'chunked',
#       'Content-Type':'video/mp4',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Connection': 'keep-alive',
#       'Content-Disposition': 'inline',
    }
    response = Response(stream.raw, headers=response_headers)

    @response.call_on_close
    @copy_current_request_context
    def end_stream():
        client_ip = request.environ['REMOTE_ADDR']
        ua_string = request.environ['HTTP_USER_AGENT']
        url = request.environ['REQUEST_URI'].removeprefix('/stream/start/')
        path = base64.b64decode(url.encode('utf-8')).decode('utf-8')
        session_id = _session_id_string.format(path=path, client=client_ip, ua_string=ua_string)
        logger.info(f'START.ON_CLOSE: Ended {session_id}')
        stream.close()
        try:
            del __active_sockets__[session_id]
        except KeyError:
            logger.error(f'START.ON_CLOSE: Socket for {session_id} was not found')
        report(_reportActionEnd, client, ua_string, request.environ['PATH_INFO'])
        logger.info(f'[START.ON_CLOSE]: Deleted socket from global list, currently active sockets:\n{__active_sockets__}')
        return Response(status=HTTPStatus.MOVED_PERMANENTLY)  # TODO: Check if necessary

    logger.info(f"START: Returning stream for {path} to {client}")
    report(_reportActionBegin, client, ua_string, request.environ['PATH_INFO'])
    return response


@__app__.route(f'/stream/stop/<path:path>')
def stop(path):
    global __active_sockets__
    global _session_id_string
    global _session_id_divider

    saved_session_decoded = base64.b64decode(path).decode('utf-8')
    path, client = saved_session_decoded.split(_session_id_divider)
    session_id = _session_id_string.format(path=path, client=client)
    logger.info(f'STOP: Drop stream {session_id}')
    try:
        saved_socket = __active_sockets__[session_id]
        saved_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, fileno=saved_socket)
        saved_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)  # Block socket from reconnecting, check if good or not
        saved_socket.shutdown(socket.SHUT_RDWR)   
        saved_socket.close()
        logger.info(f'STOP: Socket {session_id} closed')
    except KeyError:
        logger.error(f'STOP: Socket for {session_id} was not found')
    return Response()


if __name__ == '__main__':
    __app__.run(host=socket_address, port=internal_proxy_port, debug=debug, use_reloader=debug, threaded=True)
