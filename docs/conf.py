#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, os.path.abspath('../'))

import nella

extensions = ['sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon']

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

project = 'NellaPy'
copyright = '2017, Zini'
author = 'Zini'

version = nella.__VERSION__
release = nella.__VERSION__

language = None
exclude_patterns = []
pygments_style = 'sphinx'
todo_include_todos = False

# html_theme = 'alabaster'
html_theme = 'classic'
html_static_path = ['_static']

htmlhelp_basename = 'NellaPydoc'

intersphinx_mapping = {'python': ('https://docs.python.org/3/', None)}
