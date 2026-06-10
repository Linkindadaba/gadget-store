# TODO

- [ ] Identify why static CSS is not applying in deployed site (confirm 404/200 for /static/css/*).
- [ ] Ensure WhiteNoise/STATICFILES configuration is correct for production.
- [ ] Add/adjust settings for `STATICFILES_STORAGE` + `WHITENOISE_USE_FINDERS` if needed.
- [ ] Run `python manage.py collectstatic` (and optionally `runserver` locally) to verify static assets.
- [ ] Re-test deployed site to confirm styling loads (Bootstrap + custom CSS).

