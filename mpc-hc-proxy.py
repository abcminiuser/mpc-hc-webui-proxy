#!/usr/bin/python

"""
    Media Player Classic - Home Cinema

    Web API proxy, see README.md for more details.

    By Dean Camera, dean [at] fourwalledcubicle [dot] com
        Released under a MIT license, see LICENSE.md
"""

import cgi
from http import server
import re
import requests
from urllib.parse import urlparse, parse_qs



# Port to serve on
PORT = 13579

# Port to communicate with the MPC-HC web API
MPCHC_PORT = 13580



class VariablesPage():
    TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <title>MPC-HC WebServer - Variables</title>
    </head>
    <body>
        <p id="file">{FILE}</p>
        <p id="filepatharg">{FILEPATHARG}</p>
        <p id="filepath">{FILEPATH}</p>
        <p id="filedirarg">{FILEDIRARG}</p>
        <p id="filedir">{FILEDIR}</p>
        <p id="state">{STATE}</p>
        <p id="statestring">{STATESTRING}</p>
        <p id="position">{POSITION}</p>
        <p id="positionstring">{POSITIONSTRING}</p>
        <p id="duration">{DURATION}</p>
        <p id="durationstring">{DURATIONSTRING}</p>
        <p id="volumelevel">{VOLUMELEVEL}</p>
        <p id="muted">{MUTED}</p>
        <p id="playbackrate">{PLAYBACKRATE}</p>
        <p id="size">{SIZE}</p>
        <p id="reloadtime">{RELOADTIME}</p>
        <p id="version">{VERSION}</p>
    </body>
</html>'''

    # List of MPC-HC state variables which should *not* be passed through the proxy.
    VARIABLE_REDACTIONS = [
        "file",
        "filepatharg",
        "filepath",
        "filedirarg",
        "filedir",
    ]


    def __init__(self, url):
        self._url = url


    def _get_mpchc_variables(self):
        player_variables = dict()

        try:
            response = requests.get("{}/variables.html".format(self._url), data=None, timeout=1)

            mpchc_variables = re.findall(r'<p id="(.+?)">(.+?)</p>', response.text)
            for var in mpchc_variables:
                player_variables[var[0]] = var[1].lower()
        except requests.exceptions.ConnectionError:
            pass

        return player_variables


    def render(self, params):
        player_variables = self._get_mpchc_variables()

        for k in self.VARIABLE_REDACTIONS:
            player_variables.pop(k)

        template_values = {
            "{FILE}"           : player_variables.get("file"          , ""),
            "{FILEPATHARG}"    : player_variables.get("filepatharg"   , ""),
            "{FILEPATH}"       : player_variables.get("filepath"      , ""),
            "{FILEDIRARG}"     : player_variables.get("filedirarg"    , ""),
            "{FILEDIR}"        : player_variables.get("filedir"       , ""),
            "{STATE}"          : player_variables.get("state"         , "0"),
            "{STATESTRING}"    : player_variables.get("statestring"   , "Stopped"),
            "{POSITION}"       : player_variables.get("position"      , "0"),
            "{POSITIONSTRING}" : player_variables.get("positionstring", "00:00:00"),
            "{DURATION}"       : player_variables.get("duration"      , "0"),
            "{DURATIONSTRING}" : player_variables.get("durationstring", "00:00:00"),
            "{VOLUMELEVEL}"    : player_variables.get("volumelevel"   , "0"),
            "{MUTED}"          : player_variables.get("muted"         , "0"),
            "{PLAYBACKRATE}"   : player_variables.get("playbackrate"  , "1"),
            "{SIZE}"           : player_variables.get("size"          , "1"),
            "{RELOADTIME}"     : player_variables.get("reloadtime"    , "0"),
            "{VERSION}"        : player_variables.get("version"       , "1.0.0.0"),
        }

        page_data = str(self.TEMPLATE)
        for k, v in template_values.items():
            page_data = page_data.replace(k, v)

        return page_data



class InfoPage(VariablesPage):
    TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <title>MPC-HC Web Server - Info</title>
    </head>
    <body>
        <p id="mpchc_np">&laquo; MPC-HC v{VERSION} &bull; {FILE} &bull; {POSITIONSTRING}/{DURATIONSTRING} &bull; {SIZE} &raquo;</p>
    </body>
</html>'''



class StatusPage(VariablesPage):
    TEMPLATE = '''OnStatus("{FILE}", "{STATESTRING}", {POSITION}, "{POSITIONSTRING}", {DURATION}, "{DURATIONSTRING}", {MUTED}, {VOLUMELEVEL}, "{FILE}")'''



class CommandPage():
    TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <title>MPC-HC Web Server - Command</title>
    </head>
    <body>
        {BODY}
    </body>
</html>'''

    # List of allowable MPC-HC commands, Commands not listed here will be rejected.
    ALLOWED_COMMAND_IDS = [
        889, # Play/Pause
        887, # Play
        888, # Pause
        890, # Stop
        891, # Frame-step
        892, # Frame-step back
        893, # Go To
        895, # Increase Rate
        894, # Decrease Rate
        896, # Reset Rate
        905, # Audio Delay +10 ms
        906, # Audio Delay -10 ms
        900, # Jump Forward (small)
        899, # Jump Backward (small)
        902, # Jump Forward (medium)
        901, # Jump Backward (medium)
        904, # Jump Forward (large)
        903, # Jump Backward (large)
        898, # Jump Forward (keyframe)
        897, # Jump Backward (keyframe)
        996, # Jump to Beginning
        922, # Next
        921, # Previous
    ]

    def __init__(self, url):
        self._url = url


    def render(self, params):
        try:
            command_id = int(params.get("wm_command", None)[0])
        except:
            command_id = None

        if not command_id in self.ALLOWED_COMMAND_IDS:
           return self.TEMPLATE.replace("{BODY}", "<p>This command has been disallowed.</p>")

        try:
            data = {
                "wm_command" : command_id
            }

            requests.get("{}/command.html".format(self._url), data=data, timeout=1)
        except requests.exceptions.ConnectionError:
            pass

        return ""



class RootPage():
    TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <title>MPC-HC Web Server</title>
    </head>
    <body>
        Proxy is running.
    </body>
</html>'''


    def __init__(self, url):
        self._url = url


    def render(self, params):
        return self.TEMPLATE



class RequestHandler(server.BaseHTTPRequestHandler):
    PAGES = {
       "/variables.html" : VariablesPage,
       "/info.html"      : InfoPage,
       "/status.html"    : StatusPage,
       "/command.html"   : CommandPage,
       "/"               : RootPage,
    }

    def _process_request(self, path, params):
        mpchc_base_url = "http://127.0.0.1:{}".format(MPCHC_PORT)

        page_handler = RequestHandler.PAGES.get(path)
        if page_handler is None:
             self.send_error(404, message="Invalid or unsupported MPC-HC Web API URL.")
             return

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        response = page_handler(mpchc_base_url).render(params)
        self.wfile.write(bytes(response, 'utf-8'))


    def do_POST(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD':'POST',
                     'CONTENT_TYPE':self.headers['Content-Type'],
                     })

        request_path = self.path
        request_params = dict()

        for k in form.keys():
            request_params[k] = [form[k].value]

        self._process_request(request_path, request_params)


    def do_GET(self):
        request = urlparse(self.path)

        request_path = request.path
        request_params = parse_qs(request.query)

        self._process_request(request_path, request_params)


if __name__ == "__main__":
    serveraddr = ('', PORT)
    srvr = server.HTTPServer(serveraddr, RequestHandler)
    srvr.serve_forever()
