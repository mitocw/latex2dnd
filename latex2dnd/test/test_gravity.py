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

class TestGravity(unittest.TestCase):

    def test_gravity(self):
        testdir = path(l2dndmod.__file__).parent / 'testtex'  
        fn = testdir / 'gravity.tex'
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

            files = ['gravity_dnd_label1.png', 'gravity_dnd.xml', 'gravity_dnd.xml', 'gravity_dnd_sol.png']
            for fn in files:
                self.assertTrue(os.path.exists(path(tmdir)/fn))

            xfn = path(tmdir) / 'gravity_dnd.xml'
            xml = open(xfn).read()
            self.assertIn('<img src="/static/images/gravity/gravity_dnd_sol.png"/>', xml)
            self.assertIn("samples = 'G,m_1,m_2,d@1,1,1,1:20,20,20,20#40'", xml)

if __name__ == '__main__':
    unittest.main()
