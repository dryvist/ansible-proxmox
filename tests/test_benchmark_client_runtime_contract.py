"""Contract checks for benchmark-client runtime packages."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "playbooks/tasks/benchmark-client/runtime.yml"


def test_client_installs_docker_engine_and_cli() -> None:
    tasks = yaml.safe_load(RUNTIME.read_text())
    install = next(
        task
        for task in tasks
        if task["name"] == "Install Docker and benchmark runtime prerequisites"
    )
    argv = install["ansible.builtin.command"]["argv"]

    assert "docker.io" in argv
    assert "docker-cli" in argv
