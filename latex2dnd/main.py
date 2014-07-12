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
from path import path
from lxml import etree
from collections import OrderedDict

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
            print cmd
        os.system(cmd)

        # crop the file, verbosely, to get the bounding box
        cmd = 'pdfcrop --verbose tmp.pdf %s' % (pdfimfn)
        if verbose:
            print cmd
        bbstr = os.popen(cmd).read()

        hrbb_str = re.findall('HiResBoundingBox:([^\n]+)', bbstr)[0].split()

	# turn bounding box into units of inches
        def pt2in(x):
            return float(x) * 1.0/72

        hrbb = map(pt2in, hrbb_str)

        if verbose:
            print "BoundingBox (inches): %s" % hrbb

        self.fn = fn
        self.pdfimfn = pdfimfn
        self.imfn = imfn
        self.hrbb = hrbb

        # generate PNG from cropped PDF
        cmd = "pdftoppm -r %s -png %s > %s" % (dpi, pdfimfn, imfn)
        if verbose:
            print cmd
        os.system(cmd)
        
        # get png image size
        # file mytest1.png
        # mytest1.png: PNG image data, 2550 x 3301, 8-bit/color RGB, non-interlaced

        imdat = os.popen('file %s' % imfn).read().split()[4:7]
        if verbose:
            print imdat
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
            print cmd
        os.system(cmd)
        
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
            print cmd
        os.system(cmd)

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
            print cmd
        os.system(cmd)

        
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
        self.pos = map(toinches, self.numbers.split(', '))

        # save highres bounding box (units: inches)
        self.hrbb = hrbb

        if self.verbose:
            print str(self)
        self.offset(hrbb[0], hrbb[1])
        if self.verbose:
            print "  --> offset %s" % str(self)

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
        return map(in_to_px, [self.pos[0], ysize-self.pos[1], self.pos[2], ysize-self.pos[3]])


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
                 can_reuse=False, custom_cfn=None):
        '''
        texfn = *.tex filename
        '''
        if compile:
            # set the TEXINPUTS path
            mydir = os.path.dirname(__file__)
            texpath = os.path.abspath(mydir + '/tex')
            os.environ['TEXINPUTS'] = "::%s" % texpath
            if verbose:
                print "Adding %s to TEXINPUTS" % texpath
                print "Running latex twice"
                print "-"*77
            # run pdflatex TWICE
            os.system('pdflatex %s' % texfn)
            os.system('pdflatex %s' % texfn)
            if verbose:
                print "="*77

        outdir = path(outdir)

        if not os.path.exists(outdir):
            os.mkdir(outdir)
        if not os.path.isdir(outdir):
            print "Error: output directory '%s' is not a directory" % outdir
            return

        self.options = {}
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

        # by convention, page 1 has the main drag-and-drop image,
        # and page 2 has the labels, in individual boxes.

        self.generate_dnd_image()
        self.generate_label_images(outdir)
        self.generate_dnd_xml()

        if verbose:
            print "="*70
            print "Done.  Generated:"
            print "    %s -- edX drag-and-drop question XML" % self.xmlfn
            print "    %s -- dnd problem image" % self.dndimfn
            print "    %s -- dnd problem solution image" % self.solimfn
            print "    %d dnd draggable image labels:" % len(self.labels)
            for label, lfn in self.labels.items():
                print "        %s -- label '%s'" % (lfn, label)
            print 
            print "The XML expects images to be in %s" % self.imdir
            print "="*70

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

        for label, labnum in self.dnd_labels.items():
            draggable = etree.SubElement(dnd, 'draggable')
            draggable.set('id', label)
            draggable.set('icon', self.imdir + self.labels[labnum].basename())
            if self.options.get('can_reuse', False):
                draggable.set('can_reuse', 'true')
        
        anskey = []
        for tname, aname in self.box_answers.items():
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
                print "    %s" % etree.tostring(target)
            dnd.append(etree.Comment(' answer=%s ' % aname))
            # anskey is a list of {draggable_id : target_id}
            anskey.append({aname: tname})

            
        if self.options.get('custom_cfn', None) is not None:

            # if custom_cfn is defined (either on command line, or in \DDoptions,
            # then use the named check function to evaluate DND output
            
            cfn = self.options['custom_cfn']
            cr.set('cfn', cfn)
            if self.verbose:
                print "    Using custom check function '%s' to evaluate DND output" % cfn
                
        elif self.dnd_formula:
            
            # if self.dnd_formula is not {}, then use a formula for checking, 
            # with customresponse script code, instead of the default
            # dnd grader.

            cfn = 'check_%s' % self.fnpre.basename()
            cr.set('cfn', cfn)
            
            script = etree.SubElement(xml, 'script')
            script.set('type', "text/python")

            mydir = os.path.dirname(__file__)
            libpath = path(os.path.abspath(mydir + '/lib'))
            check_code = open(libpath / 'dnd_formulacheck.py').read()

            # map from draggable labels to label formula contents
            dmap = {}
            for lname, lsym in self.dnd_label_contents.items():
                lsym = lsym.strip()
                if lsym.startswith('$') and lsym.endswith('$'):
                    lsym = lsym[1:-1]
                dmap[lname] = lsym

            dndf = self.dnd_formula
            info = {'CHECK_FUNCTION': cfn,
                    'CHECK_DMAP': repr(dmap),
                    'CHECK_FORMULA': repr(dndf['formula']),
                    'CHECK_SAMPLES': repr(dndf['samples']),
                    'CHECK_EXPECT': repr(dndf['expect']),
                    'CHECK_ERROR_MSG': repr(dndf['err']),
                    'OPTION_ALLOW_EMPTY': repr(self.options.get('allow_empty', False)),
                    'OPTION_HIDE_FORMULA_INPUT': repr(self.options.get('hide_formula_input', False))
                    }

            for key, val in info.items():
                check_code = check_code.replace(key, val)
            script.text = '\n' + check_code
            if self.verbose:
                print script.text

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
                          'ans = json.loads(submission[0])\n'
                          "correct = ['correct']\n"
                          "for rule in caset:\n"
                          "    if rule not in ans:\n"
                          "        correct = ['incorrect']\n"
                          "        break\n"
                          "\n"
                          "# use this for debugging\n"
                          "# messages = ['ans=%s' % submission[0]]\n")
    
            answer.text = '\ncaset = %s\n' % repr(anskey) + cacode
    
        sol = etree.SubElement(xml, 'solution')
        img = etree.SubElement(sol, 'img')
        img.set('src', self.imdir + self.solimfn.basename())

        with open(xmlfn,'w') as fp:
            fp.write(etree.tostring(xml, pretty_print=True))

        self.xmlfn = xmlfn

    def generate_dnd_image(self):
        '''
        The image from latex has solutions in it.  We white-out the
        boxes to make the dnd image.
        '''
        self.dndpi = PageImage(self.pdffn, page=1, imfn=self.solimfn, dpi=self.dpi, verbose=self.imverbose)
        # old test
        #self.dndpi.NegateBox(self.BoxSet['box1'], outfn='test.png')
        self.dndpi.WhiteBox([ self.BoxSet['box'+n] for n in self.box_answers], outfn=self.dndimfn)

    def generate_label_images(self, outdir='.'):
        outdir = path(outdir)
        # page with all labels
        self.labelimfn = outdir / self.fnpre + "_labels.png"	
        labelpi = PageImage(self.pdffn, page=2, imfn=self.labelimfn, dpi=self.dpi, verbose=self.imverbose)

        self.labels = OrderedDict()
        
        # extract each label box
        # by convention, the label boxes are named boxLABEL###
        for label, box in self.BoxSet.iteritems():
            if not label.startswith('boxLABEL'):
                continue
            m = re.search('boxLABEL([0-9]+)', label)
            labelnum = m.group(1)
            outfn = outdir / self.fnpre + '_dnd_label%s.png' % labelnum
            labelpi.ExtractBox(box, outfn)
            self.labels[label[8:]] = outfn
        if self.verbose:
            print "  %s labels" % len(self.labels)
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

        dndfn = self.fnpre + '.dnd'

        if not os.path.exists(dndfn):
            print "Error: %s does not exist; did the latex compilation fail?" % dndfn
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
                    if self.options.get(key, None) is not None:
                        print "  %s already fixed by command-line option: using that to override \DDoptions %s" % (key, option)
                    else:
                        self.options[key] = val
                 # print "OPTIONS = ", self.options

        if self.verbose:
            print "  %s target boxes" % len(self.box_answers)

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


def CommandLine():
    parser = optparse.OptionParser(usage="usage: %prog [options] filename.tex",
                                   version="%prog 0.9")
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
                      help="Resolution of PNG files in DPI (default 300)",)
    parser.add_option("--cfn",
                      action="store",
                      dest="custom_cfn",
                      default=None,
                      help="Name of python script check function to use for drag-drop checking",)
    (opts, args) = parser.parse_args()

    if len(args)<1:
        parser.error('wrong number of arguments')
        sys.exit(0)
    fn = args[0]

    l2d = LatexToDragDrop(fn, 
                          compile=(not opts.skip_latex), 
                          verbose=opts.verbose, 
                          dpi=opts.resolution,
                          outdir=opts.output_dir,
                          imverbose=opts.very_verbose,
                          can_reuse=opts.can_reuse,
                          custom_cfn=opts.custom_cfn,
    )

if __name__=="__main__":
    CommandLine()
