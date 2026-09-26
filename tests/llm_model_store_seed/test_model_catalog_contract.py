import re
from pathlib import Path

ROLE = Path(__file__).resolve().parents[2] / "roles" / "llm_model_store_seed"

# Every {hf_repo, gguf} pair declared anywhere in dryvist/ansible-proxmox-ai's
# `llama_cpp_models` as of the session that wrote this test: the role default
# in roles/llama_cpp/defaults/main/00-core.yml (qwen3-4b, nomic-embed-text-v1.5)
# plus the per-group overrides in inventory/group_vars/llm_cpu_9b_group.yml,
# llm_cpu_moe_group.yml and llm_vllm_group.yml. This is a snapshot, not a live
# cross-repo fetch — this repo's other tests (e.g. test_contract.py) are
# offline and dependency-free by convention, and a network call here would be
# the only one in the suite. Update this list in the same change that updates
# ansible-proxmox-ai's llama_cpp_models, or this test goes stale in the wrong
# direction (passing while the real upstream list has moved).
KNOWN_UPSTREAM_LLAMA_CPP_MODELS = {
    ("bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF", "Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf"),
    ("nomic-ai/nomic-embed-text-v1.5-GGUF", "nomic-embed-text-v1.5.Q4_K_M.gguf"),
    ("unsloth/Qwen3.5-9B-GGUF", "Qwen3.5-9B-Q4_K_M.gguf"),
    ("bartowski/Qwen_Qwen3.6-35B-A3B-GGUF", "Qwen_Qwen3.6-35B-A3B-Q4_K_M.gguf"),
    ("unsloth/Qwen3.8-27B-GGUF", "Qwen3.8-27B-UD-IQ3_XXS.gguf"),
}


def _defaults_text():
    return (ROLE / "defaults" / "main.yml").read_text()


def test_every_known_upstream_model_is_covered():
    defaults = _defaults_text()
    for hf_repo, gguf in KNOWN_UPSTREAM_LLAMA_CPP_MODELS:
        pattern = re.compile(
            rf"hf_repo:\s*{re.escape(hf_repo)}\s*\n\s*gguf:\s*{re.escape(gguf)}\s*\n"
        )
        assert pattern.search(defaults), (
            f"{hf_repo}/{gguf} is declared in ansible-proxmox-ai's "
            "llama_cpp_models but missing from llm_model_store_seed_models "
            "(defaults/main.yml) -- the seed would never fetch it."
        )


def test_every_model_pins_a_renovate_tracked_hf_revision():
    defaults = _defaults_text()
    # Every hf_revision: line is immediately preceded (ignoring blank/comment
    # lines other than its own annotation) by a matching `# renovate-digest:
    # datasource=git-refs depName=<x> packageName=https://huggingface.co/<x's
    # own hf_repo>` annotation -- the ONE Renovate-trackable var per model.
    # A dedicated prefix, not this estate's shared `# renovate:` one: the
    # shared annotation manager (dryvist/.github) has no packageName group
    # and would otherwise also match this line.
    entries = re.findall(
        r"hf_repo:\s*(?P<hf_repo>\S+)\s*\n\s*gguf:\s*(?P<gguf>\S+)\s*\n"
        r"\s*# renovate-digest: datasource=git-refs depName=(?P<depName>\S+) packageName=(?P<packageName>\S+)\s*\n"
        r"\s*hf_revision:\s*(?P<hf_revision>[0-9a-f]{7,40})\s*\n",
        defaults,
    )
    assert len(entries) == len(KNOWN_UPSTREAM_LLAMA_CPP_MODELS), (
        "Every model entry must have hf_repo, gguf, a git-refs renovate "
        "annotation and hf_revision in that exact order, immediately "
        "adjacent -- found a mismatch."
    )
    for hf_repo, _gguf, _dep_name, package_name, hf_revision in entries:
        assert package_name == f"https://huggingface.co/{hf_repo}", (
            f"{hf_repo}'s renovate packageName ({package_name}) does not "
            "point at its own HuggingFace repo -- Renovate would track the "
            "wrong upstream's commits."
        )
        assert re.fullmatch(r"[0-9a-f]{7,40}", hf_revision), (
            f"{hf_repo}'s hf_revision ({hf_revision}) is not a bare hex "
            "commit sha -- get_url's checksum resolution assumes one."
        )


def test_no_literal_sha256_checksum_in_the_role():
    # The sha256 is read from HuggingFace's own LFS blob metadata at run
    # time (tasks/seed_model.yml); a literal sha256 anywhere in the role
    # would be the second, driftable source this design exists to avoid.
    for path in (ROLE / "defaults" / "main.yml", *(ROLE / "tasks").glob("*.yml")):
        text = path.read_text()
        assert not re.search(r"\bsha256:\s*[0-9a-f]{64}\b", text), (
            f"{path} hardcodes a sha256 checksum -- it must be resolved "
            "live from HuggingFace's blob metadata instead."
        )
