#!/usr/bin/python
#
# Python script to compile latex file into an edX drag-and-drop problem
#
# From myfile.tex produces:
#
#      - myfile_dnd.png: drag-and-drop image
#      - myfile_dnd_sol.png: image of solution, with correct labels in boxes
#      - myfile_dnd.xml: drag-and-drop XML, with embedded python
#      - myfile_dnd_label###.png: drag-and-drop labels (### = number)
#
# Copy the *.png files to /your_course/static/images/myfile/
# 
# If you're using latex2edx (https://github.com/mitocw/latex2edx), you can
# then instantiate the generated dnd problem using:
#
# \begin{edXproblem}{Latex to drag and drop test}{}
#
# \edXinclude{mytest_dnd.xml}
# 
# \end{edXproblem}

import os
import sys
import re
import json
import optparse
import random
import string
import glob
try:
    from path import path
except:
    from path import Path as path
from lxml import etree
from collections import OrderedDict
from .formula import FormulaTester
from .dndspec import DNDspec2tex
from .dnd2catsoop import DndToCatsoop

class PageImage(object):
    '''
    Grab page of PDF, convert to PNG, and get HighRes BoundingBox for image
    '''
    def __init__(self, fn, page=1, imfn=None, pdfimfn=None, dpi=300, verbose=False):
        '''
        fn = filename
        '''
        if fn.endswith('.pdf'):
            fnpre = fn[:-4]
        else:
            fnpre = fn
        if pdfimfn is None:
            pdfimfn = fnpre + "_image.pdf"
        if imfn is None:
            imfn = fnpre + "_image.png"
        self.verbose = verbose

        # get page from PDF
        cmd = "pdfseparate -l %s -f %s %s tmp.pdf" % (page, page, fn)
        if verbose:
            print(cmd)
        os.system(cmd)
        if not os.path.exists("tmp.pdf"):
            raise Exception("===> [latex2dnd] error running pdfseparate, command: %s" % cmd)

        # crop the file, verbosely, to get the bounding box
        cmd = 'pdfcrop --verbose tmp.pdf %s' % (pdfimfn)
        if verbose:
            print(cmd)
        try:
            with os.popen(cmd) as cfp:
                bbstr = cfp.read()
        except Exception as err:
            print("===> [latex2dnd] error running pdfcrop, command: %s" % cmd)
            print("Error: ", err)
            raise

        try:
            hrbb_str = re.findall('HiResBoundingBox:([^\n]+)', bbstr)[0].split()
        except Exception as err:
            print("===> [latex2dnd] error finding high resolution bounding boxes in output from command: %s" % cmd)
            print("Error: ", err)
            raise

	# turn bounding box into units of inches
        def pt2in(x):
            return float(x) * 1.0/72

        hrbb = list(map(pt2in, hrbb_str))

        if verbose:
            print("BoundingBox (inches): %s" % hrbb)

        self.fn = fn
        self.pdfimfn = pdfimfn
        self.imfn = imfn
        self.hrbb = hrbb

        # generate PNG from cropped PDF
        cmd = "pdftoppm -r %s -png %s > %s" % (dpi, pdfimfn, imfn)
        if verbose:
            print(cmd)
        os.system(cmd)
        
        # get png image size
        # file mytest1.png
        # mytest1.png: PNG image data, 2550 x 3301, 8-bit/color RGB, non-interlaced

        with os.popen('file %s' % imfn) as ifp:
            imdat = ifp.read().split()[4:7]
        if verbose:
            print(imdat)
        imx = int(imdat[0])
        imy = int(imdat[2][:-1])

        self.sizex = imx
        self.sizey = imy

    def NegateBox(self, box, outfn=None):
        '''
        Negate image area where box is positioned.
        '''
        # make sure box is set for context of this image
        box.offset_by_bb(self.hrbb) 
        geom = box.png_geom(self.sizex, self.sizey)
        
        if outfn is None:
            outfn = self.imfn

        cmd = 'convert {imfn} -region {geom} -negate {outfn}'.format(imfn=self.imfn, 
                                                                     geom=geom,
                                                                     outfn=outfn)
        if self.verbose:
            print(cmd)
        os.system(cmd)
        if not os.path.exists(outfn):
            raise Exception("===> [latex2dnd] error running convert, command: %s" % cmd)
        
    def WhiteBox(self, boxes, outfn=None):
        '''
        White-out image area where box is positioned.
        Process multiple boxes together.
        '''
        if outfn is None:
            outfn = self.imfn

        if not isinstance(boxes, list):
            boxes = [ boxes ]

        regions = []
        for box in boxes:
            # make sure box is set for context of this image
            box.offset_by_bb(self.hrbb) 
            geom = box.png_geom(self.sizex, self.sizey, delta=4.5)

            regions.append('-region {geom} -threshold -1 '.format(geom=geom))

        cmd = 'convert {imfn} {regions} {outfn}'.format(imfn=self.imfn, 
                                                        regions=' '.join(regions),
                                                        outfn=outfn)
        if self.verbose:
            print(cmd)
        os.system(cmd)
        if not os.path.exists(outfn):
            raise Exception("===> [latex2dnd] error running convert, command: %s" % cmd)

    def ExtractBox(self, box, outfn=None):
        '''
        Extract image in boxed area
        '''
        # make sure box is set for context of this image
        box.offset_by_bb(self.hrbb) 
        geom = box.png_geom(self.sizex, self.sizey, delta=4.5)
        
        if outfn is None:
            outfn = self.imfn[:-4] + '_extract.png'

        cmd = 'convert {imfn} -crop {geom} {outfn}'.format(imfn=self.imfn, 
                                                           geom=geom,
                                                           outfn=outfn)
        if self.verbose:
            print(cmd)
        os.system(cmd)
        if not os.path.exists(outfn):
            raise Exception("===> [latex2dnd] error running convert, command: %s" % cmd)

        
class Box(object):
    '''
    represent a drag-and-drop box, as specified by latex zpos sp coordinates.
    be able to contextualize box position within a cropped,
    pixellated image.
    '''
    def __init__(self, pos_line, hrbb=None, verbose=False):
        self.label, self.numbers = pos_line.split(': ')
        self.verbose = verbose
        
        if hrbb is not None:
            self.offset_by_bb(hrbb)

    def offset_by_bb(self, hrbb):
        '''
        offset the box position to match the high res bounding box, hrbb
        '''
        # points in *.pos file from latex measured from lower left corner of page
        # page is nominally 8.5 x 11
        def toinches(x):
            return float(x) * (1.0/72.27)/65536

        # llx, lly, urx, ury = map(toinches, numbers.split(', '))
        self.pos = list(map(toinches, self.numbers.split(', ')))

        # save highres bounding box (units: inches)
        self.hrbb = hrbb

        if self.verbose:
            print(str(self))
        self.offset(hrbb[0], hrbb[1])
        if self.verbose:
            print("  --> offset %s" % str(self))

    def __str__(self):
        return "Box %s: %s" % (self.label, self.pos)

    def offset(self, dx, dy):
        self.pos[0] -= dx
        self.pos[2] -= dx
        self.pos[1] -= dy
        self.pos[3] -= dy

    def png_pos(self, imx, imy):
        '''
        return list of [llx, lly, urx, ury] for pixel position of box
        in image.  uses upper left as (0,0)

        for the conversion factor, choose the larger of imx or imy,
        to get greater accuracy (less roundoff)
        '''
        if imx > imy:
            cf = (1.0 * imx) / (self.hrbb[2]-self.hrbb[0])
        else:
            cf = (1.0 * imy) / (self.hrbb[3]-self.hrbb[1])
        self.cf = cf
        ysize = self.hrbb[3]-self.hrbb[1]  # y-size of source image, in inches

        def in_to_px(x):
            return int(cf * x)
        return list(map(in_to_px, [self.pos[0], ysize-self.pos[1], self.pos[2], ysize-self.pos[3]]))


    def png_geom(self, imx, imy, delta=0):
        '''
        return geometry string for box, in units of pixels (for PNG file)
        it is assumed that the PNG file has a width which imx which is
        equal to that given by hrbb, i.e. hrbb[2]-hrbb[0].

        the geometry string uses a coordinate system with (0,0) in the upper left
        '''
        pp = self.png_pos(imx, imy)
        dx = int(pp[2] - pp[0] - 2*delta)
        dy = int(pp[1] - pp[3] - 2*delta)
        geom = '%dx%d+%d+%d' % (dx, dy, int(pp[0]+delta), int(pp[3]+4+delta))
        return geom


class LatexToDragDrop(object):
    '''
    Grab boxes from latex *.aux file, 
    extract image for drag-and-drop
    extract labels for drag-and-drop
    generate drag-and-drop XML.

    for myfile.tex, the output is:

      - myfile_dnd.png: drag-and-drop image
      - myfile_dnd_sol.png: image of solution, with correct labels in boxes
      - myfile_dnd.xml: drag-and-drop XML, with embedded python
      - myfile_dnd_label###.png: drag-and-drop labels (### = number)

    '''
    
    def __init__(self, texfn, compile=True, verbose=True, dpi=300, imverbose=False, outdir='.',
                 can_reuse=False, custom_cfn=None, randomize_solution_filename=True, do_cleanup=False,
                 command_line_options_override=True,
                 interactionmode=None):
        '''
        texfn = *.tex filename

        command_line_options_override = (bool) True if provided parameers should override whatever is specified in the tex or dndspec file
        '''
        self.command_line_options_override = command_line_options_override
        if compile:
            # set the TEXINPUTS path
            mydir = os.path.dirname(__file__)
            oldti = os.environ.get('TEXINPUTS', "")
            texpath = os.path.abspath(mydir + '/tex')
            newti = "::%s" % texpath
            if oldti:
                newti += ":" + oldti
            os.environ['TEXINPUTS'] = newti
                
            if verbose:
                print("Setting TEXINPUTS=%s" % os.environ['TEXINPUTS'])
                print("Running latex twice")
                print("-"*77)
            imstr = ""
            if interactionmode:
                imstr = "-interaction=%s" % interactionmode
            # run pdflatex TWICE
            for k in range(2):
                os.system('pdflatex %s %s' % (imstr, texfn))
            if verbose:
                print("="*77)

        outdir = path(outdir)

        if not os.path.exists(outdir):
            os.mkdir(outdir)
        if not os.path.isdir(outdir):
            print("Error: output directory '%s' is not a directory" % outdir)
            return

        self.outdir = outdir
        self.max_image_width = 780
        self.options = {}
        self.test_results = {}
        self.verbose = verbose
        self.imverbose = imverbose
        self.options['can_reuse'] = can_reuse
        self.options['custom_cfn'] = custom_cfn
        self.texfn = texfn
        self.fnpre = path(texfn[:-4])
        self.pdffn = self.fnpre + '.pdf'
        self.dndimfn = outdir / (self.fnpre + '_dnd.png')
        self.solimfn = outdir / (self.fnpre + '_dnd_sol.png')
        self.dpi = dpi
        self.load_boxes()
        self.load_dnd()

        if randomize_solution_filename:
            randkey = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            self.solimfn = outdir / (self.fnpre + '_dnd_sol_%s.png' % randkey)

        # by convention, page 1 has the main drag-and-drop image,
        # and page 2 has the labels, in individual boxes.

        if do_cleanup:
            self.cleanup_old_solution_image_files()

        self.generate_dnd_image()
        self.generate_label_images(outdir)
        self.generate_dnd_xml()

        if do_cleanup and os.path.exists("tmp.pdf"):
            os.unlink("tmp.pdf")
            if verbose:
                print("    Removed tmp.pdf")

        if verbose:
            print("="*70)
            print("Done.  Generated:")
            print("    %s -- edX drag-and-drop question XML" % self.xmlfn)
            print("    %s -- dnd problem image" % self.dndimfn)
            print("    %s -- dnd problem solution image" % self.solimfn)
            print("    %d dnd draggable image labels:" % len(self.labels))
            for label, lfn in list(self.labels.items()):
                print("        %s -- label '%s'" % (lfn, label))
            print() 
            print("The DND image has size %s x %s (used DPI=%s)" % (self.dndpi.sizex, self.dndpi.sizey, self.final_dpi))
            print("The XML expects images to be in %s" % self.imdir)
            print("="*70)

    def cleanup_old_solution_image_files(self):
        '''
        Delete old solution image files, if present
        '''
        old_solimfn_pat = path(self.outdir) / (self.fnpre + '_dnd_sol_??????.png')
        print("pat=%s" % old_solimfn_pat)
        old_sol_image_files = list(glob.glob(old_solimfn_pat))
        if old_sol_image_files:
            if self.verbose:
                print("[latex2dnd] Cleaning up by removing %d old files:" % (len(old_sol_image_files)))
            for fn in old_sol_image_files:
                os.unlink(fn)
                print("            Removed %s" % fn)

    def generate_dnd_xml(self):
        xmlfn = self.fnpre + '_dnd.xml'
        self.imdir = '/static/images/%s/' % self.fnpre.basename()

        xml = etree.Element('span')
        cr = etree.SubElement(xml, 'customresponse')
        dnd = etree.SubElement(cr, 'drag_and_drop_input')
        dnd.set('img', self.imdir + self.dndimfn.basename())
        dnd.set('target_outline', 'false')	# latex already provides outlines
        dnd.set('one_per_target', 'true')
        dnd.set('no_labels', 'true')
        dnd.set('label_bg_color', "rgb(222, 139, 238)")

        for label, labnum in list(self.dnd_labels.items()):
            draggable = etree.SubElement(dnd, 'draggable')
            draggable.set('id', label)
            draggable.set('icon', self.imdir + self.labels[labnum].basename())
            if self.options.get('can_reuse', False):
                draggable.set('can_reuse', 'true')
        
        anskey = []
        for tname, aname in list(self.box_answers.items()):
            target = etree.SubElement(dnd, 'target')
            target.set('id', tname)
            box = self.BoxSet['box' + tname]
            box.offset_by_bb(self.dndpi.hrbb)
            pos = box.png_pos(self.dndpi.sizex, self.dndpi.sizey)

            target.set('x', str(pos[0]))
            target.set('y', str(pos[3]))
            target.set('w', str(pos[2]-pos[0]))
            target.set('h', str(pos[1]-pos[3]))
            if self.verbose and False:
                print("    %s" % etree.tostring(target))
            dnd.append(etree.Comment(' answer=%s ' % aname))
            # anskey is a list of {draggable_id : target_id}
            anskey.append({aname: tname})

            
        if self.options.get('custom_cfn', None) is not None:

            # if custom_cfn is defined (either on command line, or in \DDoptions,
            # then use the named check function to evaluate DND output
            
            cfn = self.options['custom_cfn']
            cr.set('cfn', cfn)
            if self.verbose:
                print("    Using custom check function '%s' to evaluate DND output" % cfn)
                
        elif self.dnd_formula and self.dnd_formula.get('formula'):
            
            # if self.dnd_formula is not {}, then use a formula for checking, 
            # with customresponse script code, instead of the default
            # dnd grader.

            cfn = 'check_%s' % self.fnpre.basename()
            cfn = cfn.replace('-', '_')		# cfn must be a legal python procedure name
            cr.set('cfn', cfn)
            
            script = etree.SubElement(xml, 'script')
            script.set('type', "text/python")

            mydir = os.path.dirname(__file__)
            libpath = path(os.path.abspath(mydir + '/lib'))
            with open(libpath / 'dnd_formulacheck.py') as cfp:
                check_code = cfp.read()

            # map from draggable labels to label formula contents
            dmap = {}
            for lname, lsym in list(self.dnd_label_contents.items()):
                lsym = lsym.strip()
                if lsym.startswith('$') and lsym.endswith('$'):
                    lsym = lsym[1:-1]
                dmap[lname] = lsym

            dndf = self.dnd_formula

            # do some error checking here - validate samples string
            if dndf.get('formula'):
                m = re.search('([^@]+)@([^:]+):([^\#]+)#(\d+)', repr(dndf['samples']))
                if not m:
                    print("WARNING!!! Incorrect \DDforumla samples expression?  you have:")
                    print("  formula = %s" % dndf['formula'])
                    print("  samples = %s" % dndf['samples'])
                    print("  expect  = %s" % dndf['expect'])

            info = {'CHECK_FUNCTION': cfn,
                    'CHECK_DMAP': repr(dmap),
                    'CHECK_FORMULA': repr(dndf['formula']),
                    'CHECK_SAMPLES': repr(dndf['samples']),
                    'CHECK_EXPECT': repr(dndf['expect']),
                    'CHECK_ERROR_MSG': repr(dndf['err']),
                    'OPTION_ALLOW_EMPTY': repr(self.options.get('allow_empty', False)),
                    'OPTION_HIDE_FORMULA_INPUT': repr(self.options.get('hide_formula_input', False))
                    }

            for key, val in list(info.items()):
                check_code = check_code.replace(key, val)
            script.text = '\n' + check_code
            if self.verbose:
                print(script.text)

            fut = FormulaTester(check_code, self.box_answers, self.unit_tests)
            self.test_results = fut.run_tests()
            tfn = self.fnpre + '_dnd_tests.json'
            with open(tfn,'w') as fp:
                fp.write(json.dumps(self.test_results, indent=4))
            if self.verbose:
                print("Wrote unit test results to %s" % tfn)

        else:

            # use default dnd grader
            answer = etree.SubElement(cr, 'answer')
    
            if not self.options.get('can_reuse', False):
                cacode = ('ca = [ {"draggables": ca.keys(),"targets": ca.values(),"rule":"exact"} for ca in caset ]\n'
                          'if draganddrop.grade(submission[0], ca):\n'
                          '    correct = ["correct"]\n'
                          'else:\n'
                          '    correct = ["incorrect"]\n')
            else:
                cacode = ('# custom checking for reusable labels - assumes all targets get some label\n'
                          'import json\n'
                          "correct = ['correct']\n"
                          'try:\n'
                          '    ans = json.loads(submission[0])\n'
                          'except Exception as err:\n'
                          "    correct = ['incorrect']\n"
                          '    ans = []\n'
                          "for rule in caset:\n"
                          "    if rule not in ans:\n"
                          "        correct = ['incorrect']\n"
                          "        break\n"
                          "\n"
                          "# use this for debugging\n"
                          "# messages = ['ans=%s' % submission[0]]\n")
    
            errmsg = self.dnd_formula.get('err')
            if errmsg:
                cacode += ("if correct==['incorrect']:\n"
                           "    messages = [%s]\n" % repr(errmsg))

            answer.text = '\ncaset = %s\n' % repr(anskey) + cacode
    
        sol = etree.SubElement(xml, 'solution')
        img = etree.SubElement(sol, 'img')
        img.set('src', self.imdir + self.solimfn.basename())

        with open(xmlfn,'w') as fp:
            fp.write(etree.tostring(xml, pretty_print=True).decode())

        self.xmlfn = xmlfn

    def generate_dnd_image(self):
        '''
        The image from latex has solutions in it.  We white-out the
        boxes to make the dnd image.
        '''
        if type(self.dpi) in [str, str] and ('max' in self.dpi):
            self.final_dpi = 300
        else:
            self.final_dpi = self.dpi
        
        if type(self.dpi) in [str, str]:
            m = re.match("max([0-9]+)", self.dpi)	# if dpi=max200 then let 200 be the starting dpi value, but autoscale smaller to fit
            if m:
                self.final_dpi = m.group(1)
                self.dpi = "max"
            
            m = re.match("max:([0-9]+)", self.dpi)		# if dpi=max:780 then let 780 be self.max_image_width, and autoscale to fit
            if m:
                self.dpi = "max"
                self.max_image_width = int(m.group(1))
                print("[latex2dnd] Using %d as maximum image width" % self.max_image_width)

        if self.dpi=="max":
            # automatically set DPI by limiting image width to max_image_width
            self.dndpi = PageImage(self.pdffn, page=1, imfn=self.solimfn, dpi=self.final_dpi, verbose=self.imverbose)            
            if self.dndpi.sizex > self.max_image_width:
                print("[latex2dnd] Page width %d exceeds max=%s at dpi=%s" % (self.dndpi.sizex, self.max_image_width, self.final_dpi))
                newdpi = int(self.final_dpi * 1.0 * self.max_image_width / self.dndpi.sizex * 0.95)
                print("            Reducing dpi to %s" % newdpi)
                self.final_dpi = newdpi
                self.dndpi = PageImage(self.pdffn, page=1, imfn=self.solimfn, dpi=self.final_dpi, verbose=self.imverbose)            
                if self.dndpi.sizex > self.max_image_width:
                    print("[latex2dnd] Page width %d STILL exceeds max=%s at dpi=%s" % (self.dndpi.sizex, self.max_image_width, self.final_dpi))
            
        self.dndpi = PageImage(self.pdffn, page=1, imfn=self.solimfn, dpi=self.final_dpi, verbose=self.imverbose)
        # old test
        #self.dndpi.NegateBox(self.BoxSet['box1'], outfn='test.png')
        self.dndpi.WhiteBox([ self.BoxSet['box'+n] for n in self.box_answers], outfn=self.dndimfn)

    def generate_label_images(self, outdir='.'):
        outdir = path(outdir)
        # page with all labels
        self.labelimfn = outdir / self.fnpre + "_labels.png"	
        labelpi = PageImage(self.pdffn, page=2, imfn=self.labelimfn, dpi=self.final_dpi, verbose=self.imverbose)

        self.labels = OrderedDict()
        
        # extract each label box
        # by convention, the label boxes are named boxLABEL###
        for label, box in self.BoxSet.items():
            if not label.startswith('boxLABEL'):
                continue
            m = re.search('boxLABEL([0-9]+)', label)
            labelnum = m.group(1)
            outfn = outdir / self.fnpre + '_dnd_label%s.png' % labelnum
            labelpi.ExtractBox(box, outfn)
            self.labels[label[8:]] = outfn
        if self.verbose:
            print("  %s labels" % len(self.labels))
            # print json.dumps(self.labels, indent=4)

    def load_dnd(self):
        '''
        load the *.dnd file generated by pdflatex
        This file lists the target boxes, with specification of correct labels.
        It also lists all the labels, and their author-given names.

        We'll use those names in the XML file.

        This file may provide configuration options specified by the author.
        '''
        self.dnd_labels = OrderedDict()
        self.dnd_label_contents = OrderedDict()
        self.box_answers = OrderedDict()
        self.dnd_formula = {}
        self.unit_tests = []

        dndfn = self.fnpre + '.dnd'

        if not os.path.exists(dndfn):
            print("Error: %s does not exist; did the latex compilation fail?" % dndfn)
            raise "latex2dnd_error"

        for k in open(dndfn):
            m = re.search('LABEL: ([0-9]+) = (.*) /// (.*)', k)
            if m:
                # 1 = label number
                # 2 = label name
                # 3 = label contents (math symbols or word)
                self.dnd_labels[m.group(2)] = m.group(1)
                self.dnd_label_contents[m.group(2)] = m.group(3)
            m = re.search('BOX: ([^ ]+) = (.*)', k)
            if m:
                # 1 = box name
                # 2 = answer label name
                self.box_answers[m.group(1)] = m.group(2)
            m = re.search('TEST: ([^/]+) /// ([^/]+) /// ([^/]+)', k)		# unit test specifications
            if m:
                # 1 = correct or incorrect
                # 2 = list of comma separated target ID's (answer box numbers)
                # 3 = list of comma separated draggable ID's (answer label IDs)
                etype = m.group(1).lower()
                assert etype=="correct" or etype=="incorrect"
                target_ids = m.group(2).strip().split(',')
                draggable_ids = m.group(3).strip().split(',')
                if not len(target_ids)==len(draggable_ids):
                    print("--> Error in DDtest: mismatch in length of target IDs and draggable IDs in '%s'" % k)
                    sys.exit(0)
                target_assignments = dict(list(zip(target_ids, draggable_ids)))
                self.unit_tests.append({'etype': etype, 'target_assignments': target_assignments})
                if self.verbose:
                    print("Added unit test [%s] = %s" % (len(self.unit_tests), self.unit_tests[-1]))

            m = re.search('FORMULA: (.*)', k)
            if m:
                #1 = formula to use in checking
                # fix formula, replace square with curly brackets,
                # add underscore in front of numerical ids
                formula = m.group(1).replace('[','{').replace(']','}').strip()
                formula = re.sub('\{([0-9]+)\}','{_\\1}', formula)
                self.dnd_formula['formula'] = formula
            m = re.search('FORMULA_SAMPLES: (.*)', k)
            if m:
                self.dnd_formula['samples'] = m.group(1).strip().replace('\\#','#')
            m = re.search('FORMULA_EXPECT: (.*)', k)
            if m:
                self.dnd_formula['expect'] = m.group(1)
            m = re.search('FORMULA_ERR: (.*)', k)
            if m:
                self.dnd_formula['err'] = m.group(1)
            m = re.search('OPTIONS: (.*)', k)
            if m:
                # define options based on key=value pairs specified in the tex file
                # for example, custom_cfn=my_check_function
                options = m.group(1).split()
                for option in options:
                    if '=' in option:
                        (key, val) = option.split('=',1)
                        key = key.lower().strip()
                    else:
                        key = option.lower().strip()
                        val = True
                    if self.options.get(key, None) is not None and self.command_line_options_override:
                        print("  %s=%s already fixed by command-line option: using that to override \DDoptions %s" % (key, val, option))
                    else:
                        self.options[key] = val
                 # print "OPTIONS = ", self.options

        if self.verbose:
            print("  %s target boxes" % len(self.box_answers))

    def load_boxes(self):
        '''
        read in position of boxes
        create list of boxes from the *.aux file generated by latex
        
        the aux file has lines like this:
        
        \zref@newlabel{boxLABEL1-ll}{\posx{13022933}\posy{41185446}\abspage{2}}
        \zref@newlabel{boxLABEL1-ur}{\posx{15542652}\posy{42290270}\abspage{2}}
        '''

        BoxSet = OrderedDict()
        
        if 0:
            # old way uses the *.pos file, but that doesn't contain all the points
            posfn = self.fnpre + '.pos'
        
            for k in open(posfn):
                b = Box(k, hrbb)
                BoxSet[b.label] = b
        else:
            # use the *.aux file instead; it has all the zpos points
            auxfn = self.fnpre + ".aux"
            for k in open(auxfn):
                if not k.startswith('\\zref@newlabel'):
                    continue
                m = re.search('label\{([^\}]+)\}\{\\\\posx\{([^\}]+)\}\\\\posy\{([^\}]+)\}', k)
                if m is None:
                    # print "no match for %s" % k
                    continue
                label = m.group(1)
                if label.endswith('-ll'):
                    x = [m.group(2)]
                    y = [m.group(3)]
                else:
                    x.append(m.group(2))
                    y.append(m.group(3))
                    label = label[:-3]
                    b = Box('%s: %s, %s, %s, %s' % (label, x[0], y[0], x[1], y[1]))
                    BoxSet[b.label] = b
        
        self.BoxSet = BoxSet


def CommandLine(opts=None, args=None, arglist=None, return_object=False):
    '''
    Main command line.  Accepts args, to allow for simple unit testing.
    '''
    parser = optparse.OptionParser(usage="usage: %prog [options] [filename.tex | filename.dndspec]",
                                   version="%prog 1.1.1")
    parser.add_option('-v', '--verbose', 
                      dest='verbose', 
                      default=False, action='store_true',
                      help='verbose messages')
    parser.add_option('-V', '--very-verbose', 
                      dest='very_verbose', 
                      default=False, action='store_true',
                      help='very verbose messages')
    parser.add_option('-C', '--can-reuse-labels', 
                      dest='can_reuse', 
                      default=False, action='store_true',
                      help='allow draggable labels to be reusable')
    parser.add_option('-s', '--skip-latex-compilation', 
                      dest='skip_latex', 
                      default=False, action='store_true',
                      help='skip latex compilation')
    parser.add_option("-d", "--output-directory",
                      action="store",
                      dest="output_dir",
                      default=".",
                      help="Directory name for output PNG files",)
    parser.add_option("-c", "--config-file",
                      action="store",
                      dest="config_file",
                      default="latex2dnd_config.json",
                      help="configuration file to load",)
    parser.add_option("-u", "--url-for-images",
                      action="store",
                      dest="image_url",
                      default="/static/images",
                      help="base URL for images",)
    parser.add_option("-r", "--resolution",
                      action="store",
                      dest="resolution",
                      default="300",
                      help="Resolution of PNG files in DPI (default 300), can set to 'max' to auto-scale",)
    parser.add_option("--cfn",
                      action="store",
                      dest="custom_cfn",
                      default=None,
                      help="Name of python script check function to use for drag-drop checking",)
    parser.add_option("--output-tex",
                      action="store_true",
                      dest="output_tex",
                      default=False,
                      help="Final output should be a tex file (works when input is a *.dndspec file)",)
    parser.add_option("--output-catsoop",
                      action="store_true",
                      dest="output_catsoop",
                      default=False,
                      help="Final output should be a markdown file for catsoop",)
    parser.add_option("--cleanup",
                      action="store_true",
                      dest="do_cleanup",
                      default=False,
                      help="Remove old solution image files, and tmp.pdf",)
    parser.add_option("--nonrandom",
                      action="store_true",
                      dest="nonrandom",
                      default=False,
                      help="Do not use a random string in the solution filename",)
    parser.add_option("--tex-options-override",
                      action="store_true",
                      default=False,
                      help="allow options in tex or dndspec file to override command line options",)

    if not opts:
        (opts, args) = parser.parse_args(arglist)

    if len(args)<1:
        parser.error('wrong number of arguments')
        sys.exit(0)
    fn = args[0]

    if fn.endswith(".dndspec"):
        try:
            s2t = DNDspec2tex(fn, verbose=opts.verbose)
        except Exception as err:
            print("[latex2dnd] Failed to run dndspec2tex on input file %s, err=%s" % (fn, err))
            raise
        if opts.output_tex:
            sys.exit(0)
        fn = s2t.tex_filename

    l2d = LatexToDragDrop(fn, 
                          compile=(not opts.skip_latex), 
                          verbose=opts.verbose, 
                          dpi=opts.resolution,
                          outdir=opts.output_dir,
                          imverbose=opts.very_verbose,
                          can_reuse=opts.can_reuse,
                          custom_cfn=opts.custom_cfn,
                          do_cleanup=opts.do_cleanup,
                          command_line_options_override=(not opts.tex_options_override),
                          randomize_solution_filename=(not opts.nonrandom),
    )
    if opts.output_catsoop:
        d2c = DndToCatsoop(l2d)
        l2d.d2c = d2c

    if return_object:
        return l2d

if __name__=="__main__":
    CommandLine()
