# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `ignore_status_codes` setting to skip tracking for responses with the given HTTP
  status codes (e.g. `[301, 302]` to not track redirects).
- Support for Django 6.x and Python 3.15.

### Changed
- Minimum supported Celery version is now 5.2.0.
- The CI matrix now also tests the minimum supported dependency versions and is
  aligned with the tox environments.

### Documentation
- Clarified `url_masks` usage: patterns should not be anchored on a trailing `/`,
  since `request.path` does not always end with one.

## [0.3.4] - 2026-09-17

### Changed
- Reduced and improved logging in the middleware and transport layer.

## [0.3.3] - 2026-09-16

### Security
- When `token_auth` is configured, single tracking events are now sent through the
  bulk tracking API as a POST body instead of a GET query parameter, so the auth
  token no longer ends up in logs, proxies or browser history.

## [0.3.2] - 2026-09-09

### Added
- DEBUG-level logging of the resolved Matomo config, the selected backend and the
  per-request tracking parameters, to make diagnosing tracking issues easier.

### Fixed
- `flush_matomo_batch` read the config key `TOKEN_AUTH` instead of the documented
  `token_auth`, which silently dropped the token from bulk tracking requests.

## [0.3.1] - 2026-09-03

### Added
- `url_masks` setting to collapse dynamic path segments (e.g. record ids) into a
  fixed placeholder before the URL is sent to Matomo.

### Fixed
- `DirectTrackingBackend` had a mismatched `send()` signature and dispatched the
  Celery task instead of sending synchronously, so it was broken whenever selected.

### Changed
- The package version is now derived from git tags via `setuptools_scm`.
- Build and dependency tooling switched from Poetry to uv (with `tox-uv` for tests).
- Updated the Django test matrix and GitHub Actions versions.

## [0.3.0] - 2026-02-25

### Added
- Pluggable tracking backends, selectable via the `backend` setting:
  - `CeleryTrackingBackend` (default) — one Celery task per pageview.
  - `RedisBatchTrackingBackend` — queues events in Redis and bulk-sends them via the
    periodic `flush_matomo_batch` Celery Beat task. Requires the new `bulk_send`
    extra (`redis`) and the `redis_url` / `redis_key` settings.
  - `DirectTrackingBackend` — sends synchronously in the request (for debugging).
- Support for Python 3.13 and 3.14.

### Changed
- Refactored the middleware: it now only collects tracking data, while a new
  transport layer handles encoding and sending to Matomo.

## [0.2.0] - 2025-09-20

### Added
- `timeout` setting for tracking requests sent by the middleware (#2).
- Support for Django 4.2 and 5.x.

### Changed
- Python 3.10–3.12 is now required.
- Migrated project metadata to the standard `[project]` table in `pyproject.toml`.
- Releases are published to PyPI using trusted publishing.

## [0.1.3] - 2023-03-28

### Fixed
- The full URL (including hostname) is now sent to Matomo.
- The client IP (`cip` parameter) is only sent when `token_auth` is configured.

## [0.1.2] - 2023-03-28

### Added
- Logging statement when a tracking request is sent.

## [0.1.1] - 2023-03-28

### Fixed
- Publishing workflow.

## [0.1.0] - 2023-03-27

### Added
- Initial release: Django middleware that tracks page views server-side through the
  Matomo tracking API, sending requests asynchronously via Celery.

[Unreleased]: https://github.com/DessimozLab/django-matomo-api-tracking/compare/v0.3.4...HEAD
[0.3.4]: https://github.com/DessimozLab/django-matomo-api-tracking/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/DessimozLab/django-matomo-api-tracking/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/DessimozLab/django-matomo-api-tracking/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/DessimozLab/django-matomo-api-tracking/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/DessimozLab/django-matomo-api-tracking/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/DessimozLab/django-matomo-api-tracking/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/DessimozLab/django-matomo-api-tracking/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/DessimozLab/django-matomo-api-tracking/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/DessimozLab/django-matomo-api-tracking/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/DessimozLab/django-matomo-api-tracking/releases/tag/v0.1.0
