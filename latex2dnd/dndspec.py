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
    def __init__(self, tex, index_set=None, index=None, math_exp=None, box_label=None, ltype=None, verbose=False):
        '''
        tex = label tex
        index_set = dict of current index values already used, with keys=index, val=DNDlabel objects
        index = suggested index number for this label
        math_exp = should be text formula parsable
        box_label = should be alpha only
        ltype = match or distractor
        '''
        self.tex = tex
        self.index = index
        self.index_set = index_set
        self.ltype = ltype
        self.verbose = verbose

        if self.index in index_set:
            raise Exception("[dndspec] Error!  non-unique index number %d for label '%s', index_set=%s" % (index, tex, index_set))
        index_set[self.index] = self

        if not math_exp:
            math_exp = self.make_math_exp(tex)
        self.math_exp = math_exp

        if not box_label:
            box_label = self.make_box_label(tex)
        self.box_label = box_label

        self.ddlabel = "\\DDlabel[%s]{%s}{$%s$}" % (self.math_exp, self.box_label, self.tex)
        self.formula_box = " ([%s]) " % self.index
        self.ddboxes = {}	# key=index, val=ddbox string; first one uses self.index

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
        ddbox = " \\DD%s{%d}{%s} " % (bwidth, index, self.box_label)
        self.ddboxes[index] = ddbox
        return ddbox

    def make_math_exp(self, tex):
        if all([ x in string.letters or x in string.digits for x in tex]):
            return tex
        expr = ""
        for c in tex:
            if c in string.letters or c in string.digits:
                expr += c
            else:
                expr += ""
        if expr.startswith("_"):
            expr = "x" + expr
        while expr.endswith("_"):
            expr = expr[:-1]
        return expr

    def make_box_label(self, tex):
        if all([ x in string.letters for x in tex]):
            return tex
        expr = ""
        digit_names = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
        for c in tex:
            if c in string.letters:
                expr += c
            elif c in string.digits:
                expr += digit_names[int(c)]
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
    def __init__(self, sfn, output_tex=False, verbose=False):
        '''
        sfn = dndpsec filename (should be *.dndspec)
        '''
        self.input_filename = sfn
        self.verbose = verbose
        self.parse_file(sfn)
        self.assemble_labels()
        self.assemble_dnd_expression()
        self.assemble_dnd_formula()
        self.generate_tex()

        # output latex
        ofn = sfn.replace('.dndspec', '.tex')
        open(ofn, 'w').write(self.dnd_tex)
        if self.verbose:
            print "Wrote dnd tex to %s" % ofn
        self.tex_filename = ofn

    def parse_file(self, sfn):
        self.match_labels = None
        self.distractor_labels = []
        self.all_labels = []
        self.expression = ""
        self.check_formula = None
        self.check_formula_boxes = None
        self.comments = ""
        
        mode = None
        for k in open(sfn):
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
            m = re.match('^MATCH_LABELS:(.*)', k)
            if m:
                self.match_labels = [x.strip() for x in m.group(1).split(',')]
                continue
            m = re.match('^DISTRACTOR_LABELS:(.*)',k)
            if m:
                self.distractor_labels = [x.strip() for x in m.group(1).split(',')]
                continue
            m = re.match('^ALL_LABELS:(.*)',k)
            if m:
                self.all_labels += [x.strip() for x in m.group(1).split(',')]
                continue
            m = re.match('^CHECK_FORMULA:(.*)',k)
            if m:
                self.check_formula = ' ' + m.group(1).strip() + ' '
                continue
            m = re.match('^CHECK_FORMULA_BOXES:(.*)',k)
            if m:
                self.check_formula_boxes = m.group(1).strip()
                continue
            
    def assemble_labels(self):
        '''
        Assemble labels tex.  Create self.all_labels list if needed.
         Also generate index for labels; number the match labels first 
        since those are the boxes in the DND expression.
        '''
        self.target_box_numbers = {}

        if not self.match_labels:
            raise Exception("[dndspec] Error!  No match labels specified")
        if not self.all_labels:
            self.all_labels = self.match_labels + self.distractor_labels
         # generate box index for labels ; distractor labels get dummy indices
        cnt = 0
        label_objs = OrderedDict()		# main dict of labels, with key=label tex, val=DNDlabel (with label_objs)
        for label in self.match_labels:
            cnt += 1
            label_objs[label] = DNDlabel(label, index_set=self.target_box_numbers, index=cnt, verbose=self.verbose, ltype="match")
        for label in self.all_labels:
            if not label in label_objs:
                cnt += 1
                label_objs[label] = DNDlabel(label, index_set=self.target_box_numbers, index=cnt, verbose=self.verbose, ltype="distractor")
                
        # generate \DDlabel[math_exp]{box_label}{label_tex} for each label
        # label_tex is the tex for the label, specified in LABELS
        ltex = [ label_objs[label].ddlabel for label in self.all_labels ]

        self.label_objs = label_objs
        self.label_tex = '\n'.join(ltex)
        
    def assemble_dnd_expression(self):
        '''
        asssemble dnd expression from provided input.
        replace found match labels with \DDB{boxnum}{box_label}
        '''
        dnd_expression = self.expression
        self.commented_expression = '%' + self.expression.replace('\n', '\n%') + '\n%'
        for label in self.match_labels:
            lobj = self.label_objs[label]
            labre = "\s%s\s" % label.replace('\\', '\\\\').replace('{', '\{').replace('^', '\^')
            matches = re.findall(labre, dnd_expression, flags=re.M)
            if not matches:
                print "--> [dndspec] WARNING: no matching label '%s' found in expression!" % label
                print "expression = %s" % dnd_expression
                print "label regular expression = %s" % labre
                print "search: %s" % (re.search(labre, dnd_expression, flags=re.M))
                sys.exit(0)
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
            cfb = self.math_check_formula
            for label in self.match_labels:
                lobj = self.label_objs[label]
                cfb = re.sub("\s%s\s" % lobj.math_exp, lobj.formula_box, cfb)
            self.check_formula_boxes = cfb

        self.formula_variables = ','.join([ self.label_objs[label].math_exp for label in self.match_labels])
        self.formula_nsamples = 20
        nvar = len(self.match_labels)
        self.formula_sample_ranges = ','.join('1'*nvar) + ":" + ','.join(['20']*nvar) 
        self.formula_samples = "%s@%s\\#%d" % (self.formula_variables, self.formula_sample_ranges, self.formula_nsamples)

        self.dd_formula = "\\DDformula{ %s }{ %s }{ %s }{}" % (self.check_formula_boxes,
                                                               self.formula_samples,
                                                               self.math_check_formula)

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
                  }
        for key, val in params.items():
            template = template.replace('<' + key + '>', val)
            
        self.dnd_tex = template
                                 
