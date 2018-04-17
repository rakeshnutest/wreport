#!/usr/bin/env python
import logging
import os
import sys
import unittest

# Get the absolute paths to a few key places in the source tree.
tests_directory = os.path.dirname(os.path.realpath(__file__))
py_directory = os.path.realpath(os.path.join(tests_directory, ".."))

# Append the top directory to Python paths so that imports work in the tests.
sys.path.append(py_directory)

# Set up logging
logging.basicConfig(format='[%(filename)20s:%(lineno)3s - %(funcName)20s() ] %('
                               'asctime)s %(levelname)s: %(message)s',
                                                   level=logging.DEBUG)

# Discover and run the tests.
loader = unittest.TestLoader()
tests = loader.discover(tests_directory)
testRunner = unittest.runner.TextTestRunner(verbosity=2)
exit_code = not testRunner.run(tests).wasSuccessful()
sys.exit(exit_code)

