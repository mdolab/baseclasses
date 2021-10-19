import unittest
from baseclasses.utils import redirectIO
import sys
import os

baseDir = os.path.dirname(os.path.abspath(__file__))


class TestRedirectIO(unittest.TestCase):
    def setUp(self):
        self.stdout_lines = ["redirect echo out", "redirect out"]

        self.stderr_lines = ["redirect echo err", "redirect err"]

    def test_redirectIO(self):
        stdout_file = os.path.join(baseDir, "test_redirectIO.out")
        stderr_file = os.path.join(baseDir, "test_redirectIO.err")

        # redirecting output
        redirectIO.redirectIO(open(stdout_file, "w"), open(stderr_file, "w"))

        # write some stuff
        os.system('echo "redirect echo out"')
        print("redirect out")

        os.system('echo "redirect echo err" 1>&2')
        print("redirect err", file=sys.stderr)

        # check that stuff matches
        out_stream = open(stdout_file, "r")
        out_result = list(out_stream)
        out_stream.close()
        err_stream = open(stdout_file, "r")
        err_result = list(err_stream)
        err_stream.close()

        self.assertEqual(len(out_result), len(self.stdout_lines))
        self.assertEqual(len(err_result), len(self.stderr_lines))

        for i in range(len(out_result)):
            self.assertEqual(out_result[i], self.stdout_lines[i])
            self.assertEqual(err_result[i], self.stderr_lines[i])
        os.remove(stdout_file)
        os.remove(stderr_file)

    def test_redirectIO_same(self):
        stdout_file = os.path.join(baseDir, "test_redirectIO_same.out")

        # redirecting output
        redirectIO.redirectIO(open(stdout_file, "w"))

        # write some stuff
        os.system('echo "redirect echo out"')
        print("redirect out")

        os.system('echo "redirect echo err" 1>&2')
        print("redirect err", file=sys.stderr)

        # check that stuff matches
        out_stream = open(stdout_file, "r")
        out_result = list(out_stream)
        out_stream.close()

        self.assertEqual(len(out_result), len(self.stdout_lines) + len(self.stderr_lines))

        for i in range(len(out_result)):
            self.assertEqual(out_result[i], self.stdout_lines[i])
            self.assertEqual(out_result[i + 2], self.stderr_lines[i])
        os.remove(stdout_file)

    def test_redirectingIO(self):
        stdout_file = os.path.join(baseDir, "test_redirectIO.out")
        stderr_file = os.path.join(baseDir, "test_redirectIO.err")

        # redirecting output
        with redirectIO.redirectingIO(open(stdout_file, "w"), open(stderr_file, "w")):

            # write some stuff
            os.system('echo "redirect echo out"')
            print("redirect out")

            os.system('echo "redirect echo err" 1>&2')
            print("redirect err", file=sys.stderr)

        os.system('echo "outside echo out"')
        print("outside out")
        os.system('echo "outside echo err" 1>&2')
        print("outside err", file=sys.stderr)

        # check that stuff matches
        out_stream = open(stdout_file, "r")
        out_result = list(out_stream)
        out_stream.close()
        err_stream = open(stdout_file, "r")
        err_result = list(err_stream)
        err_stream.close()

        self.assertEqual(len(out_result), len(self.stdout_lines))
        self.assertEqual(len(err_result), len(self.stderr_lines))

        for i in range(len(out_result)):
            self.assertEqual(out_result[i], self.stdout_lines[i])
            self.assertEqual(err_result[i], self.stderr_lines[i])

        os.remove(stdout_file)
        os.remove(stderr_file)

    def test_redirectingIO_same(self):
        stdout_file = os.path.join(baseDir, "test_redirectIO.out")

        # redirecting output
        with redirectIO.redirectingIO(open(stdout_file, "w")):

            # write some stuff
            os.system('echo "redirect echo out"')
            print("redirect out")

            os.system('echo "redirect echo err" 1>&2')
            print("redirect err", file=sys.stderr)

        print("outside out")
        os.system('echo "outside echo out"')
        print("outside err", file=sys.stderr)
        os.system('echo "outside echo err" 1>&2')

        # check that stuff matches
        out_stream = open(stdout_file, "r")
        out_result = list(out_stream)
        out_stream.close()

        self.assertEqual(len(out_result), len(self.stdout_lines) + len(self.stderr_lines))

        for i in range(len(out_result)):
            self.assertEqual(out_result[i], self.stdout_lines[i])
            self.assertEqual(out_result[i + 2], self.stderr_lines[i])

        os.remove(stdout_file)

if __name__ == "__main__":
    print("runnning tests")
    unittest.main()
