"""The publisher entry point hides and writes the service-issued credential."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "playbooks/publish-fan-control-write-token.yml"


def test_publisher_hides_the_input_and_uses_the_scoped_shared_role() -> None:
    play, = yaml.safe_load(PLAYBOOK.read_text(encoding="utf-8"))

    assert play["vars_prompt"] == [
        {
            "name": "fan_control_write_token",
            "prompt": "Enter the service-generated write token",
            "private": True,
        }
    ]

    publish = play["tasks"][0]
    include = publish["ansible.builtin.include_role"]
    assert include == {
        "name": "dryvist.homelab.openbao_secrets",
        "tasks_from": "publish.yml",
    }
    assert publish["vars"]["openbao_secrets_publish_app"] == "fan-control-write"
    assert list(publish["vars"]["openbao_secrets_publish_data"]) == [
        "fan_control_write_token"
    ]
    assert publish["no_log"] is True
