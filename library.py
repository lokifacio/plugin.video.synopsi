try:
    import xbmc, xbmcgui, xbmcaddon
except ImportError:
    from tests import xbmc, xbmcgui, xbmcaddon
import threading
import time
import socket
import json
import re
import traceback
from app_apiclient import AppApiClient
from utilities import *
from cache import *


ABORT_REQUESTED = False


class RPCListener(threading.Thread):
    def __init__(self, cache):
        super(RPCListener, self).__init__()
        self.cache = cache
        self.apiclient = None
        self.sock = socket.socket()
        self.sock.settimeout(5)
        self.connected = False
        sleepTime = 100
        t = time.time()
        while sleepTime<500 and (not self.connected or ABORT_REQUESTED or xbmc.abortRequested):
            try:
                self.sock.connect(("localhost", 9090))  #   TODO: non default api port (get_api_port)
            except Exception, exc:
                xbmc.log('%0.2f %s' % (time.time() - t, str(exc)))
                xbmc.sleep(int(sleepTime))
                sleepTime *= 1.5
            else:
                xbmc.log('Connected to 9090')
                self.connected = True

        self.sock.setblocking(True)

    def process(self, data):
        pass

    def run(self):
        global ABORT_REQUESTED

        if not self.connected:
            xbmc.log('RPC Listener cannot run, there is not connection to xbmc')
            return False

        self.apiclient = AppApiClient.getDefaultClient()

        while True:
            data = self.sock.recv(8192)
            data = data.replace('}{', '},{')
            datapack='[%s]' % data
            # xbmc.log('SynopsiTV: {0}'.format(str(data)))
            try:
                data_json = json.loads(datapack)
            except ValueError, e:
                xbmc.log('RPC ERROR:' + str(e))
                xbmc.log('RPC ERROR DATA:' + str(data))
                continue

            for request in data_json:
                method = request.get("method")

                if method == "System.OnQuit":
                    ABORT_REQUESTED = True
                    break
                else:
                    self.process(request)

        self.sock.close()
        xbmc.log('Library thread end')

    def process(self, data):
        methodName = data['method'].replace('.', '_')
        method = getattr(self, methodName, None)
        if method == None:
            xbmc.log('Unknown method: ' + methodName)
            return

        xbmc.log('calling: ' + methodName)
        xbmc.log(str(data))
        
        #   Try to call that method
        try:
            method(data)
        except:
            xbmc.log('Error in method "' + methodName + '"')
            xbmc.log(traceback.format_exc())

        #   http://wiki.xbmc.org/index.php?title=JSON-RPC_API/v4


class RPCListenerHandler(RPCListener):
    """
    RPCListenerHandler defines event handler methods that are autotically called from parent class's RPCListener
    """
    def __init__(self, cache):
        super(RPCListenerHandler, self).__init__(cache)
        self.playerEvents = []

    #   NOT USED NOW
    def playerEvent(self, data):
        self.log(json.dumps(data, indent=4))

    def log(self, msg):
        xbmc.log('LIBRARY / ' + msg)

    def addorupdate(self, atype, aid):
        self.cache.addorupdate(atype, aid)

    def remove(self, atype, aid):
        self.cache.remove(atype, aid)

    def VideoLibrary_OnUpdate(self, data):
        item = data['params']['data']['item']
        self.addorupdate(item['type'], item['id'])

    def VideoLibrary_OnRemove(self, data):
        d = data['params']['data']
        self.remove(d['type'], d['id'])

    def Player_OnPlay(self, data):
        self.playerEvent(data)

    def Player_OnStop(self, data):
        self.playerEvent(data)

    def Player_OnSeek(self, data):
        self.playerEvent(data)
        pass

    def Player_OnPause(self, data):
        self.playerEvent(data)
        pass

    def Player_OnResume(self, data):
        self.playerEvent(data)
        pass

    def GUI_OnScreenSaverActivated(self, data):
        self.playerEvent(data)
        pass

    def GUI_OnScreenSaverDeactivated(self, data):
        self.playerEvent(data)
        pass

