"""
DNDspec provides a simple text representation of an edX drag-and-drop problem.

This module provides a class to compile a *.dndspec file into a latex *.tex file
which latex2dnd can then process to generate the full XML and images for an
edX drag-and-drop problem.
"""

import os
import sys
import re
import string
from collections import OrderedDict

class DNDlabel(object):
    '''
    Represent a drag-and-drop draggable label.
    '''
    def __init__(self, tex, index_set=None, draggable_label_set=None, index=None, math_exp=None, draggable_label=None, 
                 ltype=None, verbose=False, distractor_variable="zzz", no_math=False):
        '''
        tex = label tex
        index_set = dict of current index values already used, with keys=index, val=DNDlabel objects
        draggable_label_set = dict of draggable label set by draggable label ids (val=DNDlabel objects), used to ensure unique draggable IDs
        index = suggested index number for this label
        math_exp = should be text formula parsable
        draggable_label = should be alpha only
        ltype = match or distractor
        no_math = boolean, suppress $ from \DDlabel if True
        '''
        self.tex = tex
        self.index = index
        self.index_set = index_set
        self.draggable_label_set = draggable_label_set
        self.ltype = ltype
        self.no_math = no_math
        self.verbose = verbose
        self.math_variable = None	# math variable for this label (used in formula sample string)

        if self.index in index_set:
            raise Exception("[dndspec] Error!  non-unique index number %d for label '%s', index_set=%s" % (index, tex, index_set))
        index_set[self.index] = self

        if not math_exp:
            math_exp = self.make_math_exp(tex)
        self.math_exp = math_exp

        self.make_math_variable()
        if self.ltype=="distractor":
            all_known_mathvars = [x.math_variable for x in list(self.draggable_label_set.values())]
            if self.math_variable is not None and (self.math_variable not in all_known_mathvars):
                self.math_variable = distractor_variable

        if not draggable_label:
            draggable_label = self.make_draggable_label(tex)
        while draggable_label in self.draggable_label_set:	# ensure draggable label is unique
            draggable_label += 'x'
        self.draggable_label = draggable_label
        self.draggable_label_set[draggable_label] = self

        if self.verbose:
            print("          [%s] Mapping label '%s' [%s] to variable '%s', math exp '%s' (%s)" % (index, tex, draggable_label,
                                                                                                  self.math_variable, self.math_exp,
                                                                                                  self.ltype))

        if self.no_math:
            self.ddlabel = "\\DDlabel[%s]{%s}{%s}" % (self.math_exp, self.draggable_label, self.tex)
        else:
            self.ddlabel = "\\DDlabel[%s]{%s}{$%s$}" % (self.math_exp, self.draggable_label, self.tex)
        self.formula_box = [ ]
        self.ddboxes = OrderedDict()	# key=index, val=ddbox string; first one uses self.index

    def make_math_variable(self):
        '''
        The math variable for this label may be used in the sample string.
        It is different from math_exp in that:
           - numbers may be left out (ie the math variable is None)
           - distractors can be mapped to some dummy variable (eg zzz)
           - exponents should not generate additional variables (eg x^2 --> variable "x")
           - simple math functions should not generate variables (TODO)
        '''
        m = re.match('[0-9\.]+', self.math_exp)	# positive numbers
        if m:
            self.math_variable = None
            return
        m = re.match('\-[0-9\.]+', self.math_exp)	# negative numbers
        if m:
            self.math_variable = None
            return
        m = re.match('[0-9]+/[0-9]+', self.math_exp)	# numerical fractions
        if m:
            self.math_variable = None
            return
        m = re.match('([A-Za-z]+)_\{*([0-9]+)\}*\^\{*([0-9]+)\}*$', self.math_exp)	# numerical subscript and exponent, e.g. d_1^{2}
        if m:
            self.math_variable = "%s_%s" % (m.group(1), m.group(2))
            return
        m = re.match('-*([a-zA-Z]+[a-zA-Z0-9]*)\^([0-9]+)$', self.math_exp)	# exponentiated variable
        if m:
            self.math_variable = m.group(1)
            return
        m = re.match('-*([a-zA-Z]+[a-zA-Z0-9]*)$', self.math_exp)	# negated variable, or variable
        if m:
            self.math_variable = m.group(1)
            return
        m = re.match('([A-Za-z]+)_([0-9]+)$', self.math_exp)	# numerical subscript, e.g. m_1
        if m:
            self.math_variable = self.math_exp
            return

    def get_new_index(self):
        '''
        Construct a unique new box index number, by taking max of self.index_set + 1
        Record new index in index_set
        '''
        new_index = max(self.index_set.keys())+1
        self.index_set[new_index] = self
        return new_index

    def make_ddbox(self, nwidth=1):
        '''
        This needs to be called when a label appears inside an expression.
        '''
        bwidth = "B" * nwidth
        if len(self.ddboxes)==0:
            index = self.index
        else:
            index = self.get_new_index()
            if self.verbose:
                print("[dndspec] generating new box index %d for label %s" % (index, self.tex))
        ddbox = " \\DD%s{%d}{%s} " % (bwidth, index, self.draggable_label)
        self.ddboxes[index] = ddbox
        self.formula_box.append( " ([%s]) " % index  )	# boxed expression for formulas
        return ddbox

    def make_math_exp(self, tex):
        if all([ x in string.ascii_letters or x in string.digits for x in tex]):
            return tex

        m = re.match('\\\\frac\{([0-9]+)}\{([0-9])+}$', tex)	# numerical fractions, e.g. \frac{1}{2} -> 1/2
        if m:
            return "%s/%s" % (m.group(1), m.group(2))
        m = re.match('([A-Za-z]+)_\{*([0-9]+)\}*\^\{*([0-9]+)\}*$', tex)	# numerical subscript and exponent, e.g. d_1^{2}
        if m:
            return "%s_%s^%s" % (m.group(1), m.group(2), m.group(3))
        m = re.match('([A-Za-z]+)\^\{*([0-9]+)\}*$', tex)	# numerical exponent, e.g. d^{2}
        if m:
            return "%s^%s" % (m.group(1), m.group(2))
        m = re.match('([A-Za-z]+)_\{*([0-9]+)\}*$', tex)	# numerical subscript, e.g. m_1
        if m:
            return "%s_%s" % (m.group(1), m.group(2))

        expr = ""
        idx = 0
        replp = {'+': 'plus',
                 '-': 'minus',
                 }
        while idx < len(tex):
            has_more = (idx+1 < len(tex))
            c = tex[idx]
            if c in string.ascii_letters or c in string.digits:
                expr += c
            elif c=='^' and has_more and (tex[idx+1] in string.digits):
                expr += c
            elif c=='-' and has_more and (tex[idx+1] in (string.digits + string.ascii_letters + '\\')):
                expr += c
            elif c in replp:
                expr += replp[c]
            else:
                expr += ""
            idx += 1
        if expr.startswith("_"):
            expr = "x" + expr
        while expr.endswith("_"):
            expr = expr[:-1]
        return expr

    def make_draggable_label(self, tex):
        if all([ x in string.ascii_letters for x in tex]):
            return tex
        expr = ""
        digit_names = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
        replp = {'+': 'plus',
                 '-': 'minus',
                 }
        for c in tex:
            if c in string.ascii_letters:
                expr += c
            elif c in string.digits:
                expr += digit_names[int(c)]
            elif c in replp:
                expr += replp[c]
            else:
                expr += ""
        if expr.startswith("_"):
            expr = "x" + expr
        while expr.endswith("_"):
            expr = expr[:-1]
        return expr

class DNDspec2tex(object):
    """
    Class which ingests a *.dndspec file and produces a latex *.tex file
    which latex2dnd can then process to generate the full XML and images for an
    edX drag-and-drop problem.

    A dndspec file shoud have this format:

    MATCH_LABELS: <comma separated list of labels appearing in EXPRESSION which should be made into boxes>
    DISTRACTOR_LABELS: <comma separated list of labels to be shown as draggables>
    ALL_LABELS: <comma separated list of MATCH and DISTRACTOR labels, in desired order, to be shown as draggables>
    MATH_EXP: <label>, <math_exp_for_label>
    BEGIN_EXPRESSION
          <latex expression containing MATCH labels>
    END_EXPRESSION
    CHECK_FORMULA: <text representation of correct formula, using MATCH labels, to be used for checking>
    CHECK_FORMULA_BOXES: <formula using [#], where [#] is the MATCH label number; needed if MATCH labels appear in more than one input box>

    """
    def __init__(self, sfn, output_fp=None, input_tex=None, verbose=False, default_dpi="300"):
        '''
        sfn = dndpsec filename (should be *.dndspec)
        '''
        self.input_filename = sfn
        self.verbose = verbose
        self.parse_file(sfn, input_tex=input_tex, default_dpi=default_dpi)
        self.assemble_labels()
        self.assemble_dnd_expression()
        self.assemble_dnd_formula()
        self.assemble_formula_tests()
        self.generate_tex()

        # output latex
        if not output_fp:
            ofn = sfn.replace('.dndspec', '.tex')
            output_fp = open(ofn, 'w')
        else:
            ofn = "output_fp"
        output_fp.write(self.dnd_tex)

        if self.verbose:
            print("Wrote dnd tex to %s" % ofn)
        self.tex_filename = ofn

    def parse_file(self, sfn, input_tex=None, default_dpi="300"):
        self.match_labels = []
        self.distractor_labels = []
        self.all_labels = []
        self.box_width = "8ex"
        self.box_height = "4ex"
        self.expression = ""
        self.check_formula = None
        self.check_formula_boxes = None
        self.label_delimeter = ","	# default is that MATCH_LABELS and ALL_LABELS are delimited by a comma
        self.comments = ""
        self.extra_header_tex = ""
        self.resolution = default_dpi
        self.dd_options = "HIDE_FORMULA_INPUT"
        self.formula_tests = []		# list of dicts specifying tests
        self.label_objects_by_box_index = {}	# key=index, val=DNDlabel object
        self.label_objects_by_draggable_id = {}	# key = draggable label, val=DNDlabel object
        self.label_math_exp = []	# list of (label, math_exp) as specified by user -- useful for giving numerical math_exp to text labels
        self.dnd_feedback = None
        self.dnd_feedback_tex = ""
        
        mode = None
        if not input_tex:
            lines = open(sfn)
        else:
            lines = input_tex.split('\n')

        def splitstr(s):
            strlist = [x.strip() for x in s.split(self.label_delimeter)]
            if '' in strlist:
                strlist.remove('')
            return strlist
            
        def space_pad(s):
            return ' ' + s + ' '

        def make_label_math_exp(s):
            label, math_exp = [x.strip() for x in s.split(',')]
            if 0 and (not label in (self.match_labels + self.distractor_labels)):
                msg = "[dndspec] cannot have MATH_EXP for unknown label %s" % label
                print(msg)
                raise Exception(msg)
            return (label, math_exp)

        def make_test_correct(s):
            test_formula = ' ' + s + ' '            
            return {'etype': 'correct', 'formula': test_formula}

        def make_test_incorrect(s):
            test_formula = ' ' + s + ' '            
            return {'etype': 'incorrect', 'formula': test_formula}

        keyword_table = {'BOX_WIDTH': {'field': 'box_width', 'func': None},
                         'BOX_HEIGHT': {'field': 'box_height', 'func': None},
                         'DELIMETER': {'field': 'label_delimeter', 'func': None},
                         'EXTRA_HEADER_TEX': {'field': 'extra_header_tex', 'func': None, 'add': True},
                         'MATCH_LABELS': {'field': 'match_labels', 'func': splitstr, 'add': True},
                         'DISTRACTOR_LABELS': {'field': 'distractor_labels', 'func': splitstr, 'add': True},
                         'ALL_LABELS': {'field': 'all_labels', 'func': splitstr, 'add': True},
                         'CHECK_FORMULA': {'field': 'check_formula', 'func': space_pad},
                         'CHECK_FORMULA_BOXES': {'field': 'check_formula_boxes', 'func': space_pad},
                         'TEST_CORRECT': {'field': 'formula_tests', 'func': make_test_correct, 'append': True},
                         'TEST_INCORRECT': {'field': 'formula_tests', 'func': make_test_incorrect, 'append': True},
                         'RESOLUTION': {'field': 'resolution', 'func': None},
                         'OPTIONS': {'field': 'dd_options', 'func': None},
                         'NAME': {'field': 'dnd_name', 'func': None},
                         'TITLE': {'field': 'dnd_title', 'func': None},
                         'MATH_EXP': {'field': 'label_math_exp', 'func': make_label_math_exp, 'append': True},
                         'FEEDBACK': {'field': 'dnd_feedback', 'func': None},
        }

        cnt = 0
        for k in lines:
            cnt += 1
            if mode=="in_expression":
                if k.startswith("END_EXPRESSION"):
                    mode = None
                    continue
                self.expression += k
                continue
            if k.startswith("BEGIN_EXPRESSION"):
                mode = "in_expression"
                continue
            if k.startswith('%') or k.startswith('#'):
                self.comments += "%" + k[1:]
                continue
            if len(k.strip())==0:	# skip empty lines
                continue

            kwfound = False
            for kw, kwinfo in list(keyword_table.items()):
                m = re.match('^%s:(.*)' % kw, k)
                if m:
                    val = m.group(1).strip()
                    val = (kwinfo['func'] or (lambda x: x))(val)
                    if kwinfo.get('append'):
                        getattr(self, kwinfo['field']).append(val)
                    elif kwinfo.get('add'):
                        setattr(self, kwinfo['field'], getattr(self, kwinfo['field']) + val)
                    else:
                        setattr(self, kwinfo['field'], val)
                    kwfound = True
                    break

            if not kwfound:
                msg = "[dndspec]: Cannot interpret line %d: %s" % (cnt, k)
                print(msg)
                raise Exception(msg)

        if self.verbose:
            print("[dndspec] box_width=%s" % self.box_width)
            print("[dndspec] from file %s read %d match labels, %d labels alltogether, and %d tests" % (sfn,
                                                                                                        len(self.match_labels),
                                                                                                        len(self.all_labels),
                                                                                                        len(self.formula_tests),
                                                                                                        ))
            
    def assemble_labels(self):
        '''
        Assemble labels tex.  Create self.all_labels list if needed.
         Also generate index for labels; number the match labels first 
        since those are the boxes in the DND expression.
        '''
        if not self.match_labels:
            raise Exception("[dndspec] Error!  No match labels specified")
        if not self.all_labels:
            self.all_labels = self.match_labels + self.distractor_labels
         # generate box index for labels ; distractor labels get dummy indices
        cnt = 0
        label_objs = OrderedDict()		# main dict of labels, with key=label tex, val=DNDlabel (with label_objs)
        user_specified_math_exp = dict(self.label_math_exp)

        def make_label(label, cnt, ltype):
            no_math = 'NO_MATH' in self.dd_options
            
            return DNDlabel(label,
                            index_set=self.label_objects_by_box_index,
                            draggable_label_set=self.label_objects_by_draggable_id,
                            index=cnt,
                            math_exp=user_specified_math_exp.get(label),
                            verbose=self.verbose,
                            no_math=no_math,
                            ltype=ltype)

        for label in self.match_labels:
            cnt += 1
            label_objs[label] = make_label(label, cnt, 'match')

        for label in self.all_labels:
            if not label in label_objs:
                cnt += 1
                label_objs[label] = make_label(label, cnt, "distractor")
                
        # double-check that all match_labels are in all_labels
        for label in self.match_labels:
            if not label in self.all_labels:
                msg = "Error in dndspec: label '%s' is in MATCH_LABELS but is missing from ALL_LABELS!" % label
                raise Exception(msg)

        # generate \DDlabel[math_exp]{draggable_label}{label_tex} for each label
        # label_tex is the tex for the label, specified in LABELS
        ltex = [ label_objs[label].ddlabel for label in self.all_labels ]

        self.label_objs = label_objs
        self.label_tex = '\n'.join(ltex)
        
    def escape_regexp(self, expr):
        '''
        Escape tex expression to avoid undesirable regular expression matches.
        '''
        expr = expr.replace('\\', '\\\\').replace('{', '\{').replace('^', '\^')
        expr = expr.replace('(', '\(').replace(')', '\)')
        expr = expr.replace('[', '\[').replace(']', '\]')
        expr = expr.replace('+', '\+')
        expr = expr.replace('|', '\|')
        expr = expr.replace('*', '\*')
        expr = expr.replace('}', '\}')
        # expr = expr.replace('_', '\_')
        return expr

    def assemble_dnd_expression(self):
        '''
        asssemble dnd expression from provided input.
        replace found match labels with \DDB{boxnum}{draggable_label}
        '''
        dnd_expression = self.expression
        self.commented_expression = '%' + self.expression.replace('\n', '\n%') + '\n%'
        for label in self.match_labels:
            lobj = self.label_objs[label]
            labre = "\s%s\s" % self.escape_regexp(label)
            try:
                matches = re.findall(labre, dnd_expression, flags=re.M)
            except Exception as err:
                print("Error in dndspec - failed to assemble DND expression, labre=%s, dnd_expression=%s" % (labre, dnd_expression))
                raise
            if not matches:
                msg = "--> [dndspec] WARNING: no matching label '%s' found in expression!" % label
                print(msg)
                print("expression = %s" % dnd_expression)
                print("label regular expression = %s" % labre)
                print("search: %s" % (re.search(labre, dnd_expression, flags=re.M)))
                raise Exception(msg)
            if self.verbose:
                print("[dndspec] found %d matches for label '%s' in expression" % (len(matches), label))
            for match in matches:
                # if a label appears multiple times in the expression, then
                # the the box numbers must change, to ensure all DDB box numbers
                # are unique
                def make_ddbox(m):
                    return lobj.make_ddbox(nwidth=1)
                dnd_expression = re.sub(labre, make_ddbox, dnd_expression, count=1, flags=re.M)
        self.dnd_expression = dnd_expression
        if self.verbose:
            print("[dndspec] dnd_expression=%s" % self.dnd_expression)

    def formula_to_boxed(self, formula, labelset=None, exit_on_failure=True, missing_ok=False):
        '''
        Convert a text math formula to one with index boxed [#] for each identified expression.
        If an expression appears more than once, then use the corresponding additional (already
        defined) DDBox index numbers.
        '''
        labelset = labelset or self.match_labels
        for label in labelset:
            lobj = self.label_objs[label]
            labre = "\s%s\s" % self.escape_regexp(lobj.math_exp)
            n_matches = 0
            index = 0
            while re.search(labre, formula):
                if index==0 and len(lobj.formula_box)==0:
                    lobj.make_ddbox()	# every label object should have a default box index [#], if not, make it
                if index < len(lobj.formula_box):
                    box = lobj.formula_box[index]
                else:
                    msg = "--> [dndspec] Error! %d matches already found for %s in formula %s, but just found another?" % (n_matches, label, formula)
                    print("    label math expression = %s" % labre)
                    print(msg)
                    raise Exception(msg)
                (formula, nmatch) = re.subn(labre, box, formula, count=1)
                n_matches += nmatch
                index += 1
            if not n_matches and (not missing_ok):
                msg = "--> [dndspec] WARNING: no matching math expression found for '%s' (%s) in formula" % (label, lobj.math_exp)
                print(msg)
                print("    formula = %s" % formula)
                print("    label math expression = %s" % labre)
                if exit_on_failure:
                    sys.exit(0)
                else:
                    raise Exception(msg)
        return formula

    def assemble_dnd_formula(self):
        '''
        assemble dnd formula from provided input.
        '''
        if not self.check_formula:
            self.dd_formula = ""
            return

        # make instructor formula expression using math_exp (instead of label) text
        self.math_check_formula = self.check_formula
        for label in self.match_labels:
            lobj = self.label_objs[label]
            labre = self.escape_regexp("\s%s\s" % label)
            try:
                self.math_check_formula = re.sub(labre, ' ' + lobj.math_exp + ' ', self.math_check_formula)
            except Exception as err:
                msg = "[dndspec] Failed to make instructor formula expression, label=%s, math_exp=%s, formula=%s" % (labre,
                                                                                                                     lobj.math_exp,
                                                                                                                     self.math_check_formula)
                print(msg)
                raise Exception(msg)

        # make check formula boxes if one not provided
        if not self.check_formula_boxes:
            self.check_formula_boxes = self.formula_to_boxed(self.math_check_formula, exit_on_failure=False)

        varlist = [ self.label_objs[label].math_variable for label in self.all_labels]
        varlist = [x for x in varlist if x is not None]	# remove None
        varlist = list(OrderedDict.fromkeys(varlist))	# remove duplicates
        self.formula_variables = ','.join(list(varlist))
        self.formula_nsamples = 20
        nvar = len(varlist)
        self.formula_sample_ranges = ','.join('1'*nvar) + ":" + ','.join(['20']*nvar) 
        self.formula_samples = "%s@%s\\#%d" % (self.formula_variables, self.formula_sample_ranges, self.formula_nsamples)
        if self.verbose:
            print("[dndspec] Generated check_formula_boxes '%s'" % self.check_formula_boxes)
            print("          Using %d variables: %s" % (nvar, self.formula_variables))
            print("          And taking %d samples" % (self.formula_nsamples))

        self.varlist = varlist
        self.dd_formula = "\\DDformula{ %s }{ %s }{ %s }{}" % (self.check_formula_boxes,
                                                               self.formula_samples,
                                                               self.math_check_formula)

    def extract_boxes_from_formula(self, boxed_formula):
        '''
        Extract list of indexes of boxes in formula, in string order, 
        e.g. "[1] * [2] / [3]" -> [1,2,3]
        '''
        boxes = re.findall('\[[0-9]+\]', boxed_formula)
        box_id_list = [int(x[1:-1]) for x in boxes]
        return box_id_list

    def assemble_formula_tests(self):
        '''
        assemble formula tests based on extra TEST_CORRECT and TEST_INCORRECT specifications
        uses \DDtest{correct|incorrect}{target_box_indexes}{draggable_label_names}
        '''
        test_tex = []
        if not self.check_formula:
            self.formula_test_tex = ""
            return

        check_formula_box_id_list = self.extract_boxes_from_formula(self.check_formula_boxes)
        for test in self.formula_tests:
            try:
                boxed_test_formula = self.formula_to_boxed(test['formula'],
                                                           labelset=self.all_labels,
                                                           exit_on_failure=False, missing_ok=True)
            except Exception as err:
                print("[dndspec] Failed to construct test for test_formula='%s'" % (test['formula']))
                raise

            # compare boxed_test_formula to check_formula_boxes to see which boxes the input is going into
            test_formula_box_id_list = self.extract_boxes_from_formula(boxed_test_formula)

            # translate test formula box id's into draggable label id's
            label_ids = [ self.label_objects_by_box_index[x].draggable_label for x in test_formula_box_id_list ]
            target_ids = check_formula_box_id_list
            test['target_ids'] = list(map(str, target_ids))
            test['draggable_ids'] = label_ids
            if not len(label_ids)==len(target_ids):
                msg = "[dndspec] Error generating test from formula '%s'" % test['formula']
                print(msg)
                print("          Found %d target ID's but %d draggable label ID's" % (len(target_ids), len(label_ids)))
                print("          Boxed test formula = %s" % boxed_test_formula)
                print("          Taget ID's: %s" % str(target_ids))
                print("          Draggable label ID's: %s" % str(label_ids))
                raise Exception(msg)
            test_tex.append('\\DDtest{%s}{%s}{%s}' % (test['etype'], ','.join(test['target_ids']), ','.join(test['draggable_ids'])))

        self.formula_test_tex = '\n'.join(test_tex)
        if self.verbose:
            print("[dndspec] Generated %d tests:" % len(test_tex))
            for test in test_tex:
                print("          %s" % test)

    def generate_tex(self):
        '''
        Generate tex output from dndspec.  Use template tex file.
        '''
        mydir = os.path.dirname(__file__)
        texpath = os.path.abspath(mydir + '/tex')
        template = open(texpath + "/dndspec_template.tex").read()

        if self.dnd_feedback is not None:
            self.dnd_feedback_tex = "\\DDfeedback{%s}" % self.dnd_feedback

        params = {'FILENAME': self.input_filename,
                  'LABELS': self.label_tex,
                  'COMMENTED_EXPRESSION': self.commented_expression,
                  'EXPRESSION': self.dnd_expression,
                  'DD_FORMULA': self.dd_formula,
                  'COMMENTS': self.comments,
                  'DD_FORMULA_TESTS': self.formula_test_tex,
                  'BOX_WIDTH': self.box_width,
                  'BOX_HEIGHT': self.box_height,
                  'EXTRA_HEADER_TEX': self.extra_header_tex,
                  'RESOLUTION': self.resolution,
                  'DD_OPTIONS': self.dd_options,
                  'DD_FEEDBACK': self.dnd_feedback_tex,
                  }
        for key, val in list(params.items()):
            try:
                template = template.replace('<' + key + '>', val)
            except Exception as err:
                raise Exception("[latex2dnd.dndspec] failed to substitute template key=%s, value=%s, err=%s" % (key, val, err))
                
        self.dnd_tex = template
                                 
#-----------------------------------------------------------------------------
# unit tests

def test_dndlabel1():
    ddl = DNDlabel(r"-\pi", index_set={}, draggable_label_set={}, ltype="match")
    assert ddl.math_exp=="-pi"
    assert ddl.draggable_label == "minuspi"
    
def test_dndlabel2():
    ddl = DNDlabel("-2", index_set={}, draggable_label_set={}, ltype="match")
    assert ddl.math_exp=="-2"
    assert ddl.draggable_label == "minustwo"
                                 
def test_dndlabel3():
    ddl = DNDlabel(r"- \pi", index_set={}, draggable_label_set={}, ltype="match")
    assert ddl.math_exp=="minuspi"
    assert ddl.draggable_label == "minuspi"
                                 
def test_dndlabel4():
    ddl = DNDlabel(r"\frac{1}{2}", index_set={}, draggable_label_set={}, ltype="match")
    assert ddl.math_exp=="1/2"
    assert ddl.draggable_label == "fraconetwo"
                                 
def test_dndlabel5():
    ddl = DNDlabel("d^{2}", index_set={}, draggable_label_set={}, ltype="match")
    assert ddl.math_exp=="d^2"
    assert ddl.math_variable=="d"
    assert ddl.draggable_label == "dtwo"
                                 
def test_dndlabel6():
    ddl = DNDlabel("m_1", index_set={}, draggable_label_set={}, ltype="match")
    print("math_exp for m_1 = %s" % ddl.math_exp)
    assert ddl.math_exp=="m_1"
    assert ddl.math_variable=="m_1"
    assert ddl.draggable_label == "mone"
                                 
def test_dndlabel6():
    ddl = DNDlabel("E_0^2", index_set={}, draggable_label_set={}, ltype="match")
    print("math_exp for E_0^2 = %s" % ddl.math_exp)
    assert ddl.math_exp=="E_0^2"
    assert ddl.math_variable=="E_0"
    assert ddl.draggable_label == "Ezerotwo"
                                 
def test_dndlabel7():
    ddl = DNDlabel("\mu_0", index_set={}, draggable_label_set={}, ltype="match")
    print("math_exp for \mu_0 = %s" % ddl.math_exp)
    assert ddl.math_exp=="mu0"
    assert ddl.math_variable=="mu0"
    assert ddl.draggable_label == "muzero"
    
def test_dndspec1():
    tex = r"""MATCH_LABELS: -\pi, B^\prime, d^2, v
ALL_LABELS: \pi, -\pi, v, v^2, d, d^2, B^\prime
BEGIN_EXPRESSION
\bea
	P =\exp\left( -\pi \mu \frac{ B^\prime d^2 }{ v \hbar } \right)
\nonumber
\eea
END_EXPRESSION
CHECK_FORMULA: -pi * ( Bprime * d^2 ) / ( v )
TEST_CORRECT: -pi * ( d^2 * Bprime ) / ( v )
    """
    from io import StringIO
    ofp = StringIO()
    dst = DNDspec2tex("stdin", input_tex=tex, output_fp=ofp, verbose=True)
    contents = str(ofp.getvalue())
    print(contents)
    assert( r'\DDtest{correct}{1,2,3,4}{minuspi,dtwo,Bprime,v}' in contents)
    assert( r'\DDformula{  ([1]) * ( ([2]) * ([3]) ) / ( ([4]) )  }{ pi,v,d,Bprime@1,1,1,1:20,20,20,20\#20 }{  -pi * ( Bprime * d^2 ) / ( v )  }{}' in contents)    
    assert( r'P =\exp\left( \DDB{1}{minuspi} \mu \frac{ \DDB{2}{Bprime} \DDB{3}{dtwo} }{ \DDB{4}{v} \hbar } \right)' in contents)
    assert( r'\DDlabel[Bprime]{Bprime}{$B^\prime$}' in contents)

def test_dndspec2():
    # check error case - bad label
    tex = r"""
MATCH_LABELS: 2, v, mu, B^\prime
ALL_LABELS: 1, 2, 3, B^\prime, mu, v, v^2
BEGIN_EXPRESSION
\bea
	x_0 = \sqrt{ 2 \frac{ v \hbar }{ \mu B^\prime } }
\nonumber
\eea
END_EXPRESSION
CHECK_FORMULA: 2 * v / ( mu * Bprime )
"""
    from io import StringIO
    ofp = StringIO()
    err = ''
    try:
        dst = DNDspec2tex("stdin", input_tex=tex, output_fp=ofp, verbose=True)
    except Exception as err:
        pass
    print(str(err))
    assert "WARNING: no matching label 'mu' found" in str(err)

def test_dndspec3():
    # ensure variable order is maintained in samples (for test stability)
    tex = r"""
MATCH_LABELS: G,m_1,m_2,R
BEGIN_EXPRESSION
\bea
	\frac{ G m_1 m_2 }{ R }
\nonumber
\eea
END_EXPRESSION
CHECK_FORMULA: G * m_1 * m_2 / R
"""
    from io import StringIO
    ofp = StringIO()
    err = ''
    dst = DNDspec2tex("stdin", input_tex=tex, output_fp=ofp, verbose=True)
    assert dst.varlist==['G', 'm_1', 'm_2', 'R']

def test_dndspec4():
    # ensure powers of variables do not lead to more variables to be sampled
    tex = r"""
MATCH_LABELS: G,m_1,m_2,R
ALL_LABELS: G,G^2, m_1,m_2,R, R^2
BEGIN_EXPRESSION
\bea
	\frac{ G m_1 m_2 }{ R }
\nonumber
\eea
END_EXPRESSION
CHECK_FORMULA: G * m_1 * m_2 / R
"""
    from io import StringIO
    ofp = StringIO()
    err = ''
    dst = DNDspec2tex("stdin", input_tex=tex, output_fp=ofp, verbose=True)
    assert dst.varlist==['G', 'm_1', 'm_2', 'R']

def test_dndspec5():
    # ensure ability to change delimeters, so labels may have commas
    tex = r"""
DELIMETER: ;
MATCH_LABELS: G; m_{1,2}; m_2; R
ALL_LABELS: G; G^2; m_{1,2}; m_2; R; R^2
BEGIN_EXPRESSION
\bea
	\frac{ G m_{1,2} m_2 }{ R }
\nonumber
\eea
END_EXPRESSION
CHECK_FORMULA: G * m12 * m_2 / R
"""
    from io import StringIO
    ofp = StringIO()
    err = ''
    dst = DNDspec2tex("stdin", input_tex=tex, output_fp=ofp, verbose=True)
    assert dst.varlist==['G', 'm12', 'm_2', 'R']

def test_dndspec6():
    # ensure math variables with numbers inbetween letters work properly
    tex = r"""
BOX_WIDTH: 12ex
% DELIMETER: ;
MATCH_LABELS: \frac{1}{\lambda_j}, \omega_j^{{2}}(0), \omega_j^{{2}}(t), \lambda_j
ALL_LABELS: \omega_j^{{2}}(0), \omega_j^{{2}}(t), \omega_j(0), \omega_j(t), \lambda_j, \lambda_j^2, \frac{1}{\lambda_j}, \frac{1}{\lambda_j^2}
BEGIN_EXPRESSION
\bea
 \ddot{\lambda_j} &= \frac{1}{\lambda_j} \frac{ \omega_j^{{2}}(0) }{\lambda_1\lambda_2\lambda_3}- \omega_j^{{2}}(t) \lambda_j 
\eea
END_EXPRESSION
CHECK_FORMULA: frac1lambdaj * omegaj20 + omegaj2t * lambdaj
"""
    from io import StringIO
    ofp = StringIO()
    err = ''
    dst = DNDspec2tex("stdin", input_tex=tex, output_fp=ofp, verbose=True)
    assert dst.varlist==['omegaj20', 'omegaj2t', 'zzz', 'lambdaj', 'frac1lambdaj']

def test_dndspec6():
    # ensure error is thrown if label in MATCH_LABELS is not in ALL_LABELS
    tex = r"""
MATCH_LABELS: a, b
ALL_LABELS: a, c, f, g
BEGIN_EXPRESSION
\bea
 a + b 
\eea
END_EXPRESSION
"""
    from io import StringIO
    ofp = StringIO()
    err = ''
    the_err = ""
    try:
        dst = DNDspec2tex("stdin", input_tex=tex, output_fp=ofp, verbose=True)
    except Exception as err:
        the_err = str(err)

    assert "in MATCH_LABELS but is missing from ALL_LABELS" in the_err
    

def test_dndspec7():
    # ensure variables include alpha+(mixed alpha numbers)
    tex = r"""
BOX_WIDTH: 14ex
% DELIMETER: ;
MATCH_LABELS: \frac{1}{\kappa^2}, \kappa^2, -\frac{1}{\kappa^3}
ALL_LABELS: -\frac{1}{\kappa^2}, \frac{1}{\kappa^2}, -\kappa, \kappa, -\kappa^2, \kappa^2, -\frac{1}{\kappa^3}, \frac{1}{\kappa^3}
BEGIN_EXPRESSION
\bea
        \epsilon &= \frac{3}{4} \left[ \frac{1}{\kappa^2} \right] +\frac{3}{4} \left[ \kappa^2 \right]
                        +\frac{\eta}{\sqrt{2\pi}} \left[ -\frac{1}{\kappa^3} \right]
\nonumber
\eea
END_EXPRESSION
CHECK_FORMULA: frac1kappa^2 + kappa^2 + 9 * ( -frac1kappa^3 )
TEST_CORRECT: kappa^2 + frac1kappa^2 + 9 * ( -frac1kappa^3 )
"""
    from io import StringIO
    ofp = StringIO()
    err = ''
    the_err = ""
    dst = DNDspec2tex("stdin", input_tex=tex, output_fp=ofp, verbose=True)
    assert dst.varlist==['frac1kappa', 'kappa']

def test_dndspec8():
    # test math_exp
    tex = r"""
MATCH_LABELS: Gravity Constant, Mass One , R
ALL_LABELS: Gravity Constant, Mass One , Mass Two , R
MATH_EXP: Gravity Constant, G
MATH_EXP: Mass One, m
MATH_EXP: Mass Two, m
BEGIN_EXPRESSION
\bea
	\frac{ Gravity Constant { Mass One } }{ R }
\nonumber
\eea
END_EXPRESSION
CHECK_FORMULA: G * m / R
"""
    from io import StringIO
    ofp = StringIO()
    err = ''
    dst = DNDspec2tex("stdin", input_tex=tex, output_fp=ofp, verbose=True)
    print(dst.dnd_tex)
    assert dst.label_objs['Gravity Constant'].math_exp=="G"
    assert dst.label_objs['Mass One'].math_exp=="m"
    assert dst.label_objs['Mass Two'].math_exp=="m"
    
