import copy
import json


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def vendor_settings(config):
    """Resolve each vendor's settings on top of the shared defaults."""
    defaults = config["defaults"]
    resolved = {}
    for name in sorted(config["vendors"]):
        override = config["vendors"][name]
        settings = copy.copy(defaults)
        settings["label_map"].update(override.get("label_map", {}))
        for key, value in override.items():
            if key != "label_map":
                settings[key] = value
        resolved[name.strip().lower()] = settings
    return resolved
