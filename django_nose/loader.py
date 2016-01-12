from nose.util import tolist
from nose.loader import defaultTestLoader


def loadTestsFromDirMonkeyPatch(test_loader, path):
    """
    Monkey patch for TestLoader.loadTestsFromDir. The original
    function is a generator but we want tests to be loaded upfront
    in order to fix https://github.com/jbalogh/django-nose/issues/15
    and a generator is not compatible with that.

    """

    return list(test_loader._originalLoadTestsFromDir(path))


if not hasattr(defaultTestLoader, '_originalLoadTestsFromDir'):
    defaultTestLoader._originalLoadTestsFromDir = (
        defaultTestLoader.loadTestsFromDir)
    defaultTestLoader.loadTestsFromDir = loadTestsFromDirMonkeyPatch
