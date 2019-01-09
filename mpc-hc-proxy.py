#!/usr/bin/env python3

"""
    Media Player Classic - Home Cinema (and Derivatives)
    Web API proxy, see README.md for more details.

    By Dean Camera, dean [at] fourwalledcubicle [dot] com
        Released under a MIT license, see LICENSE.md
"""

import re
import logging
import aiohttp
from aiohttp import web


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger(__name__)


# Port to serve on
PORT = 13579

# Port to communicate with the MPC-HC web API
MPCHC_PORT = 13580

# List of MPC-HC state variables which should *not* be passed through the proxy.
VARIABLE_REDACTIONS = [
    "file",
    "filepatharg",
    "filepath",
    "filedirarg",
    "filedir",
]

# List of allowable MPC-HC commands, Commands not listed here will be rejected.
ALLOWED_COMMAND_IDS = [
    889,  # Play/Pause
    887,  # Play
    888,  # Pause
    890,  # Stop
    891,  # Frame-step
    892,  # Frame-step back
    893,  # Go To
    895,  # Increase Rate
    894,  # Decrease Rate
    896,  # Reset Rate
    905,  # Audio Delay +10 ms
    906,  # Audio Delay -10 ms
    900,  # Jump Forward (small)
    899,  # Jump Backward (small)
    902,  # Jump Forward (medium)
    901,  # Jump Backward (medium)
    904,  # Jump Forward (large)
    903,  # Jump Backward (large)
    898,  # Jump Forward (keyframe)
    897,  # Jump Backward (keyframe)
    996,  # Jump to Beginning
    922,  # Next
    921,  # Previous
    909,  # Volume Mute
    908,  # Volume Down
    907,  # Volume Up
]


class MPCHC_Proxy_Client(object):
    def __init__(self, app, port, redactions=None, commands=None):
        self.port = port
        self.session = None
        self.redactions = redactions or []
        self.commands = commands or []

        app.router.add_get('/', self.handle_page_root)
        app.router.add_get('/variables.html', self.handle_page_variables)
        app.router.add_get('/info.html', self.handle_page_info)
        app.router.add_get('/status.html', self.handle_page_status)
        app.router.add_get('/command.html', self.handle_page_command)

    async def _send_command(self, command_id):
        if self.session is None:
            self.session = aiohttp.ClientSession()

        try:
            data = {
                "wm_command": command_id
            }

            with aiohttp.Timeout(1):
                await self.session.get('http://127.0.0.1:{}/command.html'.format(self.port), params=data)
        except Exception as e:
            pass

    async def _get_variables(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

        try:
            with aiohttp.Timeout(1):
                res = await self.session.get('http://127.0.0.1:{}/variables.html'.format(self.port))
                raw = await res.text()
        except Exception as e:
            return dict()

        mpchc_variables_raw = re.findall(r'<p id="(.+?)">(.+?)</p>', raw)
        mpchc_variables_parsed = dict()

        for (var_name, var_value) in mpchc_variables_raw:
            if var_name not in self.redactions:
                mpchc_variables_parsed[var_name] = var_value.lower()

        return mpchc_variables_parsed

    async def _render_template(self, page_template, template_values=None):
        mpchc_variables = await self._get_variables()

        if template_values is None:
            template_values = dict()

        template_values.update({
            "{FILE}": mpchc_variables.get("file", ""),
            "{FILEPATHARG}": mpchc_variables.get("filepatharg", ""),
            "{FILEPATH}": mpchc_variables.get("filepath", ""),
            "{FILEDIRARG}": mpchc_variables.get("filedirarg", ""),
            "{FILEDIR}": mpchc_variables.get("filedir", ""),
            "{STATE}": mpchc_variables.get("state", "0"),
            "{STATESTRING}": mpchc_variables.get("statestring", "Stopped"),
            "{POSITION}": mpchc_variables.get("position", "0"),
            "{POSITIONSTRING}": mpchc_variables.get("positionstring", "00:00:00"),
            "{DURATION}": mpchc_variables.get("duration", "0"),
            "{DURATIONSTRING}": mpchc_variables.get("durationstring", "00:00:00"),
            "{VOLUMELEVEL}": mpchc_variables.get("volumelevel", "0"),
            "{MUTED}": mpchc_variables.get("muted", "0"),
            "{PLAYBACKRATE}": mpchc_variables.get("playbackrate", "1"),
            "{SIZE}": mpchc_variables.get("size", "1"),
            "{RELOADTIME}": mpchc_variables.get("reloadtime", "0"),
            "{VERSION}": mpchc_variables.get("version", "1.0.0.0"),
        })

        page_data = str(page_template)
        for k, v in template_values.items():
            page_data = page_data.replace(k, v)

        return page_data

    async def handle_page_root(self, request):
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

        page_text = await self._render_template(TEMPLATE)
        return web.Response(text=page_text, content_type='text/html')

    async def handle_page_variables(self, request):
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

        page_text = await self._render_template(TEMPLATE)
        return web.Response(text=page_text, content_type='text/html')

    async def handle_page_info(self, request):
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

        page_text = await self._render_template(TEMPLATE)
        return web.Response(text=page_text, content_type='text/html')

    async def handle_page_status(self, request):
        TEMPLATE = '''OnStatus("{FILE}", "{STATESTRING}", {POSITION}, "{POSITIONSTRING}", {DURATION}, "{DURATIONSTRING}", {MUTED}, {VOLUMELEVEL}, "{FILE}")'''

        page_text = await self._render_template(TEMPLATE)
        return web.Response(text=page_text)

    async def handle_page_command(self, request):
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

        command_id = request.query.get('wm_command', None)

        template_values = dict()

        if command_id is None:
            template_values['{BODY}'] = 'Command not specified.'
        elif command_id in self.commands:
            template_values['{BODY}'] = 'Command {} disallowed by proxy.'.format(command_id)
        else:
            await self._send_command(command_id)
            template_values['{BODY}'] = 'Command {} accepted.'.format(command_id)

        page_text = await self._render_template(TEMPLATE, template_values=template_values)
        return web.Response(text=page_text, content_type='text/html')


if __name__ == "__main__":
    app = web.Application()
    client = MPCHC_Proxy_Client(app, port=MPCHC_PORT, redactions=VARIABLE_REDACTIONS, commands=ALLOWED_COMMAND_IDS)
    web.run_app(app, port=PORT)
