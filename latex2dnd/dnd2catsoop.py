import os
import re
from lxml import etree

class DndToCatsoop:
    '''
    Convert DND xml file (+ associated) to format used in catsoop LMS
    '''
    def __init__(self, l2d, check_fn=None):
        '''
        l2d = LatexToDragDrop instance
        '''
        ofn = l2d.fnpre + ".md"
        xmlfn = l2d.xmlfn
        clean_fn = l2d.fnpre.replace(' ', '_')
        clean_fn = clean_fn.replace('.', '_')
        xmlmd = self.make_drag_and_drop(xmlfn, check_fn)
        md = "<question drag_and_drop>\n"
        md += xmlmd
        md += "\n"
        md += 'csq_name="""%s"""\n' % clean_fn
        md += "</question>\n"
        with open(ofn, 'w') as fp:
            fp.write(md)
        print("Wrote %s lines of markdown to %s for catsoop" % (len(md.split('\n')), ofn))

    def make_drag_and_drop(self, xmlfn, check_fn=None):
        '''
        Make catsoop question content for drag-and-drop problem, based on XML output of latex2dnd
        xmlfn = dnd XML filename
        checn_fn = check function name (if provided)
        '''
        text = [""]
        print("Procesing drag-and-drop problem from %s" % xmlfn)
        xml = etree.parse(xmlfn).getroot()
        dnd_xml = etree.tostring(xml.find(".//drag_and_drop_input")).decode("utf8")
        answer = xml.find(".//answer")

        if check_fn is not None:
            cfn = check_fn
            print("[latex2cs.make_drag_and_drop] cfn=%s" % cfn)
            text.append('csq_check_function = %s' % cfn)

        elif answer is None:
            script = xml.find(".//script")
            cfn = script.text
            cfn += "\n"
            cfn += "ret = dnd_check_function(None, submission[0])\n"
            cfn += "correct = ['incorrect']\n"
            cfn += "if ret.get('ok'): correct = ['correct']\n"
            cfn += "if 'msg' in ret:\n"
            cfn += "    messages = ret.get('msg')\n"

            # overload old formula equality testing with new sympy formula check
            if 'def is_formula_equal' in cfn:
                txt = "def is_formula_equal(expected, given, samples):\n"
                txt += "    ret = sympy_check.sympy_formula_check(expected, given)\n"
                txt += "    return ret['ok']\n\n"
                txt += "def old_is_formula_equal"
                cfn = cfn.replace("def is_formula_equal", txt)

            text.append('csq_check_function = r"""%s"""' % cfn)

        else:
            cfn = answer.text
            text.append('csq_check_function = r"""%s"""' % cfn)

        sol = xml.find(".//solution")
        sol.tag = "span"
        sol = etree.tostring(sol).decode("utf8")
        sol = sol.replace('"/static/', '"CURRENT/')
        
        text.append('csq_soln = r"""%s"""' % sol)
        text.append('csq_dnd_xml = r"""%s"""' % dnd_xml)
        text.append("")			# ensure empty line at end
        return '\n'.join(text)
        
