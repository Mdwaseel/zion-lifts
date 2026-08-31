"""No models.

Authentication reuses ``django.contrib.auth.models.User`` — the project already
has migrations and live data against it, and a second user table would give the
site two sources of truth for who may sign in.

CAPTCHA challenges live for five minutes and are single-use, so they are held in
the cache (see ``captcha.py``) rather than in a table that would need sweeping.
Refresh-token revocation is handled by SimpleJWT's ``token_blacklist`` app,
which brings its own models.
"""
