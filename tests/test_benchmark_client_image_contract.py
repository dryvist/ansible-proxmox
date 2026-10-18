"""Contract checks for benchmark-client image prefetching."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "playbooks/benchmark-client.yml"
IMAGES = ROOT / "playbooks/tasks/benchmark-client/images.yml"


def test_client_pins_the_x86_64_vllm_image_by_default() -> None:
    playbook = yaml.safe_load(PLAYBOOK.read_text())
    assert playbook[0]["ansible.builtin.import_playbook"] == "load_tofu.yml"
    validation = next(play for play in playbook if play["name"] == "Validate the benchmark client request")
    tools = validation["vars"]["benchmark_client_default_tools"]
    assert tools["vllm_client_image"] == "vllm/vllm-openai-cpu:v0.32.0-x86_64"
    assert "# renovate: datasource=docker depName=vllm/vllm-openai-cpu" in PLAYBOOK.read_text()


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


def test_engine_verification_can_be_skipped_for_an_offline_client() -> None:
    tasks = yaml.safe_load(IMAGES.read_text())
    engine_check = tasks[
        [task["name"] for task in tasks].index("Verify the engine API responds from the client")
    ]

    assert "verify_engine | default(true) | bool" in engine_check["when"]
