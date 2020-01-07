import os
import contextlib
import unittest
import tempfile
import shutil
try:
    from path import path
except:
    from path import Path as path
import latex2dnd as l2dndmod
from latex2dnd.main import LatexToDragDrop
from io import StringIO

@contextlib.contextmanager
def make_temp_directory():
    temp_dir = tempfile.mkdtemp('l2dndtmp')
    yield temp_dir
    shutil.rmtree(temp_dir)

class TestExamples(unittest.TestCase):

    def test_example1(self):
        testdir = path(l2dndmod.__file__).parent / 'testtex'  
        fn = testdir / 'quadratic.tex'
        print("="*70)
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            l2dnd = LatexToDragDrop(nfn, verbose=True, randomize_solution_filename=False)

            pre = nfn[:-4]
            auxfn = pre + ".aux"
            self.assertTrue(os.path.exists(auxfn))

            files = ['quadratic_dnd_label1.png', 'quadratic_dnd.xml', 'quadratic_dnd.xml', 'quadratic_dnd_sol.png']
            for fn in files:
                self.assertTrue(os.path.exists(path(tmdir)/fn))

            xfn = path(tmdir) / 'quadratic_dnd.xml'
            xml = open(xfn).read()
            self.assertIn('<img src="/static/images/quadratic/quadratic_dnd_sol.png"/>', xml)
            self.assertIn('<draggable id="term2" icon="/static/images/quadratic/quadratic_dnd_label3.png"/>', xml)

if __name__ == '__main__':
    unittest.main()
