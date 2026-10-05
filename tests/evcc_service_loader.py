import configparser
import importlib.util
import os
import sys
import types

REPO_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SERVICE_SOURCE = os.path.join(REPO_DIR, "dbus-evcc.py")
REPO_CONFIG = os.path.join(REPO_DIR, "config.ini")


def _stub_venus_only_modules():
    # dbus, gi and velib_python exist only on Venus OS
    for name in ("dbus", "vedbus", "gi", "gi.repository"):
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules["vedbus"].VeDbusService = object
    sys.modules["vedbus"].VeDbusItemImport = object
    sys.modules["gi.repository"].GLib = types.SimpleNamespace()


def load_service_module():
    _stub_venus_only_modules()
    spec = importlib.util.spec_from_file_location("dbus_evcc", SERVICE_SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def new_service_without_dbus():
    # __init__ registers on dbus, so the instance is created without running it
    service_class = load_service_module().DbusEvccChargerService
    return service_class.__new__(service_class)


def parse_config(text):
    config = configparser.ConfigParser()
    config.read_string(text)
    return config
