import glob

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent, PreferencesUpdateEvent, PreferencesEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from os.path import expanduser
import logging
import subprocess
import os
import re
import shlex

logger = logging.getLogger(__name__)

class SshExtension(Extension):

    def __init__(self):
        super(SshExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())
        self.subscribe(PreferencesUpdateEvent, PreferencesUpdateEventListener())
        self.subscribe(PreferencesEvent, PreferencesEventListener())

    def parse_ssh_config(self):
        home = expanduser("~")
        hosts = []

        try:
            with open(home + "/.ssh/config", "r") as ssh_config:
                for line in ssh_config:
                    line_lc = line.lower()

                    if line_lc.startswith("include"):
                        path = (home + "/.ssh/" + (line_lc.strip("include")).strip())
                        for fn in glob.iglob(path):
                            if os.path.isfile(fn):
                                with open(fn, "r") as cf:
                                    for ln in cf:
                                        lc = ln.lower()
                                        if lc.startswith(
                                                "host") and "*" not in lc and "keyalgorithms" not in lc:
                                            hosts.append(lc.strip("host").strip("\n").strip())

                    if line_lc.startswith("host") and "*" not in line_lc and "keyalgorithms" not in line_lc:
                        len_hosts=len(line_lc.strip("host").strip("\n").strip().split())
                        if len_hosts > 1:
                            hosts.extend(line_lc.strip("host").strip("\n").strip().split())
                        else:
                            hosts.append(line_lc.strip("host").strip("\n").strip())
        except:
            logger.debug("ssh config not found!")

        return hosts

    def parse_known_hosts(self):
        home = expanduser("~")
        hosts = []
        host_regex = re.compile("^[a-zA-Z0-9\\-\\.]*(?=(,.*)*\\s)")

        try:
            with open(home + "/.ssh/known_hosts", "r") as known_hosts:
                for line in known_hosts:
                    line_lc = line.lower()
                    match = host_regex.match(line_lc)

                    if match:
                        hosts.append(match.group().strip())
        except:
            logger.debug("known_hosts not found!")

        return hosts

    def launch_terminal(self, addr):
        logger.debug("Launching connection " + addr)
        shell = os.environ["SHELL"]
        home = expanduser("~")

        cmd = "ssh %CONN".replace("%CONN", addr)

        if self.terminal:
            subprocess.Popen([self.terminal, self.terminal_arg, shell, '-c', cmd, ';', shell], cwd=home)

class ItemEnterEventListener(EventListener):

    def on_event(self, event, extension):
        data = event.get_data()
        extension.launch_terminal(data)

class PreferencesUpdateEventListener(EventListener):

    def on_event(self, event, extension):

        if event.id == "ssh_launcher_terminal":
            extension.terminal = event.new_value
        elif event.id == "ssh_launcher_terminal_arg":
            extension.terminal_arg = event.new_value
        elif event.id == "ssh_launcher_terminal_cmd":
            extension.terminal_cmd = event.new_value
        elif event.id == "ssh_launcher_use_known_hosts":
            extension.use_known_hosts = event.new_value

class PreferencesEventListener(EventListener):

    def on_event(self, event, extension):
        extension.terminal = event.preferences["ssh_launcher_terminal"]
        extension.terminal_arg = event.preferences["ssh_launcher_terminal_arg"]
        extension.terminal_cmd = event.preferences["ssh_launcher_terminal_cmd"]
        extension.use_known_hosts = event.preferences["ssh_launcher_use_known_hosts"]

class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):
        icon = "images/icon.png"
        items = []
        arg = event.get_argument()
        hosts = extension.parse_ssh_config()
        if extension.use_known_hosts == "True":
            hosts += extension.parse_known_hosts()

        hosts = list(dict.fromkeys(hosts))
        hosts.sort()

        if arg is not None and len(arg) > 0:
            hosts = [x for x in hosts if arg in x]

        for host in hosts:
            items.append(ExtensionResultItem(icon=icon,
                                            name=host,
                                            description="Connect to '{}' with SSH".format(host),
                                            on_enter=ExtensionCustomAction(host, keep_app_open=False)))

        # If there are no results, let the user connect to the specified server.
        if len(items) <= 0:
            items.append(ExtensionResultItem(icon=icon,
                                            name=arg,
                                            description="Connect to {} with SSH".format(arg),
                                            on_enter=ExtensionCustomAction(arg, keep_app_open=False)))

        return RenderResultListAction(items)

if __name__ == '__main__':
    SshExtension().run()
