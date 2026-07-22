# Container start

Starts explicitly approved LXC guests through the Proxmox API. This role cannot
stop, restart, create, delete, or enroll a guest in HA.

The allowlist is keyed by the service name in the published `tofu-proxmox`
inventory. Node and VMID are resolved from that inventory and checked against
the live API before the start operation. The default allowlist is empty, so an
unscoped run performs no Proxmox API calls.

```bash
doppler run -- ansible-playbook -i inventory/hosts.yml \
  playbooks/container-start.yml \
  -e '{"container_start_services":["service-name"]}'
```

Authentication uses `PROXMOX_VE_HOSTNAME` and the existing
`PROXMOX_VE_API_TOKEN` Doppler/OpenBao value. The token must use Proxmox's
`user@realm!token-id=secret` format; the role validates and splits it without
logging the token or secret. TLS certificate validation follows the same
`PROXMOX_VE_INSECURE` policy as the `pve_cluster` role.
