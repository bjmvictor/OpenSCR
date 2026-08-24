# Translating OpenSCR

OpenSCR keeps application translations in small UTF-8 JSON catalogs under
`locales/`. Brazilian Portuguese is the source language. English is the most
complete reference catalog.

## Add or update a language

1. Copy `locales/en.json` to the desired locale name, for example `de.json`.
2. Do not change the keys. They are the stable source strings used by the UI.
3. Translate each value while preserving placeholders such as `{date}`, `{time}`
   and `{computer}` exactly.
4. Add the display name and locale code to `OpenSCRCreator.setup_menu()`.
5. Validate the catalog:

   ```bash
   python -m json.tool locales/de.json
   ```

6. Test menus, project dialogs, the save-before-close dialog, narrow windows,
   and both light and dark themes.
7. Open a pull request describing the locale and translator name.

## Standard dialog buttons

OpenSCR also loads Qt's official `qtbase_<locale>.qm` catalog. It translates
standard buttons such as Save, Discard, Cancel, Open, and Close. If Qt has no
catalog for a new locale, application text will still be translated but some
system button labels may use the operating-system language.

## Review checklist

- JSON is valid UTF-8 without comments or trailing commas.
- Keys are unchanged and values are not empty.
- Keyboard shortcuts and file extensions are preserved.
- Text fits at the default and minimum window sizes.
- Technical names such as OpenSCR, `.scr`, Qt, and GitHub remain recognizable.

