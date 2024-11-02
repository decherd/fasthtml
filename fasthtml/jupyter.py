"""Use FastHTML in Jupyter notebooks"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/api/06_jupyter.ipynb.

# %% auto 0
__all__ = ['nb_serve', 'nb_serve_async', 'is_port_free', 'wait_port_free', 'show', 'render_ft', 'htmx_config_port', 'JupyUvi',
           'HTMX', 'ws_client']

# %% ../nbs/api/06_jupyter.ipynb
import asyncio, socket, time, uvicorn
from threading import Thread
from fastcore.utils import *
from .common import *
from .common import show as _show
from fastcore.parallel import startthread
try: from IPython.display import HTML,Markdown,display
except ImportError: pass

# %% ../nbs/api/06_jupyter.ipynb
def nb_serve(app, log_level="error", port=8000, host='0.0.0.0', **kwargs):
    "Start a Jupyter compatible uvicorn server with ASGI `app` on `port` with `log_level`"
    server = uvicorn.Server(uvicorn.Config(app, log_level=log_level, host=host, port=port, **kwargs))
    async def async_run_server(server): await server.serve()
    @startthread
    def run_server(): asyncio.run(async_run_server(server))
    while not server.started: time.sleep(0.01)
    return server

# %% ../nbs/api/06_jupyter.ipynb
async def nb_serve_async(app, log_level="error", port=8000, host='0.0.0.0', **kwargs):
    "Async version of `nb_serve`"
    server = uvicorn.Server(uvicorn.Config(app, log_level=log_level, host=host, port=port, **kwargs))
    asyncio.get_running_loop().create_task(server.serve())
    while not server.started: await asyncio.sleep(0.01)
    return server

# %% ../nbs/api/06_jupyter.ipynb
def is_port_free(port, host='localhost'):
    "Check if `port` is free on `host`"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        return True
    except OSError: return False
    finally: sock.close()

# %% ../nbs/api/06_jupyter.ipynb
def wait_port_free(port, host='localhost', max_wait=3):
    "Wait for `port` to be free on `host`"
    start_time = time.time()
    while not is_port_free(port):
        if time.time() - start_time>max_wait: return print(f"Timeout")
        time.sleep(0.1)

# %% ../nbs/api/06_jupyter.ipynb
def show(*s):
    "Same as fasthtml.components.show, but also adds `htmx.process()`"
    if IN_NOTEBOOK: return _show(*s, Script('if (window.htmx) htmx.process(document.body)'))
    return _show(*s)

# %% ../nbs/api/06_jupyter.ipynb
def render_ft():
    @patch
    def _repr_markdown_(self:FT): return to_xml(Div(self, Script('if (window.htmx) htmx.process(document.body)')))

# %% ../nbs/api/06_jupyter.ipynb
def htmx_config_port(port=8000):
    display(HTML('''
<script>
document.body.addEventListener('htmx:configRequest', (event) => {
    if(event.detail.path.includes('://')) return;
    htmx.config.selfRequestsOnly=false;
    event.detail.path = `${location.protocol}//${location.hostname}:%s${event.detail.path}`;
});
</script>''' % port))

# %% ../nbs/api/06_jupyter.ipynb
class JupyUvi:
    "Start and stop a Jupyter compatible uvicorn server with ASGI `app` on `port` with `log_level`"
    def __init__(self, app, log_level="error", host='0.0.0.0', port=8000, start=True, **kwargs):
        self.kwargs = kwargs
        store_attr(but='start')
        self.server = None
        if start: self.start()
        htmx_config_port(port)

    def start(self):
        self.server = nb_serve(self.app, log_level=self.log_level, host=self.host, port=self.port, **self.kwargs)

    def stop(self):
        self.server.should_exit = True
        wait_port_free(self.port)

# %% ../nbs/api/06_jupyter.ipynb
def HTMX(path="", app=None, host='localhost', port=8000, height="auto", link=False, iframe=True):
    "An iframe which displays the HTMX application in a notebook."
    if isinstance(path, (FT,tuple,Safe)):
        assert app, 'Need an app to render a component'
        route = f'/{unqid()}'
        res = path
        app.get(route)(lambda: res)
        path = route
    if isinstance(height, int): height = f"{height}px"
    scr = """{
        let frame = this;
        window.addEventListener('message', function(e) {
            if (e.source !== frame.contentWindow) return; // Only proceed if the message is from this iframe
            if (e.data.height) frame.style.height = (e.data.height+1) + 'px';
        }, false);
    }""" if height == "auto" else ""
    if link: display(HTML(f'<a href="http://{host}:{port}{path}" target="_blank">Open in new tab</a>'))
    if iframe:
        return HTML(f'<iframe src="http://{host}:{port}{path}" style="width: 100%; height: {height}; border: none;" onload="{scr}" ' + """allow="accelerometer; autoplay; camera; clipboard-read; clipboard-write; display-capture; encrypted-media; fullscreen; gamepad; geolocation; gyroscope; hid; identity-credentials-get; idle-detection; magnetometer; microphone; midi; payment; picture-in-picture; publickey-credentials-get; screen-wake-lock; serial; usb; web-share; xr-spatial-tracking"></iframe> """)

# %% ../nbs/api/06_jupyter.ipynb
def ws_client(app, nm='', host='localhost', port=8000, ws_connect='/ws', frame=True, link=True, **kwargs):
    path = f'/{nm}'
    c = Main('', cls="container", id=unqid())
    @app.get(path)
    def f():
        return Div(c, id=nm or '_dest', hx_trigger='load',
                   hx_ext="ws", ws_connect=ws_connect, **kwargs)
    if link: display(HTML(f'<a href="http://{host}:{port}{path}" target="_blank">open in browser</a>'))
    if frame: display(HTMX(path, host=host, port=port))
    def send(o): asyncio.create_task(app._send(o))
    c.on(send)
    return c
