"""Contract checks for benchmark-client runtime packages."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "playbooks/benchmark-client.yml"
RUNTIME = ROOT / "playbooks/tasks/benchmark-client/runtime.yml"


def test_client_installs_docker_engine_and_cli() -> None:
    tasks = yaml.safe_load(RUNTIME.read_text())
    install = next(
        task
        for task in tasks
        if task["name"] == "Install Docker and benchmark runtime prerequisites"
    )
    argv = install["ansible.builtin.command"]["argv"]

    assert {"bubblewrap", "docker.io", "docker-cli"} <= set(argv)


def test_client_pins_and_verifies_gbench() -> None:
    plays = yaml.safe_load(PLAYBOOK.read_text())
    validation = next(play for play in plays if play["name"] == "Validate the benchmark client request")
    tools = validation["vars"]["benchmark_client_default_tools"]
    assert tools["gbench"] == "0.5.0.post1"
    assert tools["transformers"] == "5.24.0"

    tasks = yaml.safe_load(RUNTIME.read_text())
    install = next(task for task in tasks if task["name"] == "Install the pinned gbench release when needed")
    argv = install["ansible.builtin.command"]["argv"]
    assert "gbench=={{ benchmark_client_tools.gbench }}" in argv
    assert "transformers=={{ benchmark_client_tools.transformers }}" in argv

    verify = next(task for task in tasks if task["name"] == "Verify the installed tool versions")
    assert {"command": "/usr/local/bin/gbench", "argument": "--version"} in verify["loop"]

    verify_tf = next(
        task for task in tasks if task["name"] == "Verify the installed gbench transformers version"
    )
    assert "/opt/uv-tools/gbench/bin/python" in verify_tf["ansible.builtin.command"]["argv"]
