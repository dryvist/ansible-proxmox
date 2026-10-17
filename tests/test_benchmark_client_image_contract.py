"""Contract checks for benchmark-client image prefetching."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "playbooks/benchmark-client.yml"
IMAGES = ROOT / "playbooks/tasks/benchmark-client/images.yml"


def test_client_pins_the_x86_64_vllm_image_by_default() -> None:
    playbook = yaml.safe_load(PLAYBOOK.read_text())
    tools = playbook[0]["vars"]["benchmark_client_default_tools"]
    assert tools["vllm_client_image"] == "vllm/vllm-openai-cpu:v0.31.0-x86_64"


def test_client_pulls_and_verifies_vllm_image_only_for_present_state() -> None:
    tasks = yaml.safe_load(IMAGES.read_text())
    names = [task["name"] for task in tasks]
    pull = tasks[names.index("Pull the pinned x86_64 vLLM client image when missing")]
    verify = tasks[names.index("Require the pinned x86_64 vLLM client image")]

    assert pull["ansible.builtin.command"]["argv"][-1] == "{{ benchmark_client_tools.vllm_client_image }}"
    assert "state == 'present'" in pull["when"]
    assert "not ansible_check_mode" in pull["when"]
    assert verify["ansible.builtin.assert"]["that"] == [
        "benchmark_client_vllm_image_verification.rc == 0"
    ]
