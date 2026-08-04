"""Constants shared across every gateway and both engines.

Values that are facts about a *specific* gateway — its endpoints, its success codes, its timestamp
format — live in that gateway's own ``constants.py``. Only what genuinely applies everywhere
belongs here.
"""

DEFAULT_TIMEOUT = 15.0
"""Seconds. Long enough for a sluggish IPG, short enough that a dead one is not a hung worker."""
