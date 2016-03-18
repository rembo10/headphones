# Localization and internationalization

## How it works in Headphones

Currently, just `config` package of the Headphones implements multilanguage features. The core is common pythonic-i18n and l10n approach - the [`gettext`](https://docs.python.org/2/library/gettext.html) module.

There are just two things in the `config` package, required for i18n and i10n:

1. module `config\loc.py` - contains all settings, tunings and initialization code. All in one place.
2. function `_()`, imported from `loc.py`, and used in all modules of `config` package. This function marks string as translatable.

## How To

Here are several advices for new translators

<a id="update-catalog"/>

### Update Catalog

Assume, the catalog file (for example, `locale/fr/LC_MESSAGES/config.po`) is outdated, and you want to sync it with sources.

1. go to the `locale/` dir
2. run:

    ```sh
    ./rescan-config.sh
    ```

3. go to the `locale/fr/LC_MESSAGES/config.po`, and open it in your favourite po-edit tool (for example: POEDIT)
4. Choose in menu _Catalog > Update from POT file_, and update it from `locale/config.pot`
5. The app should show window with resulsts of updating
6. DONE

Your `config.po` file is actual now, and you could add translations to new strings.

Do not forget to compile `.po` files to `.mo` files.

### Modify sources

If you've made any changes in source files, modifying translated UI-visible strings, you should [update catalogs](#update-catalog) for each locale, and then fix broken translation-strings

### Add new language/culture

The simpliest way - use tool. We will use [**POEDIT**](https://poedit.net/).

First: get the **POT** file. You could get it from github (it is here: `locale/config.pot`), or brew it yourself:
1. go to the `locale/` dir
2. run:

    ```sh
    ./rescan-config.sh
    ```

Then:
1. Open **Poedit**
2. in menu: _File > New catalog from POT file..._
3. choose `config.pot`
4. Fill **language** and other fields in **New catalog** dialog
5. click **OK**, and in **Save dialog** choose directory `locale/<NEWLANG>/LC_MESSAGES/config.po` as the place for new translation. Here **<NEWLANG>** is the [ISO 639-1 code](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)


## See also:

* https://docs.python.org/2/library/gettext.html
* http://inventwithpython.com/blog/2014/12/20/translate-your-python-3-program-with-the-gettext-module/
* https://pymotw.com/2/gettext/