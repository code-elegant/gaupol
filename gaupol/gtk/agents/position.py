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


"""Editing times and frames."""


import gaupol.gtk


class PositionAgent(gaupol.Delegate):

    """Editing times and frames."""

    # pylint: disable-msg=E0203,W0201

    def on_adjust_durations_activate(self, *args):
        """Lengthen or shorten durations."""

        page = self.get_current_page()
        dialog = gaupol.gtk.DurationAdjustDialog(self.window, self)
        self.flash_dialog(dialog)

    def on_transform_positions_activate(self, *args):
        """Change positions by linear two-point correction."""

        page = self.get_current_page()
        time_class = gaupol.gtk.TimeTransformDialog
        frame_class = gaupol.gtk.FrameTransformDialog
        cls = (time_class, frame_class)[page.edit_mode]
        dialog = cls(self.window, self)
        self.flash_dialog(dialog)

    def on_convert_framerate_activate(self, *args):
        """Convert framerate."""

        page = self.get_current_page()
        dialog = gaupol.gtk.FramerateConvertDialog(self.window, self)
        self.flash_dialog(dialog)

    def on_shift_positions_activate(self, *args):
        """Make subtitles appear earlier or later."""

        page = self.get_current_page()
        time_class = gaupol.gtk.TimeShiftDialog
        frame_class = gaupol.gtk.FrameShiftDialog
        cls = (time_class, frame_class)[page.edit_mode]
        dialog = cls(self.window, self)
        self.flash_dialog(dialog)
