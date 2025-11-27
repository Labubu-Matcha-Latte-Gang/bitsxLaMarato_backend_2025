"""
Testing settings module mirroring globals but with test-friendly defaults.
"""

from globals import *  # noqa: F401,F403

TESTING = True
DB_AUTO_MIGRATE = False
