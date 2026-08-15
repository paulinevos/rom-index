"""The console platforms the Retro Core Launcher browses.

The subdirectory names and accepted extensions here mirror the extras that
com.micropythonos.retrocore_launcher passes to RetroGoLauncher. A ROM landing
under any other name is invisible to the launcher, so this list is the
authority on where a download is allowed to go.
"""


class UnknownPlatform(Exception):
    pass


class RomPlatform:

    _SUBDIRECTORIES = {
        "nes": ("Nintendo Entertainment System", (".nes", ".fc", ".fds", ".nsf", ".zip")),
        "gb": ("Gameboy", (".gb", ".gbc", ".zip")),
        "gbc": ("Gameboy Color", (".gbc", ".gb", ".zip")),
        "sms": ("Sega Master System", (".sms", ".sg", ".zip")),
        "gg": ("Sega Game Gear", (".gg", ".zip")),
        "col": ("ColecoVision", (".col", ".rom", ".zip")),
        "pce": ("PC Engine", (".pce", ".zip")),
        "lnx": ("Atari Lynx", (".lnx", ".zip")),
        # Game & Watch takes no .zip: retro-go registers it as "gw" only
        # (launcher/main/applications.c), unlike every other console here.
        "gw": ("Game & Watch", (".gw",)),
    }

    def __init__(self, subdirectory):
        known = self._SUBDIRECTORIES.get(subdirectory)
        if not known:
            raise UnknownPlatform("no launcher directory for '{}'".format(subdirectory))
        self.subdirectory = subdirectory
        self.display_name = known[0]
        self._extensions = known[1]

    def accepts(self, filename):
        lowered = filename.lower()
        for extension in self._extensions:
            if lowered.endswith(extension):
                return True
        return False

    def rejection_reason(self, filename):
        return "{} cannot run {} files".format(self.display_name, filename.rsplit(".", 1)[-1])
