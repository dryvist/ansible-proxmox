# iDRAC Kiosk Role

Runs a minimal Wayland kiosk on the `pve` host that drives a physically
attached monitor (HDMI/DisplayPort off the AMD iGPU) and displays **both**
iDRAC6 HTML5 (noVNC) KVM consoles side-by-side, fullscreen.

The page is a local `file://` document with two iframes pointing at the iDRAC6
viewers served from LXC 251.

## Policy exception

This repository's hosts are otherwise **headless with no extra desktop
software**. This role is a deliberate, user-approved exception, scoped to the
single node `pve`:

- It adds a desktop graphics stack (`cage` + `chromium`) to one host only.
- The kiosk is **read-only** — it shows consoles; it does not control Proxmox.
- It uses the node's **existing** HDMI/DP output (zero new hardware).

Disable it with `idrac_kiosk_enabled: false` to make the role a no-op without
removing it from the play.

## Dependencies

The kiosk only shows content if the upstream viewers are live:

- **LXC 251** (`10.0.1.251`) must be serving the two iDRAC6 noVNC viewers:
  - `http://10.0.1.251:5410/` — Dell R410
  - `http://10.0.1.251:5710/` — Dell R710
- That LXC and its ports are provisioned by the companion
  `terraform-proxmox` and `ansible-proxmox-apps` iDRAC work.

If the viewers are down, the iframes simply fail to load; the kiosk itself
stays up and retries on the browser's normal schedule.

## Variables

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `idrac_kiosk_enabled` | `true` | Master switch; `false` makes the role a no-op |
| `idrac_kiosk_kvm_ip` | `10.0.1.251` | LXC serving the noVNC viewers |
| `idrac_kiosk_r410_port` | `5410` | R410 viewer port |
| `idrac_kiosk_r710_port` | `5710` | R710 viewer port |
| `idrac_kiosk_data_dir` | `/opt/idrac-kiosk` | On-host dir for the landing page |
| `idrac_kiosk_user` | `kiosk` | Unprivileged user running the session |

## Installation

The role is wired into `playbooks/site.yml` and runs against the `proxmox`
group. No extra installation step is needed beyond the standard play:

```bash
ansible-playbook playbooks/site.yml --tags idrac_kiosk
```

## Usage

Override the vars to change targets without editing the template:

```yaml
- hosts: proxmox
  roles:
    - role: idrac_kiosk
      vars:
        idrac_kiosk_kvm_ip: "10.0.1.99"
        idrac_kiosk_r410_port: 6410
        idrac_kiosk_r710_port: 6710
```

## How it works

- `seatd` provides seat access without a full login manager.
- The `kiosk` user is added to `video`, `render`, `input`, and `seat` so it can
  open the DRM device and input devices directly.
- A systemd system service (`idrac-kiosk.service`) launches
  `cage -- chromium --kiosk ... --app=file://.../index.html`.
- `cage` hosts a single fullscreen Wayland app; `chromium` renders the page.
- systemd provides a writable `XDG_RUNTIME_DIR` via `RuntimeDirectory=` (logind
  does not create one for a system service).

## Hardware caveats

Verify on the real host — these are easy to miss on a node that has only ever
run headless:

- **GPU microcode**: `firmware-amd-graphics` lives in the Debian
  `non-free-firmware` apt component. The role does **not** silently rewrite
  your apt sources; it checks availability and warns if the package cannot be
  installed. Enable `non-free-firmware` yourself, then re-run.
- **KMS / DRM device**: amdgpu must bind and create a render node. After first
  installing the firmware on a previously-headless node, a **reboot** may be
  required. Confirm the device exists:

  ```bash
  ls -l /dev/dri/card0 /dev/dri/renderD128
  ```

- **Output**: the iGPU drives both HDMI and DisplayPort; plug the monitor into
  either.

## iDRAC6 session cap

iDRAC6 vKVM allows roughly **two** concurrent virtual-console sessions per
server. A permanent kiosk **holds one session per server** for as long as it
runs. Plan accordingly: if you also open a console from a workstation you may
hit the limit and need to close the kiosk session (`systemctl stop
idrac-kiosk` on `pve`) or reset the iDRAC's stuck sessions.

## Operating

```bash
# On pve:
systemctl status idrac-kiosk      # service state
journalctl -u idrac-kiosk -b      # current-boot logs
systemctl restart idrac-kiosk     # reload after a config/page change
systemctl stop idrac-kiosk        # free the iDRAC vKVM sessions
```
