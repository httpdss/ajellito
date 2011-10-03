import time
import string
import os
from dulwich.repo import Repo

from django.conf import settings

try:
    settings.CACHE_BACKEND
    CACHE_ENABLED = True
except AttributeError:
    CACHE_ENABLED = False

try:
    UNRESTRICTED_SIZE = settings.UNRESTRICTED_SIZE
except AttributeError:
    UNRESTRICTED_SIZE = False

try:
    PRINTABLE_CARD_STOCK = settings.PRINTABLE_CARD_STOCK
except AttributeError:
    PRINTABLE_CARD_STOCK = None

ALPHABET = ''.join(c for c in string.ascii_uppercase + string.ascii_lowercase + string.digits + string.punctuation if c != '.')
BASE = len(ALPHABET)

def num_encode(n):
    s = []
    while True:
        n, r = divmod(n, BASE)
        s.append(ALPHABET[r])
        if n == 0: break
    return ''.join(reversed(s))

CACHE_PREFIX = num_encode(os.getpid()) + '.'
CACHE_PREFIX += '.'.join(str(num_encode(int(p))) for p in str(time.time()).split('.'))

try:
    BACKLOG_ARCHIVE = settings.BACKLOG_ARCHIVE
    if not os.path.exists(os.path.join(BACKLOG_ARCHIVE, '.git')):
        BACKLOG_ARCHIVE = None
except AttributeError:
    BACKLOG_ARCHIVE = None
except ImportError:
    BACKLOG_ARCHIVE = None

RELEASE = None
__projectdir__ = os.path.abspath(os.path.dirname(__file__))
while __projectdir__ != '/' and not os.path.exists(os.path.join(__projectdir__, 'settings.py')):
    __projectdir__ = os.path.dirname(__projectdir__)
if __projectdir__ != '/' and os.path.exists(os.path.join(__projectdir__, '.git')):
    repo = Repo(__projectdir__)
    for commit in repo.revision_history(repo.head()):
        RELEASE = 'Git: ' + commit.tree
        break
if RELEASE is None:
    try:
        import agilitorelease
        RELEASE = agilitorelease.RELEASE
    except:
        pass
