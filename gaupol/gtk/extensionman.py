# Copyright (C) 2008 Osmo Salomaa
#
# This file is part of Gaupol.
#
# Gaupol is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# Gaupol is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# Gaupol.  If not, see <http://www.gnu.org/licenses/>.

"""Finding activating, storing and deactivating extensions."""

import gaupol
import inspect
import os
import re
import sys

__all__ = ("ExtensionManager", "ExtensionMetadata",)


class ExtensionManager(object):

    """Finding activating, storing and deactivating extensions."""

    _global_dir = os.path.join(gaupol.LIB_DIR, "extensions")
    _local_dir = os.path.join(gaupol.PROFILE_DIR, "extensions")
    _re_comment = re.compile(r"#.*$")

    def __init__(self, application):

        self.application = application
        self._active = {}
        self._metadata = {}

    def _find_extensions_in_directory(self, directory):
        """Find all extensions in directory and parse their metadata files."""

        is_metadata_file = lambda x: x.endswith(".gaupol-extension")
        for (root, dirs, files) in os.walk(directory):
            for name in filter(is_metadata_file, files):
                path = os.path.abspath(os.path.join(root, name))
                self._parse_metadata(path)

    def _parse_metadata(self, path):
        """Parse extension metadata file."""

        try: lines = gaupol.util.readlines(path, "utf_8", None)
        except UnicodeError: # Metadata file must be UTF-8.
            args = (sys.exc_info(), path, "utf_8")
            return gaupol.gtk.util.print_read_unicode(*args)
        lines = [self._re_comment.sub("", x) for x in lines]
        lines = [x.strip() for x in lines]
        metadata = ExtensionMetadata()
        metadata.path = path
        for line in (x for x in lines if x):
            if line.startswith("["): continue
            name, value = unicode(line).split("=", 1)
            name = (name[1:] if name.startswith("_") else name)
            metadata.set_field(name, value)
        self._store_metadata(path, metadata)

    def _store_metadata(self, path, metadata):
        """Store metadata to instance variables after validation."""

        def discard_extension(name):
            message = "Field '%s' missing in file '%s', dicarding extension."
            print message % (name, path)
        if not metadata.has_field("GaupolVersion"):
            return discard_extension("GaupolVersion")
        if not metadata.has_field("Module"):
            return discard_extension("Module")
        if not metadata.has_field("Name"):
            return discard_extension("Name")
        if not metadata.has_field("Description"):
            return discard_extension("Description")
        module = metadata.get_field("Module")
        self._metadata[module] = metadata

    def find_extensions(self):
        """Find all extensions and parse their metadata files."""

        self._find_extensions_in_directory(self._global_dir)
        self._find_extensions_in_directory(self._local_dir)

    def setup_extensions(self):
        """Setup all extensions configured as active."""

        for module_name in gaupol.gtk.conf.extensions.active:
            if not module_name in self._metadata:
                gaupol.gtk.conf.extensions.active.remove(module_name)
                continue
            metadata_path = self._metadata[module_name].path
            directory = os.path.dirname(metadata_path)
            sys.path.insert(0, directory)
            module = __import__(module_name, {}, {}, [])
            sys.path.pop(0)
            for attr_name in dir(module):
                if attr_name.startswith("_"): continue
                value = getattr(module, attr_name)
                if not inspect.isclass(value): continue
                if issubclass(value, gaupol.gtk.Extension):
                    extension = value()
                    extension.setup(self.application)
                    self._active[module_name] = extension

    def teardown_extensions(self):
        """Teardown all active extensions."""

        for name, extension in self._active.iteritems():
            extension.teardown(self.application)
        self._active = {}

    def update_extensions(self, page):

        for name, extension in self._active.iteritems():
            extension.update(self.application, page)


class ExtensionMetadata(gaupol.MetadataItem):

    """Extension metadata specified in a separate desktop-style file."""

    def __init__(self, fields=None):

        gaupol.MetadataItem.__init__(self, fields)
        self.path = None