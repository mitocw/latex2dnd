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
  -C, --can-reuse-labels
                        allow draggable labels to be reusable
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

LaTeX Macros
============

latex2dnd works by introducing three important new macros:

1. \DDlabel{label_name}{label_contents}  
    -- label_name = alphanumeric name (no spaces) for the draggable label
    -- label_contents = latex string for contents of label (math ok, e.g. $\sqrt{a+b}$)

2. \DDBox{box_name}{width}{height}{label_name}
    -- box_name = alphanumeric name (no spaces) for the target box
    -- width, height = size of target box
    -- label_name = name of label which gives correct label to go in this box (the answer)

3. \writeDDlabels[height]
    -- height = optional argument which specifies the height of the labels (widths are automatic)

Here is an example, giving the LaTeX code for a drag-and-drop question asking for the
quadratic equation roots formula to be filled in:

    \documentclass{article}
    \input{latex2dnd}
    
    \begin{document}
    
    % define drag-drop labels
    \DDlabel{term1}{$-b$}
    \DDlabel{term1p}{$+b$}
    \DDlabel{term2}{$b^2$}
    \DDlabel{dubexp}{$b^{2^\alpha}$}
    \DDlabel{dubsub}{$b_{2_\alpha}$}
    \DDlabel{fac}{$-4ac$}
    \DDlabel{facp}{$+4ac$}
    \DDlabel{ta}{$+2a$}
    \DDlabel{tam}{$-2a$}
    
    % shorthand macro to make all boxes the same size (6 by 4)
    \newcommand\DDB[2]{\DDbox{#1}{6ex}{4ex}{#2}}
    
    % the formula with boxes
    $$\lambda = \frac{\DDB{1}{term1}\pm \sqrt{\DDB{2}{term2}\DDB{3}{fac}}}{\DDB{4}{ta}}$$
    
    % output labels, with fixed box heights
    \writeDDlabels[4.3ex]
    
    \end{document}

Note that more labels are defined than just the correct ones.  This is the XML generated from the above example:

    <span>
      <customresponse>
       <drag_and_drop_input img="/static/images/quadratic/quadratic_dnd.png" target_outline="false" one_per_target="true" no_labels="true" label_bg_color="rgb(222, 139, 238)">
          <draggable id="term1" icon="/static/images/quadratic/quadratic_dnd_label1.png"/>
          <draggable id="term1p" icon="/static/images/quadratic/quadratic_dnd_label2.png"/>
          <draggable id="term2" icon="/static/images/quadratic/quadratic_dnd_label3.png"/>
          <draggable id="dubexp" icon="/static/images/quadratic/quadratic_dnd_label4.png"/>
          <draggable id="dubsub" icon="/static/images/quadratic/quadratic_dnd_label5.png"/>
          <draggable id="fac" icon="/static/images/quadratic/quadratic_dnd_label6.png"/>
          <draggable id="facp" icon="/static/images/quadratic/quadratic_dnd_label7.png"/>
          <draggable id="ta" icon="/static/images/quadratic/quadratic_dnd_label8.png"/>
          <draggable id="tam" icon="/static/images/quadratic/quadratic_dnd_label9.png"/>
          <target id="1" x="70" y="19" w="123" h="74"/>
          <!-- answer=term1 -->
          <target id="2" x="283" y="19" w="123" h="74"/>
          <!-- answer=term2 -->
          <target id="3" x="427" y="19" w="122" h="74"/>
          <!-- answer=fac -->
          <target id="4" x="249" y="129" w="122" h="74"/>
          <!-- answer=ta -->
        </drag_and_drop_input>
        <answer>
    caset = [{'term1': '1'}, {'term2': '2'}, {'fac': '3'}, {'ta': '4'}]
    ca = [ {"draggables": ca.keys(),"targets": ca.values(),"rule":"exact"} for ca in caset ]
    if draganddrop.grade(submission[0], ca):
        correct = ["correct"]
    else:
        correct = ["incorrect"]
    </answer>
      </customresponse>
      <solution>
        <img src="/static/images/quadratic/quadratic_dnd_sol.png"/>
      </solution>
    </span>

History
=======

* v0.9.0: python package, with unit tests
*     .1: add -C (can_reuse) flag
*     .2: improved box alignment and pixel position computation
*     .3: center labels in boxes; custom code when can_reuse=true
