# Copyright (C) 2005-2007 Osmo Salomaa
#
# This file is part of Gaupol.
#
# Gaupol is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# Gaupol is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# Gaupol; if not, write to the Free Software Foundation, Inc., 51 Franklin
# Street, Fifth Floor, Boston, MA 02110-1301, USA.


"""User interface for a single project."""


import gtk
import os
import pango

from gaupol import enclib
from gaupol.base import Contractual, Observable
from gaupol.gtk import conf, util
from gaupol.gtk.index import *
from gaupol.gtk.tooltips import Tooltips
from gaupol.gtk.view import View
from gaupol.i18n import _
from gaupol.project import Project


class Page(Observable):

    """User interface for a single project.

    Instance variables:

        edit_mode:  MODE constant, currently used in the view
        project:    The associated Project
        tab_label:  gtk.Label contained in the tab_widget
        tab_widget: Widget to use in a notebook tab
        tooltips:   Markup-enabled Tooltips, always active
        untitle:    Title used if the main document is unsaved
        view:       The associated View

    Signals:

        close-request (page)

    This class represents one page in a notebook of user interfaces for
    projects. The view is updated automatically when project data changes.
    """

    __metaclass__ = Contractual
    _signals = ["close-request"]

    def __init__(self, counter=0):

        Observable.__init__(self)
        self.edit_mode = conf.editor.mode
        self.project = None
        self.tab_label = None
        self.tab_widget = None
        self.tooltips = Tooltips()
        self.untitle = _("Untitled %d") % counter
        self.view = View(conf.editor.mode)

        self._init_project()
        self._init_widgets()
        self._init_signal_handlers()
        self.update_tab_label()

    def _assert_store(self):
        """Assert that store's data matches project's."""

        mode = self.edit_mode
        store = self.view.get_model()
        assert len(store) == len(self.project.subtitles)
        for i in range(len(store)):
            subtitle = self.project.subtitles[i]
            assert store[i][1] == subtitle.get_start(mode)
            assert store[i][2] == subtitle.get_end(mode)
            assert store[i][3] == subtitle.get_duration(mode)
            assert store[i][4] == subtitle.main_text
            assert store[i][5] == subtitle.tran_text

    def _get_subtitle_value(self, row, col):
        """Get value of subtitle data corresponding to row and column."""

        mode = self.edit_mode
        subtitle = self.project.subtitles[row]
        if col == START:
            return subtitle.get_start(mode)
        if col == END:
            return subtitle.get_end(mode)
        if col == DURN:
            return subtitle.get_duration(mode)
        if col == MTXT:
            return subtitle.main_text
        if col == TTXT:
            return subtitle.tran_text
        raise ValueError

    def _get_tab_close_button(self):
        """Initialize and return a tab close button."""

        button = gtk.Button()
        args = gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU
        image = gtk.image_new_from_stock(*args)
        button.add(image)
        button.set_relief(gtk.RELIEF_NONE)
        button.set_focus_on_click(False)
        button.set_name("gaupol-tab-close-button")
        width, height = image.size_request()
        button.set_size_request(width + 2, height + 2)
        def request_close(*args):
            self.emit("close-request")
        button.connect("clicked", request_close)
        self.tooltips.set_tip(button, _("Close project"))
        return button

    def _init_project(self):
        """Initialize the project with proper properties."""

        limit = conf.editor.limit_undo
        levels = conf.editor.undo_levels
        undo_levels = (levels if limit else None)
        self.project = Project(conf.editor.framerate, undo_levels)

    def _init_signal_handlers(self):
        """Initialize signal handlers."""

        util.connect(self, "project", "main-file-opened")
        util.connect(self, "project", "main-texts-changed")
        util.connect(self, "project", "positions-changed")
        util.connect(self, "project", "subtitles-changed")
        util.connect(self, "project", "subtitles-inserted")
        util.connect(self, "project", "subtitles-removed")
        util.connect(self, "project", "translation-file-opened")
        util.connect(self, "project", "translation-texts-changed")

        def update_label(*args):
            self.update_tab_label()
        self.project.connect("main-file-opened", update_label)
        self.project.connect("main-file-saved", update_label)
        self.project.connect("notify::main_changed", update_label)
        self.project.connect("notify::tran_changed", update_label)

        def update_levels(*args):
            limit = conf.editor.limit_undo
            limit = (conf.editor.undo_levels if limit else None)
            self.project.undo_levels = limit
        conf.editor.connect("notify::limit_undo", update_levels)
        conf.editor.connect("notify::undo_levels", update_levels)

    def _init_widgets(self):
        """Initialize the widgets to use in a notebook tab."""

        self.tab_label = gtk.Label()
        self.tab_label.props.xalign = 0
        self.tab_label.set_ellipsize(pango.ELLIPSIZE_END)
        self.tab_label.set_max_width_chars(24)
        event_box = gtk.EventBox()
        event_box.add(self.tab_label)
        self.tooltips.set_tip(event_box, self.untitle)
        callback = self._on_tab_event_box_enter_notify_event
        event_box.connect("enter-notify-event", callback)
        button = self._get_tab_close_button()
        self.tab_widget = gtk.HBox(False, 4)
        self.tab_widget.pack_start(event_box, True, True, 0)
        self.tab_widget.pack_start(button, False, False, 0)
        self.tab_widget.set_data("button", button)
        self.tab_widget.set_data("event_box", event_box)
        self.tab_widget.show_all()

    def _on_project_main_file_opened(self, *args):
        """Reload the entire view."""

        self.reload_view_all()

    @util.asserted_return
    def _on_project_main_texts_changed(self, project, rows):
        """Reload and select main texts in rows."""

        assert rows
        self.reload_view(rows, [MTXT])
        self.view.select_rows(rows)

    @util.asserted_return
    def _on_project_positions_changed(self, project, rows):
        """Reload and select positions in rows."""

        assert rows
        self.reload_view(rows, [START, END, DURN])
        self.view.select_rows(rows)

    @util.asserted_return
    def _on_project_subtitles_changed(self, project, rows):
        """Reload and select subtitles in rows."""

        assert rows
        self.reload_view(rows, [START, END, DURN, MTXT, TTXT])
        self.view.select_rows(rows)

    def _on_project_subtitles_inserted_ensure(self, value, project, rows):
        self._assert_store()

    @util.asserted_return
    def _on_project_subtitles_inserted(self, project, rows):
        """Insert rows to the view and select them."""

        assert rows
        mode = self.edit_mode
        store = self.view.get_model()
        for row in sorted(rows):
            subtitle = self.project.subtitles[row]
            item = [row + 1,
                subtitle.get_start(mode),
                subtitle.get_end(mode),
                subtitle.get_duration(mode),
                subtitle.main_text,
                subtitle.tran_text]
            store.insert(row, item)
        self.view.set_focus(rows[0])
        self.view.select_rows(rows)

    def _on_project_subtitles_removed_ensure(self, value, project, rows):
        self._assert_store()

    @util.asserted_return
    def _on_project_subtitles_removed(self, project, rows):
        """Remove rows from the view."""

        assert rows
        store = self.view.get_model()
        for row in reversed(sorted(rows)):
            store.remove(store.get_iter(row))
        if self.project.subtitles:
            row = min(rows[0], len(self.project.subtitles) - 1)
            col = self.view.get_focus()[1]
            self.view.set_focus(row, col)

    def _on_project_translation_file_opened(self, *args):
        """Reload the entire view."""

        self.reload_view_all()

    @util.asserted_return
    def _on_project_translation_texts_changed(self, project, rows):
        """Reload and select translation texts in rows."""

        assert rows
        self.reload_view(rows, [TTXT])
        self.view.select_rows(rows)

    @util.asserted_return
    def _on_tab_event_box_enter_notify_event(self, *args):
        """Update the text in the tab tooltip."""

        main_file = self.project.main_file
        assert main_file is not None
        path = main_file.path
        format = main_file.format.display_name
        encoding = enclib.get_long_name(main_file.encoding)
        newline = main_file.newline.display_name
        tooltip  = _("<b>Path:</b> %s") % path
        tooltip += _("\n\n<b>Format:</b> %s") % format
        tooltip += _("\n<b>Encoding:</b> %s") % encoding
        tooltip += _("\n<b>Newlines:</b> %s") % newline
        event_box = self.tab_widget.get_data("event_box")
        self.tooltips.set_tip(event_box, tooltip)

    def get_main_basename(self):
        """Get the basename of the main document."""

        if self.project.main_file is not None:
            return os.path.basename(self.project.main_file.path)
        return self.untitle

    def get_translation_basename(self):
        """Get the basename of the translation document."""

        if self.project.tran_file is not None:
            return os.path.basename(self.project.tran_file.path)
        basename = self.get_main_basename()
        if self.project.main_file is not None:
            extension = self.project.main_file.format.extension
            if basename.endswith(extension):
                basename = basename[:-len(extension)]
        return _("%s translation") % basename

    def reload_view_ensure(self, value, indexes, cols):
        self._assert_store()

    def reload_view(self, rows, cols):
        """Reload the view in rows and columns."""

        mode = self.edit_mode
        store = self.view.get_model()
        for row, col in ((x, y) for x in rows for y in cols):
            value = self._get_subtitle_value(row, col)
            store[row][col] = value

    def reload_view_all_ensure(self, value):
        self._assert_store()

    def reload_view_all(self):
        """Clear and repopulate the entire view."""

        store = self.view.get_model()
        self.view.set_model(None)
        store.clear()
        mode = self.edit_mode
        for i, subtitle in enumerate(self.project.subtitles):
            store.append([i + 1,
                subtitle.get_start(mode),
                subtitle.get_end(mode),
                subtitle.get_duration(mode),
                subtitle.main_text,
                subtitle.tran_text])
        self.view.set_model(store)

    def update_tab_label(self):
        """Update the notebook tab label and return the title."""

        title = self.get_main_basename()
        if self.project.main_changed or self.project.tran_changed:
            title = "*%s" % title
        self.tab_label.set_text(title)
        return title
