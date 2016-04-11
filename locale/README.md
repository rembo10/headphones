# Localization and internationalization

* **l10n** = localization
* **i18n** = internationalization

## How it works in Headphones

Currently, just `config` package of the Headphones implements multilanguage features. The core of i18n and l10n is the [`gettext`][gettext_python] module - the common python internationalization tool.

There are just two things in the `config` package, required for i18n and i10n:

1. module `config\loc.py` - contains all settings, tunings and initialization code. All in one place.
2. function `_()`, imported from `loc.py`, and used in all modules of `config` package. This function marks string as translatable.

The other stuff - `.po` and `.mo` files with translations.

## Restrictions

The UI of HeadPhones will use the same language, as the server. That means, that preferred culture of web clients will be ignored (yeah, it is saaaaad). The only way to apply culture settings: run the server with appropriate culture ([here](#run-hp-localized))

## How To

Here are several advices for new translators

<a id='run-hp-localized'>

### Run HP localized

HP uses `gettext`, and precisely it defines, which language will be used by HeadPhones. The detailed description of choosing the culture is here: [python docs][gettext_python]

**In short**: to specify the required culture/language, you could run the HP using following command (linux-systems):

```bash
$ LANG=fr python Headphones.py

# or:

$ LANG=en-US python Headphones.py
```

<a id="update-catalog"/>

### Update Catalog

Assume, you have modified a few lines of code of the HeadPhones, including some strings in `_('asdf')` blocks. Now the catalog file (`locale/config.pot`) and all translations (for example, `locale/fr/LC_MESSAGES/config.po`, and others) are outdated.

You want to fix translations.

1. go to the `locale/` dir
2. run:

    ```sh
    ./rescan-config.sh
    ```

  * the `.pot` file (the scaffold for all translations) is updated now.
3. go to the `locale/fr/LC_MESSAGES/config.po`, and open it in your favourite po-edit tool (for example: [POEDIT])
4. Choose in menu _Catalog > Update from POT file_, and update it from `locale/config.pot`
5. The app should show window with resulsts of updating
6. DONE

You could see, that new strings don't have translations, and old strings are marked for deletion.

Now you could:

1. translate new strings
2. save `.po` file
3. compile it to the `.mo` file ([POEDIT] does it automaticaly)
4. `push` your changes to the HP upstream

### Add new language/culture

The simpliest way - use tool. We will use **[POEDIT]**.

First: get the **POT** file. You could get it from github (it is here: `locale/config.pot`), or brew it yourself:
1. go to the `locale/` dir
2. run:

    ```sh
    ./rescan-config.sh
    ```

Then:

1. Open **[Poedit]**
2. in menu: _File > New catalog from POT file..._
3. choose `config.pot`
4. Fill **language** and other fields in **New catalog** dialog
5. click **OK**, and in **Save dialog** choose directory `locale/<NEWLANG>/LC_MESSAGES/config.po` as the place for new translation. Here **<NEWLANG>** is the [ISO 639-1 code](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)


## See also:

* [gettext][gettext_python]
* http://inventwithpython.com/blog/2014/12/20/translate-your-python-3-program-with-the-gettext-module/
* https://pymotw.com/2/gettext/

[gettext_python]:https://docs.python.org/2/library/gettext.html
[poedit]:http://poedit.net/