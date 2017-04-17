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
                 ltype=None, verbose=False, distractor_variable="zzz"):
        '''
        tex = label tex
        index_set = dict of current index values already used, with keys=index, val=DNDlabel objects
        draggable_label_set = dict of draggable label set by draggable label ids (val=DNDlabel objects), used to ensure unique draggable IDs
        index = suggested index number for this label
        math_exp = should be text formula parsable
        draggable_label = should be alpha only
        ltype = match or distractor
        '''
        self.tex = tex
        self.index = index
        self.index_set = index_set
        self.draggable_label_set = draggable_label_set
        self.ltype = ltype
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
            all_known_mathvars = [x.math_variable for x in self.draggable_label_set.values()]
            if self.math_variable is not None and (self.math_variable not in all_known_mathvars):
                self.math_variable = distractor_variable

        if not draggable_label:
            draggable_label = self.make_draggable_label(tex)
        while draggable_label in self.draggable_label_set:	# ensure draggable label is unique
            draggable_label += 'x'
        self.draggable_label = draggable_label
        self.draggable_label_set[draggable_label] = self

        if self.verbose:
            print "          [%s] Mapping label '%s' [%s] to variable '%s', math exp '%s' (%s)" % (index, tex, draggable_label,
                                                                                                  self.math_variable, self.math_exp,
                                                                                                  self.ltype)

        self.ddlabel = "\\DDlabel[%s]{%s}{$%s$}" % (self.math_exp, self.draggable_label, self.tex)
        self.formula_box = " ([%s]) " % self.index
        self.ddboxes = {}	# key=index, val=ddbox string; first one uses self.index

    def make_math_variable(self):
        '''
        The math variable for this label may be used in the sample string.
        It is different from math_exp in that:
           - numbers may be left out (ie the math variable is None)
           - distractors can be mapped to some dummy variable (eg zzz)
           - exponents should not generate additional variables (eg x^2 --> variable "x")
           - simple math functions should not generate variables (TODO)
        '''
        m = re.match('[0-9]+', self.math_exp)
        if m:
            self.math_variable = None
            return
        m = re.match('-*([a-zA-Z]+[0-9]*)\^([0-9]+)', self.math_exp)
        if m:
            self.math_variable = m.group(1)
            return
        m = re.match('-*([a-zA-Z]+[0-9]*)', self.math_exp)
        if m:
            self.math_variable = m.group(1)
            return
        self.math_variable = self.math_exp

    def get_new_index(self):
        '''
        Construct a unique new box index number, by taking max of self.index_set + 1
        Record new index in index_set
        '''
        new_index = max(self.index_set.keys())+1
        self.index_set[new_index] = self
        return new_index

    def make_ddbox(self, nwidth=1):
        bwidth = "B" * nwidth
        if len(self.ddboxes)==0:
            index = self.index
        else:
            index = self.get_new_index()
            if self.verbose:
                print "[dndspec] generating new box index %d for label %s" % (index, self.tex)
        ddbox = " \\DD%s{%d}{%s} " % (bwidth, index, self.draggable_label)
        self.ddboxes[index] = ddbox
        return ddbox

    def make_math_exp(self, tex):
        if all([ x in string.letters or x in string.digits for x in tex]):
            return tex
        expr = ""
        idx = 0
        replp = {'+': 'plus',
                 '-': 'minus',
                 }
        while idx < len(tex):
            has_more = (idx+1 < len(tex))
            c = tex[idx]
            if c in string.letters or c in string.digits:
                expr += c
            elif c=='^' and has_more and (tex[idx+1] in string.digits):
                expr += c
            elif c=='-' and has_more and (tex[idx+1] in (string.digits + string.letters + '\\')):
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
        if all([ x in string.letters for x in tex]):
            return tex
        expr = ""
        digit_names = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
        replp = {'+': 'plus',
                 '-': 'minus',
                 }
        for c in tex:
            if c in string.letters:
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
    BEGIN_EXPRESSION
          <latex expression containing MATCH labels>
    END_EXPRESSION
    CHECK_FORMULA: <text representation of correct formula, using MATCH labels, to be used for checking>
    CHECK_FORMULA_BOXES: <formula using [#], where [#] is the MATCH label number; needed if MATCH labels appear in more than one input box>

    """
    def __init__(self, sfn, output_fp=None, input_tex=None, verbose=False):
        '''
        sfn = dndpsec filename (should be *.dndspec)
        '''
        self.input_filename = sfn
        self.verbose = verbose
        self.parse_file(sfn, input_tex=input_tex)
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
            print "Wrote dnd tex to %s" % ofn
        self.tex_filename = ofn

    def parse_file(self, sfn, input_tex=None):
        self.match_labels = None
        self.distractor_labels = []
        self.all_labels = []
        self.box_width = "8ex"
        self.box_height = "4ex"
        self.expression = ""
        self.check_formula = None
        self.check_formula_boxes = None
        self.comments = ""
        self.extra_header_tex = ""
        self.formula_tests = []		# list of dicts specifying tests
        self.label_objects_by_box_index = {}	# key=index, val=DNDlabel object
        self.label_objects_by_draggable_id = {}	# key = draggable label, val=DNDlabel object
        
        mode = None
        if not input_tex:
            lines = open(sfn)
        else:
            lines = input_tex.split('\n')

        def splitstr(s):
            return [x.strip() for x in s.split(',')]
            
        def space_pad(s):
            return ' ' + s + ' '

        def make_test_correct(s):
            test_formula = ' ' + s + ' '            
            return {'etype': 'correct', 'formula': test_formula}

        def make_test_incorrect(s):
            test_formula = ' ' + s + ' '            
            return {'etype': 'incorrect', 'formula': test_formula}

        keyword_table = {'BOX_WIDTH': {'field': 'box_width', 'func': None},
                         'BOX_HEIGHT': {'field': 'box_height', 'func': None},
                         'EXTRA_HEADER_TEX': {'field': 'extra_header_tex', 'func': None},
                         'MATCH_LABELS': {'field': 'match_labels', 'func': splitstr},
                         'DISTRACTOR_LABELS': {'field': 'distractor_labels', 'func': splitstr, 'add': True},
                         'ALL_LABELS': {'field': 'all_labels', 'func': splitstr, 'add': True},
                         'CHECK_FORMULA': {'field': 'check_formula', 'func': space_pad},
                         'CHECK_FORMULA_BOXES': {'field': 'check_formula_boxes', 'func': space_pad},
                         'TEST_CORRECT': {'field': 'formula_tests', 'func': make_test_correct, 'append': True},
                         'TEST_INCORRECT': {'field': 'formula_tests', 'func': make_test_incorrect, 'append': True},
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
            for kw, kwinfo in keyword_table.items():
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
                print msg
                raise Exception(msg)

        if self.verbose:
            print "[dndspec] from file %s read %d match labels, %d labels alltogether, and %d tests" % (sfn,
                                                                                                        len(self.match_labels),
                                                                                                        len(self.all_labels),
                                                                                                        len(self.formula_tests),
                                                                                                        )
            
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

        def make_label(label, cnt, ltype):
            return DNDlabel(label,
                            index_set=self.label_objects_by_box_index,
                            draggable_label_set=self.label_objects_by_draggable_id,
                            index=cnt,
                            verbose=self.verbose,
                            ltype=ltype)

        for label in self.match_labels:
            cnt += 1
            label_objs[label] = make_label(label, cnt, 'match')

        for label in self.all_labels:
            if not label in label_objs:
                cnt += 1
                label_objs[label] = make_label(label, cnt, "distractor")
                
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
                print "Error in dndspec - failed to assemble DND expression, labre=%s, dnd_expression=%s" % (labre, dnd_expression)
                raise
            if not matches:
                msg = "--> [dndspec] WARNING: no matching label '%s' found in expression!" % label
                print msg
                print "expression = %s" % dnd_expression
                print "label regular expression = %s" % labre
                print "search: %s" % (re.search(labre, dnd_expression, flags=re.M))
                raise Exception(msg)
            if self.verbose:
                print "[dndspec] found %d matches for label '%s' in expression" % (len(matches), label)
            for match in matches:
                # if a label appears multiple times in the expression, then
                # the the box numbers must change, to ensure all DDB box numbers
                # are unique
                def make_ddbox(m):
                    return lobj.make_ddbox(nwidth=1)
                dnd_expression = re.sub(labre, make_ddbox, dnd_expression, count=1, flags=re.M)
        self.dnd_expression = dnd_expression
        if self.verbose:
            print "[dndspec] dnd_expression=%s" % self.dnd_expression

    def formula_to_boxed(self, formula, labelset=None, exit_on_failure=True, missing_ok=False):
        '''
        Convert a text math formula to one with index boxed [#] for each identified expression.
        '''
        labelset = labelset or self.match_labels
        for label in labelset:
            lobj = self.label_objs[label]
            labre = "\s%s\s" % self.escape_regexp(lobj.math_exp)
            (formula, nmatch) = re.subn(labre, lobj.formula_box, formula)
            if not nmatch and (not missing_ok):
                msg = "--> [dndspec] WARNING: no matching math expression found for '%s' (%s) in formula" % (label, lobj.math_exp)
                print msg
                print "    formula = %s" % formula
                print "    label math expression = %s" % labre
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
            self.math_check_formula = re.sub("\s%s\s" % label, ' ' + lobj.math_exp + ' ', self.math_check_formula)

        # make check formula boxes if one not provided
        if not self.check_formula_boxes:
            self.check_formula_boxes = self.formula_to_boxed(self.math_check_formula, exit_on_failure=False)

        varlist = [ self.label_objs[label].math_variable for label in self.all_labels]
        varlist = [x for x in varlist if x is not None]	# remove None
        varlist = set(varlist)	# remove duplicates
        self.formula_variables = ','.join(list(varlist))
        self.formula_nsamples = 20
        nvar = len(varlist)
        self.formula_sample_ranges = ','.join('1'*nvar) + ":" + ','.join(['20']*nvar) 
        self.formula_samples = "%s@%s\\#%d" % (self.formula_variables, self.formula_sample_ranges, self.formula_nsamples)
        if self.verbose:
            print "[dndspec] Generated check_formula_boxes '%s'" % self.check_formula_boxes
            print "          Using %d variables: %s" % (nvar, self.formula_variables)
            print "          And taking %d samples" % (self.formula_nsamples)

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
                print "[dndspec] Failed to construct test for test_formula='%s'" % (test['formula'])
                raise

            # compare boxed_test_formula to check_formula_boxes to see which boxes the input is going into
            test_formula_box_id_list = self.extract_boxes_from_formula(boxed_test_formula)

            # translate test formula box id's into draggable label id's
            label_ids = [ self.label_objects_by_box_index[x].draggable_label for x in test_formula_box_id_list ]
            target_ids = check_formula_box_id_list
            test['target_ids'] = map(str, target_ids)
            test['draggable_ids'] = label_ids
            if not len(label_ids)==len(target_ids):
                msg = "[dndspec] Error generating test from formula '%s'" % test['formula']
                print msg
                print "          Found %d target ID's but %d draggable label ID's" % (len(target_ids), len(label_ids))
                print "          Boxed test formula = %s" % boxed_test_formula
                print "          Taget ID's: %s" % str(target_ids)
                print "          Draggable label ID's: %s" % str(label_ids)
                raise Exception(msg)
            test_tex.append('\\DDtest{%s}{%s}{%s}' % (test['etype'], ','.join(test['target_ids']), ','.join(test['draggable_ids'])))

        self.formula_test_tex = '\n'.join(test_tex)
        if self.verbose:
            print "[dndspec] Generated %d tests:" % len(test_tex)
            for test in test_tex:
                print "          %s" % test

    def generate_tex(self):
        '''
        Generate tex output from dndspec.  Use template tex file.
        '''
        mydir = os.path.dirname(__file__)
        texpath = os.path.abspath(mydir + '/tex')
        template = open(texpath + "/dndspec_template.tex").read()

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
                  }
        for key, val in params.items():
            template = template.replace('<' + key + '>', val)
            
        self.dnd_tex = template
                                 
#-----------------------------------------------------------------------------
# unit tests

def test_dndlabel1():
    ddl = DNDlabel("-\pi", index_set={}, draggable_label_set={}, ltype="match")
    assert ddl.math_exp=="-pi"
    assert ddl.draggable_label == "minuspi"
    
def test_dndlabel2():
    ddl = DNDlabel("-2", index_set={}, draggable_label_set={}, ltype="match")
    assert ddl.math_exp=="-2"
    assert ddl.draggable_label == "minustwo"
                                 
def test_dndlabel3():
    ddl = DNDlabel("- \pi", index_set={}, draggable_label_set={}, ltype="match")
    assert ddl.math_exp=="minuspi"
    assert ddl.draggable_label == "minuspi"
    
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
    from StringIO import StringIO
    ofp = StringIO()
    dst = DNDspec2tex("stdin", input_tex=tex, output_fp=ofp, verbose=True)
    contents = str(ofp.getvalue())
    print contents
    assert( r'\DDtest{correct}{1,2,3,4}{minuspi,dtwo,Bprime,v}' in contents)
    assert( r'\DDformula{  ([1]) * ( ([2]) * ([3]) ) / ( ([4]) )  }{ d,Bprime,v,zzz,-pi@1,1,1,1,1:20,20,20,20,20\#20 }{  -pi * ( Bprime * d^2 ) / ( v )  }{}' in contents)    
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
    from StringIO import StringIO
    ofp = StringIO()
    err = ''
    try:
        dst = DNDspec2tex("stdin", input_tex=tex, output_fp=ofp, verbose=True)
    except Exception as err:
        pass
    print str(err)
    assert "WARNING: no matching label 'mu' found" in str(err)
