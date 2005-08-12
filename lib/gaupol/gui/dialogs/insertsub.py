# Copyright (C) 2005 Osmo Salomaa
#
# This file is part of Gaupol.
#
# Gaupol is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Gaupol is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gaupol; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


"""Dialog for inserting new subtitles."""


try:
    from psyco.classes import *
except ImportError:
    pass

import gtk

from gaupol.gui.util import gui


class InsertSubtitleDialog(object):

    """Dialog for inserting new subtitles."""
    
    def __init__(self, parent):

        glade_xml = gui.get_glade_xml('insert-dialog.glade')
                            
        self._combo_box   = glade_xml.get_widget('position_combo_box')
        self._dialog      = glade_xml.get_widget('dialog'            )
        self._spin_button = glade_xml.get_widget('amount_spin_button')

        position_label = glade_xml.get_widget('position_label')
        position_label.set_mnemonic_widget(self._combo_box)

        amount_label = glade_xml.get_widget('amount_label')
        amount_label.set_mnemonic_widget(self._spin_button)

        # Set Insert button label.
        button = glade_xml.get_widget('insert_button')
        alignment = button.get_children()[0]
        hbox = alignment.get_children()[0]
        insert_label = hbox.get_children()[1]
        insert_label.set_text(_('_Insert'))
        insert_label.set_use_underline(True)

        self._dialog.set_transient_for(parent)
        self._dialog.set_default_response(gtk.RESPONSE_OK)
    
    def destroy(self):
        """Destroy the dialog."""
        
        self._dialog.destroy()
        
    def get_amount(self):
        """Get amount of subtitles to insert."""
        
        self._spin_button.update()

        return self._spin_button.get_value_as_int()

    def get_position(self):
        """Get position to insert subtitles to."""
        
        return self._combo_box.get_active()

    def set_amount(self, value):

        self._spin_button.set_value(value)

    def set_position(self, index):

        self._combo_box.set_active(index)

    def run(self):
        """Show and run the dialog."""
        
        self._dialog.show()
        
        return self._dialog.run()        
