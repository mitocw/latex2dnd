=========
latex2dnd
=========

Generate an edX drag-and-drop problem, complete with draggable labels, problem image, and
solution image, from an input latex file.

Installation
============

    pip install -e git+https://github.com/mitocw/latex2dnd.git#egg=latex2dnd

Note that pdftoppm is needed.  With osX and macbrew:

    brew install netpbm poppler

Usage
=====

Usage: latex2dnd [options] filename.tex

Options:

  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -v, --verbose         verbose messages
  -V, --very-verbose    very verbose messages
  -s, --skip-latex-compilation
                        skip latex compilation
  -d OUTPUT_DIR, --output-directory=OUTPUT_DIR
                        Directory name for output PNG files
  -c CONFIG_FILE, --config-file=CONFIG_FILE
                        configuration file to load
  -r RESOLUTION, --resolution=RESOLUTION
                        Resolution of PNG files in DPI

History
=======

* v0.9: python package
