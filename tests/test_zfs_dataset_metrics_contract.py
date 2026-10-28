"""Exercise the pool fill collector's bounded ZFS dataset metric contract."""

import os
import re
import subprocess
from pathlib import Path

from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar, trust_as_template
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = yaml.safe_load(
    (ROOT / "roles/pve_textfile_collectors/defaults/main.yml").read_text()
)
TEMPLATE = ROOT / "roles/pve_textfile_collectors/templates/pool_fill.sh.j2"
DATASET_METRICS = (
    "pve_zfs_dataset_used_bytes",
    "pve_zfs_dataset_used_by_dataset_bytes",
    "pve_zfs_dataset_used_by_snapshots_bytes",
    "pve_zfs_dataset_used_by_refreservation_bytes",
    "pve_zfs_dataset_available_bytes",
)


def render_pool_fill(output_dir):
    variables = {
        **DEFAULTS,
        "pve_textfile_collectors_textfile_dir": str(output_dir),
    }
    templar = Templar(loader=DataLoader(), variables=variables)
    return templar.template(trust_as_template(TEMPLATE.read_text()))


def write_executable(path, content):
    path.write_text(content)
    path.chmod(0o755)


def test_pool_fill_exports_bounded_dataset_properties_and_threshold(tmp_path):
    output_dir = tmp_path / "output"
    bin_dir = tmp_path / "bin"
    output_dir.mkdir()
    bin_dir.mkdir()

    guest_dataset = (
        f"bulk/replica/vm-{len('pool') * len('node')}-disk-{len('disk') - len('disk')}"
    )
    datasets = (
        "rpool\t1000\t700\t100\t200\t500",
        "rpool/ROOT\t800\t600\t100\t100\t600",
        "rpool/ROOT/system\t700\t500\t100\t100\t700",
        "bulk\t10000\t9000\t500\t500\t1000",
        "bulk/backups\t5000\t4500\t250\t250\t500",
        "bulk/appdata/nested\t4000\t3500\t250\t250\t600",
        f"{guest_dataset}\t3000\t2800\t100\t100\t700",
    )

    write_executable(
        bin_dir / "timeout",
        "#!/usr/bin/env bash\nshift\nexec \"$@\"\n",
    )
    write_executable(
        bin_dir / "zpool",
        "#!/usr/bin/env bash\n"
        "[[ \"$*\" == 'list -Hp -o name,size,alloc,free,frag,cap' ]] || exit 2\n"
        "printf '%s\\n' 'rpool 10000 5000 5000 20% 50%'\n",
    )
    write_executable(
        bin_dir / "zfs",
        "#!/usr/bin/env bash\n"
        "[[ \"$*\" == 'list -H -p -t filesystem,volume "
        "-o name,used,usedbydataset,usedbysnapshots,usedbyrefreservation,available' ]] "
        "|| exit 2\n"
        "printf '%b\\n' "
        + " ".join(f"'{dataset}'" for dataset in datasets)
        + "\n",
    )

    script = tmp_path / "pool_fill"
    script.write_text(render_pool_fill(output_dir))
    script.chmod(0o755)
    result = subprocess.run(
        [str(script)],
        capture_output=True,
        check=False,
        env={
            **os.environ,
            "OUTPUT_DIR": str(output_dir),
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
        },
        text=True,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    metrics = (output_dir / "pool_fill.prom").read_text()
    assert 'pve_textfile_success{script="pool_fill"} 1' in metrics
    assert 'pve_zpool_cap_percent{pool="rpool"} 50' in metrics
    assert (
        'pve_zfs_dataset_growth_threshold_bytes{pool="rpool"} 10737418240'
        in metrics
    )

    expected_datasets = {
        "rpool": ("rpool", ("1000", "700", "100", "200", "500")),
        "rpool/ROOT": ("rpool", ("800", "600", "100", "100", "600")),
        "rpool/ROOT/system": ("rpool", ("700", "500", "100", "100", "700")),
        "bulk": ("bulk", ("10000", "9000", "500", "500", "1000")),
        "bulk/backups": ("bulk", ("5000", "4500", "250", "250", "500")),
        guest_dataset: ("bulk", ("3000", "2800", "100", "100", "700")),
    }
    for dataset, (pool, values) in expected_datasets.items():
        for metric, value in zip(DATASET_METRICS, values, strict=True):
            assert f'{metric}{{pool="{pool}",dataset="{dataset}"}} {value}' in metrics
    assert 'dataset="bulk/appdata/nested"' not in metrics


def test_dataset_selection_is_bounded_and_alert_threshold_is_configured():
    regex = re.compile(
        "|".join(DEFAULTS["pve_textfile_collectors_zfs_dataset_include_regexes"])
    )
    guest_dataset = f"bulk/replica/vm-{len('pool') * len('node')}-disk-0"

    assert DEFAULTS["pve_textfile_collectors_zfs_growth_threshold_gib"] == 10
    assert regex.fullmatch("rpool/ROOT/system")
    assert regex.fullmatch("bulk")
    assert regex.fullmatch("bulk/backups")
    assert regex.fullmatch(guest_dataset)
    assert not regex.fullmatch("bulk/appdata/nested")
