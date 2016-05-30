# Headphones `config` package

It is a draft of a documentation, but I am sure, someday somebody will write full developer documentation for the `config`-subsystem!

**Warning** : do not use submodules prefixed with underscore *_* (see [API](#api) for description)

:octocat: Have fun! :octocat:

## Common tasks

### Add new option

The simplest way to meet with options - check the real examples in the `headphones/config/definitions/`, for example - `webui.py`, which defines options on the **Web UI** tab of the **Settings** page.

<a id="api" />
## API

There is just two public accessible classes:

* [`config`](#config)
* [`typeconv`](#typeconv)

Other classes are parts of the infrastructure of the `config` package, **you shouldn't use them in you code**. Here is a short description just for public accessible classes. Documentation for all other classes you could find in the python-doc.

<a id="config" />

### config

Implemented in `__init__.py`

#### __getattr__

`x = config.API_KEY`

Provides old-style access to option's value.

<a id="typeconv" />

### typeconv

Types and typeconversion classes for options, for example: `path`, this type is designed for local paths on FS.


## Soft Chroot module

Configuration module uses features of `softchroot` module. Current implementation could be described in following rules:

**Disabled softchroot**

*ANYPATH => ANYPATH (no changes)
	* '/' => '/'
	* '/xdsf/' => '/xdsf/'

**Enabled softchroot**

Description:
CONFIG-VALUE => VALUE VISIBLE IN UI => CONFIG-VALUE

Lets assume, that `soft_chroot` is set to `/sc/`

* Any path out of chroot env will be redirected to chroot env:
	* '/' => '/' => '/sc/'
	* '/asdf/path/file' => '/asdf/path/file' => '/sc/asdf/path/file'
* Any path in chroot env will be shortened and longed back:
	* '/sc/' => '/' => '/sc/'
	* '/sc/logs/' => '/logs/' => '/sc/logs/'
	* '/sc/security/cert.file' => '/security/cert.file' => '/sc/security/cert.file'
* Empty paths will be converted to root
	* '' => '' => '/sc/'
	* '      ' => '' => '/sc/'
