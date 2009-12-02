# Copyright (C) 2007-2009 Osmo Salomaa
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
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# Gaupol. If not, see <http://www.gnu.org/licenses/>.

"""Automatic correcting of texts."""

import gaupol
import os
import re
import sys
_ = gaupol.i18n._


class TextAgent(gaupol.Delegate):

    """Automatic correcting of texts."""

    __metaclass__ = gaupol.Contractual
    _re_capitalizable = re.compile(r"^\W*(?<!\.\.\.)\w", re.UNICODE)

    def _capitalize_position(self, parser, pos):
        """Capitalize the first alphanumeric character from position.

        Return True if something was capitalized, False if not.
        """
        match = self._re_capitalizable.search(parser.text[pos:])
        if match is not None:
            i = pos + match.end() - 1
            prefix = parser.text[:i]
            text = parser.text[i:i + 1].capitalize()
            suffix = parser.text[i + 1:]
            parser.text = prefix + text + suffix
        return match is not None

    def _capitalize_text(self, parser, pattern, cap_next):
        """Capitalize all matches of pattern in parser's text.

        Return True if the text of the next subtitle should be capitalized.
        """
        try:
            a, z = parser.next()
        except StopIteration:
            return cap_next
        if pattern.get_field("Capitalize") == "Start":
            self._capitalize_position(parser, a)
        elif pattern.get_field("Capitalize") == "After":
            cap_next = not self._capitalize_position(parser, z)
        return self._capitalize_text(parser, pattern, cap_next)

    def _get_enchant_checker_require(self, language):
        assert gaupol.util.enchant_available()

    def _get_enchant_checker(self, language):
        """Return an enchant spell-checker for language.

        Raise enchant.error if dictionary instatiation fails.
        """
        import enchant.checker
        directory = os.path.join(gaupol.CONFIG_HOME_DIR, "spell-check")
        path = os.path.join(directory, "%s.dict" % language)
        try: dictionary = enchant.DictWithPWL(str(language), str(path))
        except IOError, (no, message):
            gaupol.util.print_write_io(sys.exc_info(), path)
            dictionary = enchant.Dict(str(language))
        # Sometimes enchant will initialize a dictionary that will not
        # actually work when trying to use it, hence check something.
        dictionary.check("gaupol")
        return enchant.checker.SpellChecker(dictionary, "")

    def _get_misspelled_indices(self, checker):
        """Return a list of misspelled indices in checker's text."""

        ii = [range(x.wordpos, x.wordpos + len(x.word)) for x in checker]
        return gaupol.util.flatten(ii)

    def _get_substitutions_ensure(self, value, patterns):
        assert len(value) <= len(patterns)

    def _get_substitutions(self, patterns):
        """Return a sequence of tuples of pattern, flags, replacement."""

        re_patterns = []
        for pattern in patterns:
            string = pattern.get_field("Pattern")
            flags = pattern.get_flags()
            replacement = pattern.get_field("Replacement")
            re_patterns.append((string, flags, replacement))
        return tuple(re_patterns)

    def _remove_leftover_hi(self, texts, parser):
        """Remove leftover hearing impaired spaces and junk."""

        texts = texts[:]
        for i, text in enumerate(texts):
            parser.set_text(text)
            # Remove leading and trailing spaces.
            self._replace_all(parser, r"(^\s+|\s+$)", "")
            # Consolidate multiple consequtive spaces.
            self._replace_all(parser, r" {2,}", " ")
            # Remove lines with no alphanumeric characters.
            self._replace_all(parser, r"^\W*$", "")
            # Remove empty lines.
            self._replace_all(parser, r"(^\n|\n$)", "")
            # Add space after dialogue dashes.
            self._replace_all(parser, r"^-(\S)", r"- \1")
            # Remove dialogue dashes if not present on other lines.
            self._replace_all(parser, r"^- (.*?^[^-])", r"\1")
            # Remove dialogue dashes from single-line subtitles.
            self._replace_all(parser, r"\A- ([^\n]*)\Z", r"\1")
            texts[i] = parser.get_text()
        return texts

    def _replace_all(self, parser, pattern, replacement):
        """Replace all matches of pattern in parser's text."""

        parser.set_regex(pattern)
        parser.replacement = replacement
        parser.replace_all()

    def break_lines_require(self, indices, *args, **kwargs):
        for index in (indices or []):
            assert 0 <= index < len(self.subtitles)

    @gaupol.deco.revertable
    def break_lines(self, indices, doc, patterns, length_func, max_length,
        max_lines, max_deviation=None, skip=False, max_skip_length=sys.maxint,
        max_skip_lines=sys.maxint, register=-1):
        """Break lines to fit defined maximum line length and count.

        indices can be None to process all subtitles. length_func should return
        the length of a string argument. max_length is the maximum length of
        lines as returned by length_func. max_lines may be violated to avoid
        violating max_length. max_deviation is the maximum allowed value of
        standard deviation of the line lengths divided by max_length. It is a
        float between 0 and 1, use None for a sane default. If skip is True,
        subtitles that do not violate or do not manage to reduce
        max_skip_length and max_skip_lines are skipped. re.error is raised if
        pattern or replacement is not proper.
        """
        new_indices = []
        new_texts = []
        patterns = [x for x in patterns if x.enabled]
        patterns = self._get_substitutions(patterns)
        patterns = [(re.compile(x, y), z) for x, y, z in patterns]
        liner = self.get_liner(doc)
        liner.break_points = patterns
        if max_deviation is not None:
            liner.max_deviation = max_deviation
        liner.max_length = max_length
        liner.max_lines = max_lines
        liner.set_length_func(length_func)
        re_tag = self.get_markup_tag_regex(doc)
        indices = indices or range(len(self.subtitles))
        for index in indices:
            subtitle = self.subtitles[index]
            liner.set_text(subtitle.get_text(doc))
            tagless_text = subtitle.get_text(doc)
            if re_tag is not None:
                tagless_text = re_tag.sub("", tagless_text)
            lines = tagless_text.split("\n")
            length = max(length_func(x) for x in lines)
            line_count = len(lines)
            if (length <= max_skip_length):
                if (line_count <= max_skip_lines):
                    # Skip subtitles that do not violate
                    # any of the defined skip conditions.
                    if skip: continue
            text = liner.break_lines()
            if re_tag is not None:
                tagless_text = re_tag.sub("", text)
            lines = tagless_text.split("\n")
            length_down = max(length_func(x) for x in lines) < length
            lines_down = len(lines) < line_count
            length_fixed = (length > max_skip_length) and length_down
            lines_fixed = (line_count > max_skip_lines) and lines_down
            if (not length_fixed) and (not lines_fixed):
                # Implicitly require reduction of violator
                # if only lines in violation are to be broken.
                if skip: continue
            if text != subtitle.get_text(doc):
                new_indices.append(index)
                new_texts.append(text)
        if not new_indices: return
        self.replace_texts(new_indices, doc, new_texts, register=register)
        self.set_action_description(register, _("Breaking lines"))

    def capitalize_require(self, indices, doc, pattern, register=-1):
        for index in (indices or []):
            assert 0 <= index < len(self.subtitles)

    @gaupol.deco.revertable
    def capitalize(self, indices, doc, patterns, register=-1):
        """Capitalize texts as defined by patterns.

        indices can be None to process all subtitles.
        Raise re.error if bad pattern or replacement.
        """
        new_indices = []
        new_texts = []
        parser = self.get_parser(doc)
        patterns = [x for x in patterns if x.enabled]
        indices = indices or range(len(self.subtitles))
        for indices in gaupol.util.get_ranges(indices):
            cap_next = False
            for index in indices:
                subtitle = self.subtitles[index]
                parser.set_text(subtitle.get_text(doc))
                if cap_next or (index == 0):
                    self._capitalize_position(parser, 0)
                    cap_next = False
                for pattern in patterns:
                    string = pattern.get_field("Pattern")
                    flags = pattern.get_flags()
                    parser.set_regex(string, flags, 0)
                    parser.pos = 0
                    args = (parser, pattern, cap_next)
                    cap_next = self._capitalize_text(*args)
                text = parser.get_text()
                if text != subtitle.get_text(doc):
                    new_indices.append(index)
                    new_texts.append(text)
        if not new_indices: return
        self.replace_texts(new_indices, doc, new_texts, register=register)
        self.set_action_description(register, _("Capitalizing texts"))

    def correct_common_errors_require(self, indices, *args, **kwargs):
        for index in (indices or []):
            assert 0 <= index < len(self.subtitles)

    @gaupol.deco.revertable
    def correct_common_errors(self, indices, doc, patterns, register=-1):
        """Correct common human and OCR errors  in texts.

        indices can be None to process all subtitles.
        Raise re.error if bad pattern or replacement.
        """
        new_indices = []
        new_texts = []
        parser = self.get_parser(doc)
        patterns = [x for x in patterns if x.enabled]
        re_patterns = self._get_substitutions(patterns)
        repeats = [x.get_field_boolean("Repeat") for x in patterns]
        indices = indices or range(len(self.subtitles))
        for index in indices:
            subtitle = self.subtitles[index]
            parser.set_text(subtitle.get_text(doc))
            for i, (string, flags, replacement) in enumerate(re_patterns):
                parser.set_regex(string, flags, 0)
                parser.replacement = replacement
                count = parser.replace_all()
                while repeats[i] and count:
                    count = parser.replace_all()
            text = parser.get_text()
            if text != subtitle.get_text(doc):
                new_indices.append(index)
                new_texts.append(text)
        if not new_indices: return
        self.replace_texts(new_indices, doc, new_texts, register=register)
        description = _("Correcting common errors")
        self.set_action_description(register, description)

    def remove_hearing_impaired_require(self, indices, *args, **kwargs):
        for index in (indices or []):
            assert 0 <= index < len(self.subtitles)

    @gaupol.deco.revertable
    def remove_hearing_impaired(self, indices, doc, patterns, register=-1):
        """Remove hearing impaired parts from subtitles.

        indices can be None to process all subtitles.
        Raise re.error if bad pattern or replacement.
        """
        new_indices = []
        new_texts = []
        parser = self.get_parser(doc)
        patterns = [x for x in patterns if x.enabled]
        re_patterns = self._get_substitutions(patterns)
        indices = indices or range(len(self.subtitles))
        for index in indices:
            subtitle = self.subtitles[index]
            parser.set_text(subtitle.get_text(doc))
            for string, flags, replacement in re_patterns:
                parser.set_regex(string, flags, 0)
                parser.replacement = replacement
                parser.replace_all()
            text = parser.get_text()
            if text != subtitle.get_text(doc):
                new_indices.append(index)
                new_texts.append(text)
        new_texts = self._remove_leftover_hi(new_texts, parser)
        if not new_indices: return
        self.replace_texts(new_indices, doc, new_texts, register=register)
        description = _("Removing hearing impaired texts")
        self.set_action_description(register, description)
        remove_indices = []
        for i, text in (x for x in enumerate(new_texts) if not x[1]):
            remove_indices.append(new_indices[i])
        if not remove_indices: return
        self.remove_subtitles(remove_indices, register=register)
        self.group_actions(register, 2, description)

    def spell_check_join_words_require(self, indices, *args, **kwargs):
        for index in (indices or []):
            assert 0 <= index < len(self.subtitles)
        assert gaupol.util.enchant_available()

    @gaupol.deco.revertable
    def spell_check_join_words(self, indices, doc, language, register=-1):
        """Join misspelled words based on spell-checker suggestions.

        Raise enchant.Error if dictionary instatiation fails.
        """
        new_indices = []
        new_texts = []
        re_multispace = re.compile(r" +")
        checker = self._get_enchant_checker(language)
        seeker = self._get_enchant_checker(language)
        indices = indices or range(len(self.subtitles))
        for index in indices:
            subtitle = self.subtitles[index]
            text = subtitle.get_text(doc)
            text = re_multispace.sub(" ", text)
            checker.set_text(unicode(text))
            while True:
                try: checker.next()
                except StopIteration: break
                text = checker.get_text()
                a = checker.wordpos
                z = checker.wordpos + len(checker.word)
                ok_with_prev = ok_with_next = False
                if checker.leading_context(1) == " ":
                    seeker.set_text(text[:a - 1] + text[a:])
                    poss = self._get_misspelled_indices(seeker)
                    ok_with_prev = not (a - 1) in poss
                if checker.trailing_context(1) == " ":
                    seeker.set_text(text[:z] + text[z + 1:])
                    poss = self._get_misspelled_indices(seeker)
                    ok_with_next = not a in poss
                # Join backwards or forwards if only either,
                # but not both, produce a correctly spelled result.
                if ok_with_prev and not ok_with_next:
                    checker.set_text(text[:a - 1] + text[a:])
                if ok_with_next and not ok_with_prev:
                    checker.set_text(text[:z] + text[z + 1:])
            new_text = unicode(checker.get_text())
            if new_text != text:
                new_indices.append(index)
                new_texts.append(new_text)
        if not new_indices: return
        self.replace_texts(new_indices, doc, new_texts, register=register)
        description = _("Joining words by spell-check suggestions")
        self.set_action_description(register, description)

    def spell_check_split_words_require(self, indices, *args, **kwargs):
        for index in (indices or []):
            assert 0 <= index < len(self.subtitles)
        assert gaupol.util.enchant_available()

    @gaupol.deco.revertable
    def spell_check_split_words(self, indices, doc, language, register=-1):
        """Split misspelled words based on spell-checker suggestions.

        Raise enchant.Error if dictionary instatiation fails.
        """
        new_indices = []
        new_texts = []
        re_multispace = re.compile(r" +")
        checker = self._get_enchant_checker(language)
        indices = indices or range(len(self.subtitles))
        for index in indices:
            subtitle = self.subtitles[index]
            text = subtitle.get_text(doc)
            text = re_multispace.sub(" ", text)
            checker.set_text(unicode(text))
            while True:
                try: checker.next()
                except StopIteration: break
                # Skip capitalized names.
                if checker.word.capitalize() == checker.word:
                    continue
                length = len(checker.word)
                suggestions = []
                for i, suggestion in enumerate(checker.suggest()):
                    if suggestion.find(" ") > 0:
                        if suggestion.replace(" ", "") == checker.word:
                            suggestions.append(suggestion)
                # Split word only if only one two-word suggestion found that
                # has all the same characters as the original unsplit word.
                if len(suggestions) != 1:
                    continue
                text = checker.get_text()
                a = checker.wordpos
                z = checker.wordpos + len(checker.word)
                checker.set_text(text[:a] + suggestions[0] + text[z:])
            new_text = unicode(checker.get_text())
            if new_text != text:
                new_indices.append(index)
                new_texts.append(new_text)
        if not new_indices: return
        self.replace_texts(new_indices, doc, new_texts, register=register)
        description = _("Splitting words by spell-check suggestions")
        self.set_action_description(register, description)