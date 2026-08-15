"""Browses the curated catalogue and installs a chosen ROM."""

import logging

import lvgl as lv
from mpos import Activity, SharedPreferences, TaskManager

from catalogue import Catalogue
from catalogue_filter import CatalogueFilter
from rom_download import InstallFailed, RomDownload

logger = logging.getLogger(__name__)

DEFAULT_INDEX_URL = (
    "https://raw.githubusercontent.com/paulinevos/rom-index/main/index/index.json"
)


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
        except Exception as error:
            # Deliberately broad: an escaping exception leaves the screen on
            # "Loading catalogue..." with no way to tell what went wrong.
            logger.error("catalogue load from %s failed: %s", index_url, error)
            self._show("Could not load catalogue: {}".format(error))
            self._render_reload_only()
            return
        self._catalogue = published.matching(self._filter)
        self._render_catalogue()

    def _render_catalogue(self):
        self._list.clean()
        self._add_reload_button()
        if self._catalogue.is_empty():
            self._show("No {} ROMs in the catalogue.".format(self._filter.describe()))
            return
        for entry in self._catalogue:
            self._add_entry_button(entry)
        self._show("{} {} ROMs.".format(len(self._catalogue), self._filter.describe()))

    def _render_reload_only(self):
        self._list.clean()
        self._add_reload_button()

    def _add_entry_button(self, entry):
        button = self._list.add_button(None, "{}\n{}".format(entry.title, entry.subtitle()))
        button.add_event_cb(
            lambda event: self._begin_install(entry), lv.EVENT.CLICKED, None)

    def _add_reload_button(self):
        button = self._list.add_button(lv.SYMBOL.REFRESH, "Reload catalogue")
        button.add_event_cb(lambda event: self._reload(), lv.EVENT.CLICKED, None)

    def _reload(self):
        if self._installing:
            return
        TaskManager.create_task(self._load_catalogue())

    def _begin_install(self, entry):
        if self._installing:
            return
        self._installing = True
        TaskManager.create_task(self._install(entry))

    async def _install(self, entry):
        try:
            destination = await RomDownload(entry, self._show_async).install()
            self._show("Installed {} to {}".format(entry.title, destination))
        except InstallFailed as error:
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
