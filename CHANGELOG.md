# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.10](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.5.9...v1.5.10) (2026-05-11)


### Bug Fixes

* **deps:** refresh gh-aw action SHA pins ([#175](https://github.com/JacobPEvans/ansible-proxmox/issues/175)) ([306c514](https://github.com/JacobPEvans/ansible-proxmox/commit/306c5142202b08a690f94a3f7f2186b41ef63867))

## [1.5.9](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.5.8...v1.5.9) (2026-05-07)

### Bug Fixes

* **deps:** refresh gh-aw action SHA pins
  ([#171](https://github.com/JacobPEvans/ansible-proxmox/issues/171))
  ([2dc3ebe](https://github.com/JacobPEvans/ansible-proxmox/commit/2dc3ebe8b08c083f61da399afb3265a11aabad26))

## [1.5.8](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.5.7...v1.5.8) (2026-05-03)

### Bug Fixes

* **ci:** remove deprecated app-id secret passthrough
  ([b9e86e3](https://github.com/JacobPEvans/ansible-proxmox/commit/b9e86e3e4cf04b9880781104c3451ec49a56af35))

## [1.5.7](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.5.6...v1.5.7) (2026-05-03)

### Bug Fixes

* **deps:** refresh gh-aw action SHA pins
  ([#164](https://github.com/JacobPEvans/ansible-proxmox/issues/164))
  ([ebdcee3](https://github.com/JacobPEvans/ansible-proxmox/commit/ebdcee3cccb42c2a7a834d9993f05bf668bd279a))

## [1.5.6](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.5.5...v1.5.6) (2026-05-03)

### Bug Fixes

* **ci:** import shared health-audit config from ai-workflows
  ([#185](https://github.com/JacobPEvans/ansible-proxmox/issues/185))
  ([#159](https://github.com/JacobPEvans/ansible-proxmox/issues/159))
  ([b43d51f](https://github.com/JacobPEvans/ansible-proxmox/commit/b43d51f8aa36050e7cbc2105be953b79bbb7249e))

## [1.5.5](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.5.4...v1.5.5) (2026-04-29)

### Bug Fixes

* **deps:** refresh gh-aw action SHA pins
  ([#160](https://github.com/JacobPEvans/ansible-proxmox/issues/160))
  ([951448c](https://github.com/JacobPEvans/ansible-proxmox/commit/951448c9f1b35c6a27ef6f062230873cc35c0fd5))
* **nas_storage:** correct Jinja syntax error blocking Samba share validation
  ([#162](https://github.com/JacobPEvans/ansible-proxmox/issues/162))
  ([8e6db4f](https://github.com/JacobPEvans/ansible-proxmox/commit/8e6db4f5cc06b7d4d79af616cab2311bb5246d1a))

## [1.5.4](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.5.3...v1.5.4) (2026-04-26)

### Bug Fixes

* **deps:** refresh gh-aw action SHA pins
  ([bae16e0](https://github.com/JacobPEvans/ansible-proxmox/commit/bae16e0325aa963520aff33d87dff643aca0ddcf))

## [1.5.3](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.5.2...v1.5.3) (2026-04-25)

### Bug Fixes

* **ci:** move pip pins to requirements-ci.txt for Renovate tracking
  ([#143](https://github.com/JacobPEvans/ansible-proxmox/issues/143))
  ([e0463ca](https://github.com/JacobPEvans/ansible-proxmox/commit/e0463ca4dad8c839a73fc016a12fac48cb91febd))

## [1.5.2](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.5.1...v1.5.2) (2026-04-24)

### Bug Fixes

* **deps:** refresh gh-aw action SHA pins
  ([#139](https://github.com/JacobPEvans/ansible-proxmox/issues/139))
  ([cf122d4](https://github.com/JacobPEvans/ansible-proxmox/commit/cf122d4f390fcb907700b589acd98efad60dc3c7))

## [1.5.1](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.5.0...v1.5.1) (2026-04-21)

### Bug Fixes

* **ci:** add gh-aw-pin-refresh workflow and recompile lock files
  ([e9a45d3](https://github.com/JacobPEvans/ansible-proxmox/commit/e9a45d3c5260e8e5d5e7f9f75627fd852f55714d)),
  closes [#136](https://github.com/JacobPEvans/ansible-proxmox/issues/136)

## [1.5.0](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.4.2...v1.5.0) (2026-04-18)

### Features

* automate Samba NAS provisioning
  ([3e4e80f](https://github.com/JacobPEvans/ansible-proxmox/commit/3e4e80f8136b97a9324de5aaeb8bd3450acd982a))

## [1.4.2](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.4.1...v1.4.2) (2026-04-13)

### Bug Fixes

* add automation bots to AI Moderator skip-bots
  ([#125](https://github.com/JacobPEvans/ansible-proxmox/issues/125))
  ([72b8eb8](https://github.com/JacobPEvans/ansible-proxmox/commit/72b8eb86028191c08c8e87fe0b3f9327ae1d3760))

## [1.4.0](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.3.1...v1.4.0) (2026-04-12)

### Maintenance

* internal tooling updates

## [1.4.1](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.4.0...v1.4.1) (2026-04-13)

### Bug Fixes

* **gh-aw:** recompile agentic workflow lock files with v0.68.1
  ([5059278](https://github.com/JacobPEvans/ansible-proxmox/commit/50592788ff306b9d4204d816b8914c881eabb78d))

## [1.3.1](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.3.0...v1.3.1) (2026-04-11)

### Bug Fixes

* **nas_storage:** wrap testparm validate in sh -c
  ([#100](https://github.com/JacobPEvans/ansible-proxmox/issues/100))
  ([1b5b374](https://github.com/JacobPEvans/ansible-proxmox/commit/1b5b374d7410a97272156467083896808e236ffd))

## [1.3.0](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.2.5...v1.3.0) (2026-04-07)

### Features

* add AI merge gate and Copilot setup steps
  ([#98](https://github.com/JacobPEvans/ansible-proxmox/issues/98))
  ([4d00db0](https://github.com/JacobPEvans/ansible-proxmox/commit/4d00db0c5744b030ca8433d26c0e2c0f1a5665ea))

## [1.2.5](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.2.4...v1.2.5) (2026-04-06)

### Bug Fixes

* address AI review feedback on SSH key handling
  ([#96](https://github.com/JacobPEvans/ansible-proxmox/issues/96))
  ([3d6ccb6](https://github.com/JacobPEvans/ansible-proxmox/commit/3d6ccb6c63d66bda3009550f860738be3806cc14))

## [1.2.4](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.2.3...v1.2.4) (2026-04-04)

### Bug Fixes

* eliminate SSH key temp file — use ssh-agent or key path
  ([#91](https://github.com/JacobPEvans/ansible-proxmox/issues/91))
  ([1f740b9](https://github.com/JacobPEvans/ansible-proxmox/commit/1f740b973fad919a1a62e468fdf00a674abb3160))

## [1.2.3](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.2.2...v1.2.3) (2026-04-04)

### Bug Fixes

* remove claude-review workflow — replaced by Gemini + Copilot
  ([#93](https://github.com/JacobPEvans/ansible-proxmox/issues/93))
  ([403de64](https://github.com/JacobPEvans/ansible-proxmox/commit/403de64b1a6181952dd81a9e072c3bccc04199b1))

## [1.2.2](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.2.1...v1.2.2) (2026-03-30)

### Bug Fixes

* use nix-devenv ansible shell instead of local flake.nix
  ([#89](https://github.com/JacobPEvans/ansible-proxmox/issues/89))
  ([b65c99f](https://github.com/JacobPEvans/ansible-proxmox/commit/b65c99f267968619374bd9ee9c9b2071277fc26b))

## [1.2.1](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.2.0...v1.2.1) (2026-03-26)

### Bug Fixes

* add systemd restart policies for all native services
  ([#87](https://github.com/JacobPEvans/ansible-proxmox/issues/87))
  ([d731e44](https://github.com/JacobPEvans/ansible-proxmox/commit/d731e44c7332080479a14b85c179ac4461fc9292))

## [1.2.0](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.1.0...v1.2.0) (2026-03-25)

### Features

* add nas_storage role for Samba NAS provisioning on ZFS
  ([#78](https://github.com/JacobPEvans/ansible-proxmox/issues/78))
  ([79ab2fe](https://github.com/JacobPEvans/ansible-proxmox/commit/79ab2fe3da92d89db20fafbb6a734c2c3bb83bf6))

### Bug Fixes

* add release-please config for manifest mode
  ([cecbda8](https://github.com/JacobPEvans/ansible-proxmox/commit/cecbda87c100f69b06c3aa877593904231a6c718))
* **ci:** add pull-requests: write for release-please auto-approval
  ([#82](https://github.com/JacobPEvans/ansible-proxmox/issues/82))
  ([80eb5bf](https://github.com/JacobPEvans/ansible-proxmox/commit/80eb5bf5f67b5ca900c33a4dd9afca0f9b5c6cde))
* **ci:** implement Merge Gatekeeper pattern
  ([#79](https://github.com/JacobPEvans/ansible-proxmox/issues/79))
  ([d64ffd5](https://github.com/JacobPEvans/ansible-proxmox/commit/d64ffd531ae5ee05fb53dffae71f963615621c88))
* replace uv run with bare commands for Nix dev shell
  ([#85](https://github.com/JacobPEvans/ansible-proxmox/issues/85))
  ([805e015](https://github.com/JacobPEvans/ansible-proxmox/commit/805e015b093525e382e35dbf7d4b271cbba06249))
* sync release-please permissions, VERSION, and remove redundant config
  ([fa36f25](https://github.com/JacobPEvans/ansible-proxmox/commit/fa36f259703b113bf7e0d7a05ac5868f26e29d36))

## [1.1.0](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.0.0...v1.1.0) (2026-03-11)

### Features

* add daily repo health audit agentic workflow
  ([#75](https://github.com/JacobPEvans/ansible-proxmox/issues/75))
  ([061bc4a](https://github.com/JacobPEvans/ansible-proxmox/commit/061bc4a6feff2ecb7f695086a8e9a65b8e1a0f64))
* add GitHub Copilot agentic workflows
  ([#56](https://github.com/JacobPEvans/ansible-proxmox/issues/56))
  ([677f02a](https://github.com/JacobPEvans/ansible-proxmox/commit/677f02a51fb056c0116b8b97f358857a803b3152))
* add per-repo devShell
  ([#54](https://github.com/JacobPEvans/ansible-proxmox/issues/54))
  ([aea563b](https://github.com/JacobPEvans/ansible-proxmox/commit/aea563be1b180d9efb4e194335a5e8f956d680fa))
* add proxmox_monitoring role for crash investigation
  ([#32](https://github.com/JacobPEvans/ansible-proxmox/issues/32))
  ([da6bc18](https://github.com/JacobPEvans/ansible-proxmox/commit/da6bc181b966cf39f98e87b72738b9ef9971fea3))
* add scheduled AI workflow callers
  ([#65](https://github.com/JacobPEvans/ansible-proxmox/issues/65))
  ([70ce9dd](https://github.com/JacobPEvans/ansible-proxmox/commit/70ce9dd6ddc3aea6ccf459a9fa8422555ca88666))
* crash diagnostics role with kdump and kernel panic settings
  ([#31](https://github.com/JacobPEvans/ansible-proxmox/issues/31))
  ([d9dcb5f](https://github.com/JacobPEvans/ansible-proxmox/commit/d9dcb5fa09164ace9f76731f7543fe16d3e231d6))
* disable automatic triggers on Claude-executing workflows
  ([1e2be59](https://github.com/JacobPEvans/ansible-proxmox/commit/1e2be59c8801f631ca736d41001c78b98998d568))
* **kernel_tuning:** add C-state disable option for AMD stability
  ([#38](https://github.com/JacobPEvans/ansible-proxmox/issues/38))
  ([b1c2a09](https://github.com/JacobPEvans/ansible-proxmox/commit/b1c2a09dd0a160d3a3896bfd255e1c26ddb25291))
* **kernel_tuning:** add Proxmox boot params for AMD Zen1 stability
  ([#36](https://github.com/JacobPEvans/ansible-proxmox/issues/36))
  ([43de2de](https://github.com/JacobPEvans/ansible-proxmox/commit/43de2de45b9b3258310cda02d2433bf74c625704))
* **lxc:** add lxc_features role to manage container features as code
  ([#51](https://github.com/JacobPEvans/ansible-proxmox/issues/51))
  ([a9c4ee7](https://github.com/JacobPEvans/ansible-proxmox/commit/a9c4ee720576d22c6ac50932cceeec2afcadee09))
* **monitoring:** add MCE/EDAC hardware error detection
  ([#34](https://github.com/JacobPEvans/ansible-proxmox/issues/34))
  ([e67d0ce](https://github.com/JacobPEvans/ansible-proxmox/commit/e67d0ce06a9f8c9ea45aa20ade4da5ae5bb9d207))
* **renovate:** extend shared preset, remove duplicated rules
  ([ffc73cc](https://github.com/JacobPEvans/ansible-proxmox/commit/ffc73cc1328a59501c3114bcc3231db85a8f6324))

### Bug Fixes

* change .docs symlink to relative path
  ([#40](https://github.com/JacobPEvans/ansible-proxmox/issues/40))
  ([a78c87d](https://github.com/JacobPEvans/ansible-proxmox/commit/a78c87d3cf938e8255ac2e0e9b7a8f20a891cc37))
* **kernel_tuning:** re-enable SMT in boot parameters
  ([#41](https://github.com/JacobPEvans/ansible-proxmox/issues/41))
  ([8cb11b7](https://github.com/JacobPEvans/ansible-proxmox/commit/8cb11b73edb799e806524f61635451ec70068f2d))
* **kernel_tuning:** support both UEFI and Legacy BIOS boot methods
  ([#37](https://github.com/JacobPEvans/ansible-proxmox/issues/37))
  ([1ede20e](https://github.com/JacobPEvans/ansible-proxmox/commit/1ede20e8ef6f1e5aa49cb5dfd93cac9244e8183d))

## [Unreleased]

## [1.0.0] - 2025-01-12

### Added

* Initial repository structure
* Role: `common` - Base packages and SSH configuration
* Role: `zfs_swap` - ZFS ZVOL swap configuration (96 GB default)
* Role: `kernel_tuning` - Sysctl settings for NVMe and memory management
* Role: `ulimits` - System-wide file descriptor and process limits
* Role: `crash_diagnostics` - Kernel crash diagnostics and hardware error monitoring
* Role: `proxmox_monitoring` - System monitoring (sysstat, atop, crash-monitor, healthchecks.io)
* Role: `lxc_features` - LXC container feature flags (fuse, nesting, keyctl)
* GitHub Actions workflow for ansible-lint
* GitHub Actions workflow for Molecule tests
* Molecule test configuration for role validation
* Renovate configuration for automated dependency updates
* Pre-commit hooks configuration

[Unreleased]: https://github.com/JacobPEvans/ansible-proxmox/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/JacobPEvans/ansible-proxmox/releases/tag/v1.0.0
