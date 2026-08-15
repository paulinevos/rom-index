"""Browses the curated catalogue and installs a chosen ROM."""

import logging

import lvgl as lv
from mpos import (
    Activity,
    Intent,
    InputActivity,
    SharedPreferences,
    TaskManager,
)

from catalogue import Catalogue, CatalogueError
from catalogue_filter import CatalogueFilter
from itch_api import ItchApiError, ItchApiKey, MissingApiKey
from rom_download import InstallFailed, RomDownload

logger = logging.getLogger(__name__)

DEFAULT_INDEX_URL = (
    "https://raw.githubusercontent.com/paulinevos/rom-index/main/index.json"
)

API_KEY_SETTING = {
    "name": "itch.io API key",
    "key": "itch_api_key",
    "ui": "textarea",
    "description": "From itch.io/user/settings/api-keys. Scan it as a QR code to avoid typing.",
}


class RomInstallerActivity(Activity):

    def onCreate(self):
        self._preferences = SharedPreferences("com.paulinevos.rom_installer")
        self._preferences.load()
        self._catalogue = None
        self._filter = CatalogueFilter.from_preferences(self._preferences)
        self._installing = False

        screen = lv.obj()
        screen.set_style_pad_all(5, lv.PART.MAIN)

        self._title = lv.label(screen)
        self._title.set_text("ROM Installer")
        self._title.align(lv.ALIGN.TOP_LEFT, 0, 0)

        self._list = lv.list(screen)
        self._list.set_size(lv.pct(100), lv.pct(75))
        self._list.center()

        self._status = lv.label(screen)
        self._status.set_width(lv.pct(100))
        self._status.set_long_mode(lv.label.LONG_MODE.WRAP)
        self._status.align(lv.ALIGN.BOTTOM_LEFT, 0, 0)
        self._status.set_style_text_color(lv.color_hex(0x00FF00), lv.PART.MAIN)

        self.setContentView(screen)

    def onResume(self, screen):
        TaskManager.create_task(self._load_catalogue())

    async def _load_catalogue(self):
        self._show("Loading catalogue...")
        index_url = self._preferences.get_string("index_url", DEFAULT_INDEX_URL)
        self._filter = CatalogueFilter.from_preferences(self._preferences)
        try:
            published = await Catalogue.fetch(index_url)
        except (CatalogueError, OSError, ValueError) as error:
            self._show("Could not load catalogue: {}".format(error))
            self._render_settings_only()
            return
        self._catalogue = published.matching(self._filter)
        self._render_catalogue()

    def _render_catalogue(self):
        self._list.clean()
        self._add_settings_button()
        if self._catalogue.is_empty():
            self._show("No {} ROMs in the catalogue.".format(self._filter.describe()))
            return
        for entry in self._catalogue:
            self._add_entry_button(entry)
        self._show("{} {} ROMs.".format(len(self._catalogue), self._filter.describe()))

    def _render_settings_only(self):
        self._list.clean()
        self._add_settings_button()

    def _add_entry_button(self, entry):
        button = self._list.add_button(None, "{}\n{}".format(entry.title, entry.subtitle()))
        button.add_event_cb(
            lambda event: self._begin_install(entry), lv.EVENT.CLICKED, None)

    def _add_settings_button(self):
        button = self._list.add_button(lv.SYMBOL.SETTINGS, "itch.io API key")
        button.add_event_cb(lambda event: self._edit_api_key(), lv.EVENT.CLICKED, None)

    def _edit_api_key(self):
        intent = Intent(activity_class=InputActivity)
        intent.putExtra("setting", API_KEY_SETTING)
        intent.putExtra("value", self._preferences.get_string("itch_api_key", ""))
        self.startActivityForResult(intent, self._api_key_entered)

    def _api_key_entered(self, result):
        if not result.get("result_code"):
            return
        value = result.get("data", {}).get("value", "")
        self._preferences.edit().put_string("itch_api_key", value).commit()
        self._show("API key saved.")

    def _begin_install(self, entry):
        if self._installing:
            return
        self._installing = True
        TaskManager.create_task(self._install(entry))

    async def _install(self, entry):
        try:
            api_key = ItchApiKey.from_preferences(self._preferences)
            destination = await RomDownload(entry, api_key, self._show_async).install()
            self._show("Installed {} to {}".format(entry.title, destination))
        except MissingApiKey:
            self._show("Set your itch.io API key first (Settings below).")
        except (ItchApiError, InstallFailed) as error:
            self._show("{} failed: {}".format(entry.title, error))
        except Exception as error:
            logger.error("unexpected install failure for %s: %s", entry.title, error)
            self._show("{} failed: {}".format(entry.title, error))
        finally:
            self._installing = False

    async def _show_async(self, message):
        self._show(message)

    def _show(self, message):
        self._status.set_text(message)
