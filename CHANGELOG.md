# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.54.0](https://github.com/dryvist/ansible-proxmox/compare/v1.53.0...v1.54.0) (2026-07-16)


### Features

* **ssh_ca_trust:** distribute OpenBao SSH client-CA trust to PVE nodes and LXCs ([#410](https://github.com/dryvist/ansible-proxmox/issues/410)) ([ffd9c53](https://github.com/dryvist/ansible-proxmox/commit/ffd9c53b3370adabb047393cc17f5aff8f354ea6))

## [1.53.0](https://github.com/dryvist/ansible-proxmox/compare/v1.52.0...v1.53.0) (2026-07-13)


### Features

* consume RustFS inventory with OpenBao ([#406](https://github.com/dryvist/ansible-proxmox/issues/406)) ([fb4c998](https://github.com/dryvist/ansible-proxmox/commit/fb4c998b7bedb4a43497a997a7150adb88b58827))

## [1.52.0](https://github.com/dryvist/ansible-proxmox/compare/v1.51.1...v1.52.0) (2026-07-11)


### Features

* **media_lxc_features:** NFS library mount + staged relocation prereqs ([#395](https://github.com/dryvist/ansible-proxmox/issues/395)) ([#397](https://github.com/dryvist/ansible-proxmox/issues/397)) ([1e5ca32](https://github.com/dryvist/ansible-proxmox/commit/1e5ca3277e6c0b17e904f2d4c8582cf4604d59e2))

## [1.51.1](https://github.com/dryvist/ansible-proxmox/compare/v1.51.0...v1.51.1) (2026-07-10)


### Bug Fixes

* **standby:** accept-new host keys on pull SSH + valid Documentation URLs ([a40c01c](https://github.com/dryvist/ansible-proxmox/commit/a40c01cb0a32e950da6f283187a9225bdd422f17))

## [1.51.0](https://github.com/dryvist/ansible-proxmox/compare/v1.50.0...v1.51.0) (2026-07-10)


### Features

* **dr:** postgres_standby role — replicated dump archive + Tier-2 upload ([27cd21a](https://github.com/dryvist/ansible-proxmox/commit/27cd21a9ffd7ff5c622b26e3fe67a57dee70ab8b))

## [1.50.0](https://github.com/dryvist/ansible-proxmox/compare/v1.49.2...v1.50.0) (2026-07-10)


### Features

* **docker_lxc_features:** select agentgateway-tagged docker guests ([#393](https://github.com/dryvist/ansible-proxmox/issues/393)) ([c588683](https://github.com/dryvist/ansible-proxmox/commit/c58868300e286e795cfd96f4f8543addcaa026ab))

## [1.49.2](https://github.com/dryvist/ansible-proxmox/compare/v1.49.1...v1.49.2) (2026-07-08)


### Bug Fixes

* **idrac_kiosk:** FQDN default instead of a hardcoded internal IP ([#388](https://github.com/dryvist/ansible-proxmox/issues/388)) ([e6fbcba](https://github.com/dryvist/ansible-proxmox/commit/e6fbcba3f84d0cb961ee317bba628141ae3f9508)), closes [#378](https://github.com/dryvist/ansible-proxmox/issues/378)

## [1.49.1](https://github.com/dryvist/ansible-proxmox/compare/v1.49.0...v1.49.1) (2026-07-08)


### Bug Fixes

* **ntp,lint:** converge container guard drift + fix stale lint glob ([#385](https://github.com/dryvist/ansible-proxmox/issues/385)) ([1383f90](https://github.com/dryvist/ansible-proxmox/commit/1383f901306b3ccdcf0be89c512e3262a830116e))

## [1.49.0](https://github.com/dryvist/ansible-proxmox/compare/v1.48.1...v1.49.0) (2026-07-08)


### Features

* **common:** enforce UTC timezone on every node ([#383](https://github.com/dryvist/ansible-proxmox/issues/383)) ([1928bc7](https://github.com/dryvist/ansible-proxmox/commit/1928bc7ab95030046d1d02c8d03b640aee384e8d))

## [1.48.1](https://github.com/dryvist/ansible-proxmox/compare/v1.48.0...v1.48.1) (2026-07-08)


### Bug Fixes

* **pve_syslog_forwarder:** pin imfile state dir so the isolated -N1 validate passes ([#381](https://github.com/dryvist/ansible-proxmox/issues/381)) ([8f0e43c](https://github.com/dryvist/ansible-proxmox/commit/8f0e43c3611a7990b74a7ff2b00a7f56c0e40e9a))

## [1.48.0](https://github.com/dryvist/ansible-proxmox/compare/v1.47.3...v1.48.0) (2026-07-08)


### Features

* **pve_syslog_forwarder:** ship pve-firewall drop logs to the os index ([#379](https://github.com/dryvist/ansible-proxmox/issues/379)) ([8a3f9a8](https://github.com/dryvist/ansible-proxmox/commit/8a3f9a8dec69012918d1202aec787fa8e24c968e))

## [1.47.3](https://github.com/dryvist/ansible-proxmox/compare/v1.47.2...v1.47.3) (2026-07-08)


### Bug Fixes

* **pve_node_exporter:** pin the 1.9.1 tarball checksums from the release sums ([#376](https://github.com/dryvist/ansible-proxmox/issues/376)) ([bdb8340](https://github.com/dryvist/ansible-proxmox/commit/bdb83405e2ef3ed71cc45dadd2dbd1827149a78a))

## [1.47.2](https://github.com/dryvist/ansible-proxmox/compare/v1.47.1...v1.47.2) (2026-07-08)


### Bug Fixes

* **media_lxc_features:** add the *arr recycle bin to the /data skeleton ([#374](https://github.com/dryvist/ansible-proxmox/issues/374)) ([1610ff1](https://github.com/dryvist/ansible-proxmox/commit/1610ff1b3e9fc812d869d5824cd349dea1e8cec5))

## [1.47.1](https://github.com/dryvist/ansible-proxmox/compare/v1.47.0...v1.47.1) (2026-07-08)


### Bug Fixes

* **media_lxc_features:** honor idmap punch-through in config-owner chown ([#372](https://github.com/dryvist/ansible-proxmox/issues/372)) ([2bc9686](https://github.com/dryvist/ansible-proxmox/commit/2bc9686165b43d4e3cdf29d78cb30b0139abb1d5))

## [1.47.0](https://github.com/dryvist/ansible-proxmox/compare/v1.46.0...v1.47.0) (2026-07-07)


### Features

* **pve_node_exporter:** install prometheus node_exporter on PVE hosts ([#369](https://github.com/dryvist/ansible-proxmox/issues/369)) ([edda6d0](https://github.com/dryvist/ansible-proxmox/commit/edda6d0b02057f5e88655f34b3a37ff2533740d4))

## [1.46.0](https://github.com/dryvist/ansible-proxmox/compare/v1.45.0...v1.46.0) (2026-07-07)


### Features

* **pve_syslog_forwarder:** forward PVE node logs to the central syslog pipeline ([#368](https://github.com/dryvist/ansible-proxmox/issues/368)) ([c6c9ee9](https://github.com/dryvist/ansible-proxmox/commit/c6c9ee9987c9f23c1f9c8318fa9581bdf23efb88))

## [1.45.0](https://github.com/dryvist/ansible-proxmox/compare/v1.44.0...v1.45.0) (2026-07-07)


### Features

* **docker_lxc_features:** add AI docker LXC host features ([#366](https://github.com/dryvist/ansible-proxmox/issues/366)) ([f03dfac](https://github.com/dryvist/ansible-proxmox/commit/f03dfac9e5c20d81b307a5a6c655f79a0424f2d6))

## [1.44.0](https://github.com/dryvist/ansible-proxmox/compare/v1.43.1...v1.44.0) (2026-07-07)


### Features

* **lxc_features:** add n8n + langgraph feature entries ([#364](https://github.com/dryvist/ansible-proxmox/issues/364)) ([4961c60](https://github.com/dryvist/ansible-proxmox/commit/4961c60d4db2ef3a86f676b223017734cb1890aa))

## [1.43.1](https://github.com/dryvist/ansible-proxmox/compare/v1.43.0...v1.43.1) (2026-07-06)


### Bug Fixes

* **pve_ha:** derive HA config host from cluster primary, not literal pve ([#361](https://github.com/dryvist/ansible-proxmox/issues/361)) ([a016b10](https://github.com/dryvist/ansible-proxmox/commit/a016b10d5405bbe925343e6f8690e8a5c8b1fcd0))

## [1.43.0](https://github.com/dryvist/ansible-proxmox/compare/v1.42.0...v1.43.0) (2026-07-06)


### Features

* **pve_cluster:** guard against stale corosync vote overrides (DR/HA W4) ([#359](https://github.com/dryvist/ansible-proxmox/issues/359)) ([2b55113](https://github.com/dryvist/ansible-proxmox/commit/2b551135fe8c8f0a880426cf77746802be5f5c7e))
* **pve_ha:** autonomous HA role for tier-0 guests (DR/HA W5) ([#358](https://github.com/dryvist/ansible-proxmox/issues/358)) ([842ff92](https://github.com/dryvist/ansible-proxmox/commit/842ff92af5f6dc7c7bb11f1d7f43e2014905632c))

## [1.42.0](https://github.com/dryvist/ansible-proxmox/compare/v1.41.1...v1.42.0) (2026-07-06)


### Features

* **inventory:** commission pve4 in the homelab cluster ([#356](https://github.com/dryvist/ansible-proxmox/issues/356)) ([a9e6213](https://github.com/dryvist/ansible-proxmox/commit/a9e6213f1a8fc76c874b452787b5e56cabcb6992))

## [1.41.1](https://github.com/dryvist/ansible-proxmox/compare/v1.41.0...v1.41.1) (2026-07-06)


### Bug Fixes

* **pve3:** keep pve3 powered on 24/7, disable auto-poweroff ([#354](https://github.com/dryvist/ansible-proxmox/issues/354)) ([b83d803](https://github.com/dryvist/ansible-proxmox/commit/b83d8033b18a5d23f512798a87207759e94dbe0a))

## [1.41.0](https://github.com/dryvist/ansible-proxmox/compare/v1.40.0...v1.41.0) (2026-07-05)


### Features

* **media:** add sortarr to media_lxc_features persistence map ([#351](https://github.com/dryvist/ansible-proxmox/issues/351)) ([a3a3844](https://github.com/dryvist/ansible-proxmox/commit/a3a3844d871a2e029bce6056c448e6874d8574e6))

## [1.40.0](https://github.com/dryvist/ansible-proxmox/compare/v1.39.4...v1.40.0) (2026-07-05)


### Features

* **kernel_tuning:** opt-in C6 idle-state disable via MSR at boot ([#349](https://github.com/dryvist/ansible-proxmox/issues/349)) ([d3c5bd9](https://github.com/dryvist/ansible-proxmox/commit/d3c5bd93f9cab3fbe630d755ac93f4835f0a8aa7))

## [1.39.4](https://github.com/dryvist/ansible-proxmox/compare/v1.39.3...v1.39.4) (2026-07-05)


### Bug Fixes

* **media:** resolve appdata owner by the actual in-container user ([#347](https://github.com/dryvist/ansible-proxmox/issues/347)) ([6d7c261](https://github.com/dryvist/ansible-proxmox/commit/6d7c261c98ef2c4fdca844dc40aa52476986d27e))

## [1.39.3](https://github.com/dryvist/ansible-proxmox/compare/v1.39.2...v1.39.3) (2026-07-04)


### Bug Fixes

* normalize issue-auto-resolve to the proven template and enable the loop ([#344](https://github.com/dryvist/ansible-proxmox/issues/344)) ([308069e](https://github.com/dryvist/ansible-proxmox/commit/308069e7aa848ef3163f071ee9b7bf4cf3ea3155))

## [1.39.2](https://github.com/dryvist/ansible-proxmox/compare/v1.39.1...v1.39.2) (2026-07-04)


### Bug Fixes

* **media:** prune stale mounts and drop retired appdata ([#342](https://github.com/dryvist/ansible-proxmox/issues/342)) ([e23ce2b](https://github.com/dryvist/ansible-proxmox/commit/e23ce2b7011f387fc08f67b7a32262b5035bfc60))

## [1.39.1](https://github.com/dryvist/ansible-proxmox/compare/v1.39.0...v1.39.1) (2026-07-04)


### Bug Fixes

* **lxc_features:** per-node vmid filter + LLM fabric docker guests ([#340](https://github.com/dryvist/ansible-proxmox/issues/340)) ([417c113](https://github.com/dryvist/ansible-proxmox/commit/417c11319febd2a2fadb87bb3773f9fe840d8ad4))

## [1.39.0](https://github.com/dryvist/ansible-proxmox/compare/v1.38.0...v1.39.0) (2026-07-03)


### Features

* **lxc_gpu_features:** rename GPU LXC service to llm-fast ([#333](https://github.com/dryvist/ansible-proxmox/issues/333)) ([ec289e5](https://github.com/dryvist/ansible-proxmox/commit/ec289e565db682e18f625bb23377bfcbb3504085))

## [1.38.0](https://github.com/dryvist/ansible-proxmox/compare/v1.37.0...v1.38.0) (2026-07-03)


### Features

* add issue-backlog-sweep caller ([#337](https://github.com/dryvist/ansible-proxmox/issues/337)) ([6a06b95](https://github.com/dryvist/ansible-proxmox/commit/6a06b95316b0f274ae1adce5e0516a282f66da23))

## [1.37.0](https://github.com/dryvist/ansible-proxmox/compare/v1.36.0...v1.37.0) (2026-07-03)


### Features

* add cluster node pve4 to Proxmox inventory ([#332](https://github.com/dryvist/ansible-proxmox/issues/332)) ([1b2f06b](https://github.com/dryvist/ansible-proxmox/commit/1b2f06b14d063130012466764a84bfc24cfe8bd7))

## [1.36.0](https://github.com/dryvist/ansible-proxmox/compare/v1.35.0...v1.36.0) (2026-07-03)


### Features

* add review-thread-resolver caller for instant bot-thread resolution ([#330](https://github.com/dryvist/ansible-proxmox/issues/330)) ([6ab0e1a](https://github.com/dryvist/ansible-proxmox/commit/6ab0e1ab80c4821ff20913957c1a23dc12196547))

## [1.35.0](https://github.com/dryvist/ansible-proxmox/compare/v1.34.3...v1.35.0) (2026-07-03)


### Features

* add AI PR care caller (dep review + release highlights) ([#328](https://github.com/dryvist/ansible-proxmox/issues/328)) ([1fbc71f](https://github.com/dryvist/ansible-proxmox/commit/1fbc71fb10e769b2f2a2aad6ed8c407603cf5877))

## [1.34.3](https://github.com/dryvist/ansible-proxmox/compare/v1.34.2...v1.34.3) (2026-07-02)


### Bug Fixes

* **ci:** restore CI Fix auto-trigger as a thin cc-ci-fix wrapper ([7f1d399](https://github.com/dryvist/ansible-proxmox/commit/7f1d3996fab49e99e7b534bf5d14ac7b42b973fc))

## [1.34.2](https://github.com/dryvist/ansible-proxmox/compare/v1.34.1...v1.34.2) (2026-07-02)


### Bug Fixes

* point callers at renamed cc- reusable workflows ([d3daa9f](https://github.com/dryvist/ansible-proxmox/commit/d3daa9f30a71390e2287c72f98940e07c1e4b87e))

## [1.34.1](https://github.com/dryvist/ansible-proxmox/compare/v1.34.0...v1.34.1) (2026-07-01)


### Bug Fixes

* **media_lxc_features:** seed config datasets before mounting; never mount a missing source ([#317](https://github.com/dryvist/ansible-proxmox/issues/317)) ([adc4f93](https://github.com/dryvist/ansible-proxmox/commit/adc4f93c7afd83aa04aa671f545397a9e0c7bb39))

## [1.34.0](https://github.com/dryvist/ansible-proxmox/compare/v1.33.1...v1.34.0) (2026-07-01)


### Features

* **ntp:** prefer the network gateway as primary source; fix Debian 13 validate ([#318](https://github.com/dryvist/ansible-proxmox/issues/318)) ([21693b7](https://github.com/dryvist/ansible-proxmox/commit/21693b7293b014cd7fa8ee0456f729db0fbec0da))

## [1.33.1](https://github.com/dryvist/ansible-proxmox/compare/v1.33.0...v1.33.1) (2026-06-29)


### Bug Fixes

* **syncoid:** move OnSuccess/OnFailure to [Unit] so the DR node auto-sleeps ([#314](https://github.com/dryvist/ansible-proxmox/issues/314)) ([cdc710c](https://github.com/dryvist/ansible-proxmox/commit/cdc710c8f855a3cfb2e879f2a6850155b767b77f))

## [1.33.0](https://github.com/dryvist/ansible-proxmox/compare/v1.32.0...v1.33.0) (2026-06-28)


### Features

* **backup:** autonomous DR-node wake → replicate → sleep cycle ([#301](https://github.com/dryvist/ansible-proxmox/issues/301)) ([ea5d16f](https://github.com/dryvist/ansible-proxmox/commit/ea5d16fe1c5931cbf430e6a62ccd82fd5251809a))

## [1.32.0](https://github.com/dryvist/ansible-proxmox/compare/v1.31.0...v1.32.0) (2026-06-27)


### Features

* **media_lxc_features:** persist *arr/qBittorrent/Prowlarr/Seerr config on bulk/appdata ([#307](https://github.com/dryvist/ansible-proxmox/issues/307)) ([b6359d3](https://github.com/dryvist/ansible-proxmox/commit/b6359d3795f73ae5c567e256807c56a9ac378ef2))

## [1.31.0](https://github.com/dryvist/ansible-proxmox/compare/v1.30.0...v1.31.0) (2026-06-21)


### Features

* **ci:** re-run molecule on upstream release ([#297](https://github.com/dryvist/ansible-proxmox/issues/297)) ([5a38fbe](https://github.com/dryvist/ansible-proxmox/commit/5a38fbe0c7ba2559ac6d72d2b2b167000879ac2d))

## [1.30.0](https://github.com/dryvist/ansible-proxmox/compare/v1.29.1...v1.30.0) (2026-06-21)


### Features

* **backup:** protect object-storage data volume via sanoid+syncoid ([#296](https://github.com/dryvist/ansible-proxmox/issues/296)) ([ec23db7](https://github.com/dryvist/ansible-proxmox/commit/ec23db7568b6ba571eb4cb1cc7f17a5897f90b94))

## [1.29.1](https://github.com/dryvist/ansible-proxmox/compare/v1.29.0...v1.29.1) (2026-06-18)


### Bug Fixes

* **media:** update plex molecule assertion for the appdata mount ([#293](https://github.com/dryvist/ansible-proxmox/issues/293)) ([27c79c5](https://github.com/dryvist/ansible-proxmox/commit/27c79c5ce0acf1685b111414bd1d0a9862afce38))

## [1.29.0](https://github.com/dryvist/ansible-proxmox/compare/v1.28.1...v1.29.0) (2026-06-18)


### Features

* **media_lxc_features:** persist Plex config on bulk/appdata to survive rebuilds ([#286](https://github.com/dryvist/ansible-proxmox/issues/286)) ([c058ac3](https://github.com/dryvist/ansible-proxmox/commit/c058ac3704812f1caab4d82c0ba2d74c774800ad))

## [1.28.1](https://github.com/dryvist/ansible-proxmox/compare/v1.28.0...v1.28.1) (2026-06-18)


### Bug Fixes

* **syncoid:** set PATH so cron finds syncoid in /usr/sbin ([#289](https://github.com/dryvist/ansible-proxmox/issues/289)) ([3d02442](https://github.com/dryvist/ansible-proxmox/commit/3d0244219cccef8ac0f1738985536e896be0fb83))

## [1.28.0](https://github.com/dryvist/ansible-proxmox/compare/v1.27.2...v1.28.0) (2026-06-13)


### Features

* **zfs_replication:** opt-in syncoid-based standby replication to an intermittent node ([#280](https://github.com/dryvist/ansible-proxmox/issues/280)) ([0c067df](https://github.com/dryvist/ansible-proxmox/commit/0c067df2dd2304ce4f9b31ac28b20dbd1bf07f18))

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
