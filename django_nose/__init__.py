VERSION = (0, 0, 2)
__version__ = '.'.join(map(str, VERSION))

from runner import run_tests, run_gis_tests
