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

A working latex installation is also required.

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

Example
=======

Get quadratic.tex from the latex2dnd/testtex directory, and run this:

  latex2dnd quadratic.tex -r 220 -v

this will generate 220dpi images, with the files:

    quadratic_dnd.xml -- edX drag-and-drop question XML
    ./quadratic_dnd.png -- dnd problem image
    ./quadratic_dnd_sol.png -- dnd problem solution image
    9 dnd draggable image labels:
        ./quadratic_dnd_label1.png -- label '1'
        ./quadratic_dnd_label2.png -- label '2'
        ./quadratic_dnd_label3.png -- label '3'
        ./quadratic_dnd_label4.png -- label '4'
        ./quadratic_dnd_label5.png -- label '5'
        ./quadratic_dnd_label6.png -- label '6'
        ./quadratic_dnd_label7.png -- label '7'
        ./quadratic_dnd_label8.png -- label '8'
        ./quadratic_dnd_label9.png -- label '9'

Insert this into your course with (if you're using https://github.com/mitocw/latex2edx):

    \begin{edXproblem}{Latex to drag and drop test}{}
    
    \edXinclude{quadratic_dnd.xml}
    
    \end{edXproblem}    

and copy the png files to /static/images/quadratic/


History
=======

* v0.9: python package, with unit tests
