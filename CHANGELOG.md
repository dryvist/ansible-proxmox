# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.27.2](https://github.com/dryvist/ansible-proxmox/compare/v1.27.1...v1.27.2) (2026-06-13)


### Bug Fixes

* **media_lxc_features:** reconcile TUN passthrough like idmap (pmxcfs-safe) ([#279](https://github.com/dryvist/ansible-proxmox/issues/279)) ([501ed56](https://github.com/dryvist/ansible-proxmox/commit/501ed56f6a575fb695abeb6283fbe89bccee2347))

## [1.27.1](https://github.com/dryvist/ansible-proxmox/compare/v1.27.0...v1.27.1) (2026-06-13)


### Bug Fixes

* **inventory:** fail loud instead of silently using a stale cache ([#278](https://github.com/dryvist/ansible-proxmox/issues/278)) ([1257445](https://github.com/dryvist/ansible-proxmox/commit/1257445e43a3c996cabbca1f58acdca78ee5e3bf))

## [1.27.0](https://github.com/dryvist/ansible-proxmox/compare/v1.26.0...v1.27.0) (2026-06-12)


### Features

* **media_lxc_features:** map shared-data GID 13000 into unprivileged LXCs ([#276](https://github.com/dryvist/ansible-proxmox/issues/276)) ([0cd9016](https://github.com/dryvist/ansible-proxmox/commit/0cd9016d8040b89db8a66fc8d3900c748ebc2fc0))

## [1.26.0](https://github.com/dryvist/ansible-proxmox/compare/v1.25.0...v1.26.0) (2026-06-12)


### Features

* **pve_repositories:** ensure LXC CT templates present on every node ([#273](https://github.com/dryvist/ansible-proxmox/issues/273)) ([2f80875](https://github.com/dryvist/ansible-proxmox/commit/2f80875ed3cbe5108fc28a9a946431df0afb8c2a))

## [1.25.0](https://github.com/dryvist/ansible-proxmox/compare/v1.24.0...v1.25.0) (2026-06-12)


### Features

* **media:** single /bulk/data bind-mount + inventory-derived media guests for the pve2 rebuild ([#270](https://github.com/dryvist/ansible-proxmox/issues/270)) ([4bc6ac8](https://github.com/dryvist/ansible-proxmox/commit/4bc6ac8a525948ee70d57e853111f6c3bab89435))

## [1.24.0](https://github.com/dryvist/ansible-proxmox/compare/v1.23.0...v1.24.0) (2026-06-12)


### Features

* **inventory:** fetch S3 inventory natively via amazon.aws modules ([#266](https://github.com/dryvist/ansible-proxmox/issues/266)) ([76a9ecf](https://github.com/dryvist/ansible-proxmox/commit/76a9ecfd7f76d62ea400441b910190ba20c7f47a))


### Bug Fixes

* **inventory:** S3 resolver works under --check (tempfile has no path in check mode) ([#268](https://github.com/dryvist/ansible-proxmox/issues/268)) ([4381484](https://github.com/dryvist/ansible-proxmox/commit/438148464e9a6f5d162c6a81e308de5526ba4278))

## [1.23.0](https://github.com/dryvist/ansible-proxmox/compare/v1.22.0...v1.23.0) (2026-06-09)


### Features

* **databases:** generic ZFS database namespace + SQLite warm standby ([#263](https://github.com/dryvist/ansible-proxmox/issues/263)) ([05fc07d](https://github.com/dryvist/ansible-proxmox/commit/05fc07d50b1228a75e748450d3efc781fa5beace))

## [1.22.0](https://github.com/dryvist/ansible-proxmox/compare/v1.21.0...v1.22.0) (2026-06-07)


### Features

* **zfs:** rename node pools to tier-named bulk/fast (node-agnostic) ([#259](https://github.com/dryvist/ansible-proxmox/issues/259)) ([b455365](https://github.com/dryvist/ansible-proxmox/commit/b455365819822f36e8a3e72ed8f7d24d9898823a))

## [1.21.0](https://github.com/dryvist/ansible-proxmox/compare/v1.20.0...v1.21.0) (2026-06-07)


### Features

* **commissioning:** codify Proxmox node setup for fully-automated provisioning ([#257](https://github.com/dryvist/ansible-proxmox/issues/257)) ([67706c3](https://github.com/dryvist/ansible-proxmox/commit/67706c3431871da899a34ce7af9e8ff43f5db85a))

## [1.20.0](https://github.com/dryvist/ansible-proxmox/compare/v1.19.0...v1.20.0) (2026-06-07)


### Features

* **syncoid:** replicate Splunk VM disks to pve3 hdd3 (DR leg) ([#255](https://github.com/dryvist/ansible-proxmox/issues/255)) ([b4816a5](https://github.com/dryvist/ansible-proxmox/commit/b4816a53f77cd19eccf3efd23659e517009ad9ce))

## [1.19.0](https://github.com/dryvist/ansible-proxmox/compare/v1.18.0...v1.19.0) (2026-06-06)


### Features

* **node_auto_poweroff:** nightly graceful self-power-off via systemd timer ([#251](https://github.com/dryvist/ansible-proxmox/issues/251)) ([c62cad4](https://github.com/dryvist/ansible-proxmox/commit/c62cad40b073d1834f7887a7186aa79fa3838e11))

## [1.18.0](https://github.com/dryvist/ansible-proxmox/compare/v1.17.0...v1.18.0) (2026-06-04)


### Features

* **idrac_power:** generic IPMI power role + site.yml auto-cycle ([5d8c4b4](https://github.com/dryvist/ansible-proxmox/commit/5d8c4b485913673950f8c195cd06a5c1d5134b4c))

## [1.17.0](https://github.com/dryvist/ansible-proxmox/compare/v1.16.2...v1.17.0) (2026-06-04)


### Features

* **replication:** codify Splunk VM 200 sanoid+syncoid protection ([#244](https://github.com/dryvist/ansible-proxmox/issues/244)) ([64ad255](https://github.com/dryvist/ansible-proxmox/commit/64ad2554ed77bf2c947583baff65c01c1e5d05e8))

## [1.16.2](https://github.com/dryvist/ansible-proxmox/compare/v1.16.1...v1.16.2) (2026-06-04)


### Bug Fixes

* **zfs_pools:** handle datasets with no quota (null) ([#245](https://github.com/dryvist/ansible-proxmox/issues/245)) ([f949a31](https://github.com/dryvist/ansible-proxmox/commit/f949a315b629a4e4be3b4c317e30113c606fdc73))

## [1.16.1](https://github.com/dryvist/ansible-proxmox/compare/v1.16.0...v1.16.1) (2026-06-04)


### Bug Fixes

* **cluster_ssh_trust:** correct non-idempotent changed_when ([#242](https://github.com/dryvist/ansible-proxmox/issues/242)) ([fabe94e](https://github.com/dryvist/ansible-proxmox/commit/fabe94e615f00fdda657ee1c735877c44e1d998d))

## [1.16.0](https://github.com/dryvist/ansible-proxmox/compare/v1.15.0...v1.16.0) (2026-06-04)


### Features

* adopt nix-devenv ansible pre-commit profile ([#213](https://github.com/dryvist/ansible-proxmox/issues/213)) ([f988bc2](https://github.com/dryvist/ansible-proxmox/commit/f988bc2b9d2050e999629e6530a616a28aafb7b2))

## [1.15.0](https://github.com/dryvist/ansible-proxmox/compare/v1.14.0...v1.15.0) (2026-06-04)


### Features

* **cluster_ssh_trust:** automate inter-node SSH known_hosts trust ([#238](https://github.com/dryvist/ansible-proxmox/issues/238)) ([127afc4](https://github.com/dryvist/ansible-proxmox/commit/127afc4fa236a748f2f1bfac42d116f204833487))

## [1.14.0](https://github.com/dryvist/ansible-proxmox/compare/v1.13.0...v1.14.0) (2026-06-04)


### Features

* **nas_storage:** macOS/Time Machine/Infuse SMB support ([#234](https://github.com/dryvist/ansible-proxmox/issues/234)) ([1369611](https://github.com/dryvist/ansible-proxmox/commit/1369611006f2fb4299424d293d3ffe25f1535c52))

## [1.13.0](https://github.com/dryvist/ansible-proxmox/compare/v1.12.0...v1.13.0) (2026-06-04)


### Features

* **syncoid:** cross-node ZFS replication role (layer 2) ([#235](https://github.com/dryvist/ansible-proxmox/issues/235)) ([b151c74](https://github.com/dryvist/ansible-proxmox/commit/b151c74158df216ff5848bd5d5817e8faae327ee))

## [1.12.0](https://github.com/dryvist/ansible-proxmox/compare/v1.11.0...v1.12.0) (2026-06-04)


### Features

* **sanoid:** ZFS snapshot retention role (layer-1 protection) ([#231](https://github.com/dryvist/ansible-proxmox/issues/231)) ([0133af3](https://github.com/dryvist/ansible-proxmox/commit/0133af3d2ba17bccf4995c9f4ac8223e0e3ffcaf))

## [1.11.0](https://github.com/dryvist/ansible-proxmox/compare/v1.10.0...v1.11.0) (2026-06-04)


### Features

* **proxmox_monitoring:** ZFS pool capacity alerts via ntfy ([#230](https://github.com/dryvist/ansible-proxmox/issues/230)) ([a32a38d](https://github.com/dryvist/ansible-proxmox/commit/a32a38d301b5c1ccac2db6280ddc4e0b18b346a2))

## [1.10.0](https://github.com/dryvist/ansible-proxmox/compare/v1.9.1...v1.10.0) (2026-06-04)


### Features

* **zfs_pools:** idempotent per-dataset ZFS properties ([#228](https://github.com/dryvist/ansible-proxmox/issues/228)) ([71107a8](https://github.com/dryvist/ansible-proxmox/commit/71107a8686d1fcca41df9ccdfd643fee51b1e6f5))

## [1.9.1](https://github.com/dryvist/ansible-proxmox/compare/v1.9.0...v1.9.1) (2026-06-03)


### Bug Fixes

* **lxc_gpu_features:** idempotent GPU passthrough via lineinfile ([00571ac](https://github.com/dryvist/ansible-proxmox/commit/00571acb7f2ae0444fa0f33b6ee3094d9aa5d1bf))

## [1.9.0](https://github.com/dryvist/ansible-proxmox/compare/v1.8.0...v1.9.0) (2026-06-03)


### Features

* **lxc_gpu_features:** pass AMD RX 6800 into hermes-infer LXC ([f8f958a](https://github.com/dryvist/ansible-proxmox/commit/f8f958a531e57600bc88dbbaa1f6d5a492836dd7))

## [1.8.0](https://github.com/dryvist/ansible-proxmox/compare/v1.7.2...v1.8.0) (2026-06-01)


### Features

* **idrac_kiosk:** add pve kiosk showing both iDRAC consoles ([#205](https://github.com/dryvist/ansible-proxmox/issues/205)) ([ea111d4](https://github.com/dryvist/ansible-proxmox/commit/ea111d41dc5549026be8ae1095d41d546f79bf2f))
* **media_lxc_features:** apply root-only LXC features (bind-mounts, keyctl, /dev/net/tun) as root ([#215](https://github.com/dryvist/ansible-proxmox/issues/215)) ([52c456f](https://github.com/dryvist/ansible-proxmox/commit/52c456f62fb4332c77546e829e43491566b55d62))
* **playbooks:** add PVE point-upgrade play (snapshot + repos + upgrade) ([#208](https://github.com/dryvist/ansible-proxmox/issues/208)) ([9ea8e75](https://github.com/dryvist/ansible-proxmox/commit/9ea8e757e0c479737966405421ce460822ba76d5))
* **pve_cluster:** add pve3 as cluster member, decoupled from storage ([#217](https://github.com/dryvist/ansible-proxmox/issues/217)) ([af87178](https://github.com/dryvist/ansible-proxmox/commit/af87178cd0879dbd4905b90df2bedd4edbd88957))
* **pve_cluster:** idempotent cluster formation + multinode inventory ([#211](https://github.com/dryvist/ansible-proxmox/issues/211)) ([3314e22](https://github.com/dryvist/ansible-proxmox/commit/3314e2253bede63314ec087eb8ba6837856b446f))
* **zfs_pools:** codify per-node ZFS storage from terraform node_storage ([#206](https://github.com/dryvist/ansible-proxmox/issues/206)) ([eb0f3ed](https://github.com/dryvist/ansible-proxmox/commit/eb0f3ed0a54c0246ed3c02fbfeaa53a795a0ba9e))


### Bug Fixes

* **ci:** repoint release-please caller to org-native reusable workflow ([#218](https://github.com/dryvist/ansible-proxmox/issues/218)) ([09e40a2](https://github.com/dryvist/ansible-proxmox/commit/09e40a2f9ff6239c48bee98896b7c1bf212391be))
* **ci:** retarget reusable-workflow uses: refs to current org homes ([#207](https://github.com/dryvist/ansible-proxmox/issues/207)) ([999e116](https://github.com/dryvist/ansible-proxmox/commit/999e1160043279cdae84735ae6893a901c4d660e))
* **tests:** align inventory_load test with pve→pve1 rename ([6e03789](https://github.com/dryvist/ansible-proxmox/commit/6e03789ff9e13fa41a0f120a2f7f1dd580dac495))

## [1.7.2](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.7.1...v1.7.2) (2026-05-23)


### Bug Fixes

* **pre-commit:** exclude release-please CHANGELOG.md from markdownlint (closes [#200](https://github.com/JacobPEvans/ansible-proxmox/issues/200)) ([#201](https://github.com/JacobPEvans/ansible-proxmox/issues/201)) ([f09094c](https://github.com/JacobPEvans/ansible-proxmox/commit/f09094c3e706291d563b518eec2f30e89818e8bf))

## [1.7.1](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.7.0...v1.7.1) (2026-05-22)


### Bug Fixes

* **deps:** refresh gh-aw action SHA pins ([#195](https://github.com/JacobPEvans/ansible-proxmox/issues/195)) ([c51242b](https://github.com/JacobPEvans/ansible-proxmox/commit/c51242b1f40e6d499d18e08c7b0a39dc9daecf85))

## [1.7.0](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.6.2...v1.7.0) (2026-05-20)


### Features

* **playbooks:** add PowerEdge commissioning play for PVE 9 cluster join ([#192](https://github.com/JacobPEvans/ansible-proxmox/issues/192)) ([aa594a1](https://github.com/JacobPEvans/ansible-proxmox/commit/aa594a1a5609aa7dabf9820823744f8043f87a8d))

## [1.6.2](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.6.1...v1.6.2) (2026-05-18)


### Bug Fixes

* **deps:** refresh gh-aw action SHA pins ([#189](https://github.com/JacobPEvans/ansible-proxmox/issues/189)) ([d94a129](https://github.com/JacobPEvans/ansible-proxmox/commit/d94a12937299918ba39b51ebc1e483b6dc148fe2))

## [1.6.1](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.6.0...v1.6.1) (2026-05-15)


### Bug Fixes

* **ntp:** role hardening from downstream review feedback ([#186](https://github.com/JacobPEvans/ansible-proxmox/issues/186)) ([0f8b73a](https://github.com/JacobPEvans/ansible-proxmox/commit/0f8b73a4fd9f23fbe092417caabea798f7688647))

## [1.6.0](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.5.11...v1.6.0) (2026-05-14)


### Features

* **ntp:** add server mode and wire role into proxmox play ([#182](https://github.com/JacobPEvans/ansible-proxmox/issues/182)) ([2a96f23](https://github.com/JacobPEvans/ansible-proxmox/commit/2a96f2377cac96e252994a3ae9d6da37b4e4f381)), closes [#179](https://github.com/JacobPEvans/ansible-proxmox/issues/179)

## [1.5.11](https://github.com/JacobPEvans/ansible-proxmox/compare/v1.5.10...v1.5.11) (2026-05-14)


### Bug Fixes

* **deps:** refresh gh-aw action SHA pins ([#180](https://github.com/JacobPEvans/ansible-proxmox/issues/180)) ([1ebc217](https://github.com/JacobPEvans/ansible-proxmox/commit/1ebc217b100e6958da6c504d2ab1ae5c25a3eb9c))

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
