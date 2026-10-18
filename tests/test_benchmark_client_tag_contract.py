"""Contract checks for benchmark-client ownership tags."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE = ROOT / "playbooks/tasks/benchmark-client/lifecycle.yml"


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
