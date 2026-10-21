# bmc_console_user

Ensures a dedicated iDRAC6 account can open the virtual console using only
login and console-redirection privileges. The default target is the R410; the
R710 entry stays disabled. Credentials are read from the per-target OpenBao
KV path, whose fields are target-prefixed to avoid collisions in the apps
domain's flat merge. RACADM sets IPMI LAN and serial access to no access and
disables SOL.

This role uses Remote RACADM from the controller because the maintained Ansible
account interfaces checked do not document iDRAC6 support. RACADM prompts for
the admin credential and reads the new account password from a temporary mode-
0600 configuration file that is removed afterward. It requires `racadm` and
Python `pexpect` on the controller, a `BAO_TOKEN`, `BAO_ADDR` or `VAULT_ADDR`,
and the admin values in `IDRAC_USERNAME` / `IDRAC_PASSWORD`.

This is an operator-attended run: execute
`ansible-playbook -i inventory/hosts.yml playbooks/bmc-console-user.yml`;
RACADM runs on localhost, keeping the admin credential off the console guest.

iDRAC6 does not expose the password through RACADM, so ordinary runs leave an
existing password alone. For an attended rotation after updating OpenBao, set
`bmc_console_user_reset_password=true` for that invocation.
