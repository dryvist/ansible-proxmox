"""Pin check-mode guards, per-ESP resolution and legacy cleanup of the memtest install."""

from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
MAIN_TASKS = yaml.safe_load((ROOT / "roles/crash_diagnostics/tasks/main.yml").read_text())
MEMTEST_TASKS = yaml.safe_load((ROOT / "roles/crash_diagnostics/tasks/memtest.yml").read_text())
ESP_TASKS = yaml.safe_load((ROOT / "roles/crash_diagnostics/tasks/memtest_esp.yml").read_text())
WRITE_TASKS = (
    "Copy memtest86+ to boot partition",
    "Deploy custom GRUB config with memtest entry to boot partition",
)
LEGACY_MOUNT_PATH = "/tmp/ansible-boot-partition"


def walk(task_list):
    """Yield tasks in order, descending into block, rescue and always."""
    for task in task_list or []:
        if "block" in task:
            yield from walk(task["block"])
            yield from walk(task.get("rescue"))
            yield from walk(task.get("always"))
        else:
            yield task


TASKS = {
    task.get("name"):
    task
    for task in list(walk(MAIN_TASKS)) + list(walk(MEMTEST_TASKS)) + list(walk(ESP_TASKS))
}


class MemtestCheckMode(unittest.TestCase):
    def test_boot_partition_writes_skip_check_mode(self):
        all_tasks = list(walk(MAIN_TASKS)) + list(walk(MEMTEST_TASKS)) + list(walk(ESP_TASKS))
        guarded_tasks = [
            task["name"]
            for task in all_tasks
            if task.get("name") in WRITE_TASKS
            and "not ansible_check_mode" in task.get("when", [])
        ]

        self.assertEqual(guarded_tasks, list(WRITE_TASKS))


class MemtestEspResolution(unittest.TestCase):
    def test_memtest_tasks_are_included_with_their_tags(self):
        includes = [
            task
            for task in walk(MAIN_TASKS)
            if task.get("ansible.builtin.include_tasks") == "memtest.yml"
        ]

        self.assertEqual(len(includes), 1)
        self.assertEqual(includes[0]["tags"], ["crash_diagnostics", "memtest"])

    def test_unresolvable_uuid_does_not_fail_the_play(self):
        resolve = TASKS["Resolve boot partition UUIDs to block devices"]
        self.assertIs(resolve["failed_when"], False)
        self.assertIs(resolve["changed_when"], False)
        self.assertIs(resolve["check_mode"], False)

    def test_unresolvable_uuid_is_reported_for_proxmox_boot_tool_clean(self):
        report = TASKS["Report boot partition UUIDs that no longer resolve"]
        self.assertEqual(report["when"], "item.rc != 0")
        self.assertIn("proxmox-boot-tool clean", report["ansible.builtin.debug"]["msg"])

    def test_stale_first_uuid_leaves_the_good_one_handled(self):
        install = TASKS["Install memtest86+ on every resolvable boot ESP"]
        self.assertIn("selectattr('rc', 'equalto', 0)", install["loop"])
        self.assertEqual(
            install["loop_control"]["loop_var"], "crash_diagnostics_esp_result"
        )

    def test_every_resolved_esp_is_handled_not_just_the_first(self):
        dumped = yaml.safe_dump(MEMTEST_TASKS)
        self.assertNotIn("select | first", dumped)
        install = TASKS["Install memtest86+ on every resolvable boot ESP"]
        self.assertIn("results", install["loop"])


class MemtestEspMount(unittest.TestCase):
    def test_mount_is_ephemeral_with_per_esp_path(self):
        mount = TASKS["Mount boot ESP without writing fstab"]
        spec = mount["ansible.posix.mount"]
        self.assertEqual(spec["state"], "ephemeral")
        self.assertEqual(spec["path"], "{{ crash_diagnostics_esp_mount }}")
        install = TASKS["Install memtest86+ on every resolvable boot ESP"]
        per_esp_mount = install["vars"]["crash_diagnostics_esp_mount"]
        self.assertEqual(per_esp_mount, "/tmp/ansible-boot-esp-{{ crash_diagnostics_esp_result.item }}")
        self.assertNotEqual(per_esp_mount, LEGACY_MOUNT_PATH)

    def test_no_task_mounts_with_a_permanent_fstab_entry(self):
        for task in list(walk(MAIN_TASKS)) + list(walk(MEMTEST_TASKS)) + list(walk(ESP_TASKS)):
            spec = task.get("ansible.posix.mount", {})
            self.assertNotEqual(spec.get("state"), "mounted")

    def test_unmount_and_mount_point_removal_run_in_always(self):
        block_task = next(task for task in ESP_TASKS if "block" in task)
        always_names = [task["name"] for task in block_task["always"]]
        self.assertIn("Unmount boot ESP", always_names)
        self.assertIn("Remove temporary mount point for boot ESP", always_names)


class MemtestLegacyCleanup(unittest.TestCase):
    def test_legacy_fstab_entry_is_removed_from_fstab_only(self):
        cleanup = TASKS["Remove legacy fstab entry for the temporary boot mount"]
        spec = cleanup["ansible.posix.mount"]
        self.assertEqual(spec["state"], "absent_from_fstab")
        self.assertEqual(spec["path"], LEGACY_MOUNT_PATH)
        self.assertNotIn("when", cleanup)

    def test_legacy_mount_point_is_unmounted_and_removed_on_every_host(self):
        unmount = TASKS["Unmount leftover temporary boot mount"]
        remove = TASKS["Remove leftover temporary boot mount point"]
        self.assertEqual(unmount["ansible.posix.mount"]["state"], "unmounted")
        self.assertEqual(unmount["ansible.posix.mount"]["path"], LEGACY_MOUNT_PATH)
        self.assertEqual(remove["ansible.builtin.file"]["path"], LEGACY_MOUNT_PATH)
        self.assertEqual(remove["ansible.builtin.file"]["state"], "absent")
        self.assertNotIn("when", unmount)
        self.assertNotIn("when", remove)

    def test_uefi_hosts_skip_the_install_but_keep_the_cleanup(self):
        install = TASKS["Install memtest86+ on every resolvable boot ESP"]
        self.assertEqual(
            install["when"], "not crash_diagnostics_uefi_firmware.stat.exists"
        )
        note = TASKS["Report memtest is not handled on UEFI systemd-boot systems"]
        self.assertEqual(note["when"], "crash_diagnostics_uefi_firmware.stat.exists")
        self.assertIn("systemd-boot", note["ansible.builtin.debug"]["msg"])


if __name__ == "__main__":
    unittest.main()
