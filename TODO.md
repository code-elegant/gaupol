Gaupol 0.28.3/0.29
==================

 * [X] Only force theme variant if `dark_theme` in config file is
       `true`, thus respecting any global settings (#753315)
 * [ ] Make `GTK_THEME=Adwaita:dark gaupol` work correctly
 * [ ] Have the text view right-click spell-check language menu
       set the language permanently
 * [ ] Move the "Use Shift+Return for line-break" instruction so that
       it doesn't obstruct what is being edited

Gaupol 1.0
==========

 * Apply new GNOME goals and migrate away from deprecated widgets
   - <http://wiki.gnome.org/HowDoI/>
 * Use CSS for zebra colors (public named colors added in GTK+ 3.14!)
     * <http://bugzilla.gnome.org/show_bug.cgi?id=709617#c1>
     * <http://git.gnome.org/browse/gtk+/tree/gtk/theme/Adwaita>
 * Restore speech recognition? (#757743)
 * Allow using multiple dictionaries for spell-check
 * Add a GStreamer-based audio waveform display