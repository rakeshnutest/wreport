# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog], and this project adheres to
[Semantic Versioning].


## [Unreleased]

## [1.0.2] - 2022-07-07
### Fixed
- Fixed parsing error with SPDK devices in diskawait report
  ([ILL-305])

## [1.0.1] - 2022-06-22
### Fixed
- Initialize status to 0 for each node prior to testing disks
  ([ILL-302])

## [1.0.0] - 2022-06-16
### Added
- Add an SSD/NVMe write await report
  ([ILL-300])

### Changed
- Started using a Changelog to track this project


[Keep a ChangeLog]: https://keepachangelog.com/en/1.0.0/
[README.md]: README.md
[Semantic Versioning]: https://semver.org/spec/v2.0.0.html

[ILL-300]: https://jira.nutanix.com/browse/ILL-300
[ILL-302]: https://jira.nutanix.com/browse/ILL-302
[ILL-305]: https://jira.nutanix.com/browse/ILL-305

[1.0.0]: https://gitlab.rtp.nutanix.com/ntnx/wreport/-/tags/1.0.0
[1.0.1]: https://gitlab.rtp.nutanix.com/ntnx/wreport/-/compare/1.0.0...1.0.1
[1.0.2]: https://gitlab.rtp.nutanix.com/ntnx/wreport/-/compare/1.0.1...1.0.2
