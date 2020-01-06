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

class TestGravityWithOptions(unittest.TestCase):

    def test_gravity_with_options(self):
        testdir = path(l2dndmod.__file__).parent / 'testtex'  
        fn = testdir / 'gravity2.tex'
        print("="*70)
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            l2dnd = LatexToDragDrop(nfn, verbose=True, randomize_solution_filename=False)

            self.assertTrue(len(l2dnd.test_results)==3)

            pre = nfn[:-4]
            auxfn = pre + ".aux"
            self.assertTrue(os.path.exists(auxfn))

            files = ['gravity2_dnd_label1.png', 'gravity2_dnd.xml', 'gravity2_dnd.xml', 'gravity2_dnd_sol.png']
            for fn in files:
                self.assertTrue(os.path.exists(path(tmdir)/fn))

            xfn = path(tmdir) / 'gravity2_dnd.xml'
            xml = open(xfn).read()
            self.assertIn("'hide_formula_input': True", xml)

            tfn = path(tmdir) / 'gravity2_dnd_tests.json'
            self.assertTrue(os.path.exists(tfn))

if __name__ == '__main__':
    unittest.main()
