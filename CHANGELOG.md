# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1](https://github.com/mohmdstag7-cmd/Tr/compare/v0.1.0...v0.1.1) (2026-09-28)


### Bug Fixes

* **test:** use startswith() for api.github.com URL check (CodeQL SSRF false positive) ([7d56cbc](https://github.com/mohmdstag7-cmd/Tr/commit/7d56cbc850f89090c8e4268e141eb446bd7ea8cf))
* **updater:** use GitHub Releases API + tag_name for latest.json discovery ([78df129](https://github.com/mohmdstag7-cmd/Tr/commit/78df129af3d8446f0557941af0863ecf6421eb74))

## [Unreleased]

### Added
- In-app auto-updater: checks GitHub Releases for newer versions, downloads the installer, verifies SHA-256, and silently installs + relaunches (Part J). Includes UpdateBanner widget, UpdateDialog with progress, semver comparison, and rollback-to-previous-installer support.

## [0.1.0] - 2025-01-01

### Added
- Initial release.
