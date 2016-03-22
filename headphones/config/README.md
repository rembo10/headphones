# Headphones `config` package

I believe, there is required the good definition of the `config`-subsystem.

I am sure, someday, it will appear!

:octopus:

## Common tasks

### Add new option

The simplest way to meet with options - check the real examples in the `headphones/config/definitions/`, for example - `webui.py`, which defines options on the **Web UI** tab of the **Settings** page.

## API

There is just two public accessible classes:

* [`config`](config)
* [`typeconv`](typeconv)

Other classes are parts of the infrastructure of the `config` package, **you shouldn't use them in you code**. Here is a short description just for public accessible classes. Documentation for all other classes you could find in the python-doc.

<a id="config" />

### config

Implemented in `__init__.py`

#### Methods

<a id="typeconv" />

### typeconv

Types and typeconversion classes for options, for example: `path`, this type is designed for local paths on FS.
