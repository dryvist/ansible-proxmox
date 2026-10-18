"""Contract checks for benchmark-client ownership tags."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE = ROOT / "playbooks/tasks/benchmark-client/lifecycle.yml"
RUNTIME = ROOT / "playbooks/tasks/benchmark-client/runtime.yml"


def test_client_tag_is_set_at_creation_and_normalized_before_validation() -> None:
    tasks = yaml.safe_load(LIFECYCLE.read_text())
    names = [task["name"] for task in tasks]

    create = tasks[names.index("Create the unprivileged benchmark client")]
    argv = create["ansible.builtin.command"]["argv"]
    assert argv[argv.index("--tags") + 1] == "benchmark-client"

    derive = tasks[names.index("Derive the provisioned client tags")]
    expression = derive["ansible.builtin.set_fact"]["benchmark_client_config_tags"]
    assert "regex_replace('^tags:\\s*', '')" in expression

    validate = tasks[names.index("Require the client configuration to match this request")]
    assert "benchmark_client_config_tags is search('(^|;)benchmark-client($|;)')" in validate[
        "ansible.builtin.assert"
    ]["that"]


def test_client_full_upgrade_runs_before_benchmark_tools_install() -> None:
    tasks = yaml.safe_load(RUNTIME.read_text())
    names = [task["name"] for task in tasks]
    upgrade = tasks[names.index("Upgrade all benchmark-client packages")]
    install = tasks[names.index("Install Docker and benchmark runtime prerequisites")]

    assert names.index(upgrade["name"]) > names.index("Update package indexes in the client")
    assert names.index(upgrade["name"]) < names.index(install["name"])
    assert "full-upgrade" in upgrade["ansible.builtin.command"]["argv"]
    assert "not ansible_check_mode" in upgrade["when"]


def test_proxmox_benchmark_upgrade_converges_driver_and_checks_kernel_mismatch() -> None:
    playbook = yaml.safe_load((ROOT / "playbooks/upgrade.yml").read_text())
    roles = [entry.get("role") for entry in playbook[-1]["roles"]]
    assert roles == ["pve_repositories", "nvidia_driver", "pve_upgrade"]

    tasks = yaml.safe_load((ROOT / "roles/pve_upgrade/tasks/main.yml").read_text())
    upgrade_block = next(
        task
        for task in tasks
        if task["name"] == "Upgrade the node, always returning it to normal HA scheduling"
    )
    reboot = next(task for task in upgrade_block["block"] if task["name"].startswith("Reboot when"))
    condition = " ".join(reboot["when"])
    assert "ansible_kernel != pve_upgrade_kernel_version" in condition
    assert "pve_upgrade_result is changed" in condition
