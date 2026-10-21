"""Contract checks for operator-attended iDRAC6 console user reconciliation."""

from pathlib import Path

from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar, trust_as_template
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = yaml.safe_load((ROOT / "roles/bmc_console_user/defaults/main.yml").read_text())
TASKS = yaml.safe_load((ROOT / "roles/bmc_console_user/tasks/target.yml").read_text())
PLAYBOOK = yaml.safe_load((ROOT / "playbooks/bmc-console-user.yml").read_text())


def render(expression, **variables):
    templar = Templar(loader=DataLoader(), variables=variables)
    return templar.template(trust_as_template(expression))


def evaluate(expression, **variables):
    return render("{{ " + expression + " }}", **variables)


def nested_tasks(tasks):
    for task in tasks:
        yield task
        for section in ("block", "rescue", "always"):
            yield from nested_tasks(task.get(section, []))


def test_target_defaults_enable_only_r410():
    targets = {target["name"]: target for target in DEFAULTS["bmc_console_user_targets"]}
    assert targets["r410"]["enabled"] is True
    assert targets["r710"]["enabled"] is False
    assert targets["r410"]["path"] == "apps/idrac-kvm-r410"
    assert targets["r710"]["path"] == "apps/idrac-kvm-r710"


def test_play_runs_on_controller_and_role_reads_openbao():
    assert PLAYBOOK[0]["hosts"] == "localhost"
    assert PLAYBOOK[0]["connection"] == "local"
    read = next(task for task in TASKS if task["name"].startswith("Read the console account credential"))
    assert "community.hashi_vault.vault_kv2_get" in read
    assert read["delegate_to"] == "localhost"
    assert read["no_log"] is True
    assert read["changed_when"] is False


def test_racadm_privilege_and_secret_writes_are_scoped_and_censored():
    racadm_tasks = [task for task in TASKS if "ansible.builtin.expect" in task]
    assert racadm_tasks
    assert all(task.get("delegate_to") == "localhost" for task in racadm_tasks)
    assert all(task.get("no_log") is True for task in racadm_tasks)
    assert DEFAULTS["bmc_console_user_privilege_mask"] == "0x00000021"
    assert DEFAULTS["bmc_console_user_ipmi_privilege"] == 15
    assert DEFAULTS["bmc_console_user_sol_enabled"] == 0
    password_file = next(task for task in nested_tasks(TASKS) if "ansible.builtin.copy" in task)
    assert password_file["no_log"] is True
    assert password_file["ansible.builtin.copy"]["mode"] == "0600"
    assert "cfgUserAdminPassword=" in password_file["ansible.builtin.copy"]["content"]
    assert "# cfgUserAdminIndex={{ bmc_console_user_selected_index }}" in password_file[
        "ansible.builtin.copy"
    ]["content"]
    password = next(task for task in TASKS if task["name"].startswith("Set the console account password"))
    apply = next(task for task in password["block"] if task["name"].startswith("Apply the console account password"))
    assert "config -p -f" in apply["ansible.builtin.expect"]["command"]
    assert apply["no_log"] is True
    assert apply["changed_when"] is True
    assert "bmc_console_user_reset_password" in password["when"]
    assert password["always"][0]["ansible.builtin.file"]["state"] == "absent"


def test_password_values_are_not_process_arguments():
    secret_refs = (
        "bmc_console_user_admin_password",
        "bmc_console_user_secret.secret[bmc_console_user_target.fields.password]",
    )
    for task in nested_tasks(TASKS):
        for action in ("ansible.builtin.expect", "ansible.builtin.command", "ansible.builtin.shell"):
            if action in task:
                command = str(task[action].get("command", task[action].get("argv", task[action].get("cmd", ""))))
                assert not any(secret_ref in command for secret_ref in secret_refs)


def test_access_settings_run_only_when_the_read_slot_differs():
    configure = next(task for task in TASKS if task["name"].startswith("Configure console account access"))
    settings = configure["loop"]
    assert {item["attribute"] for item in settings} == {
        "cfgUserAdminPrivilege",
        "cfgUserAdminIpmiLanPrivilege",
        "cfgUserAdminIpmiSerialPrivilege",
        "cfgUserAdminSolEnable",
        "cfgUserAdminEnable",
    }
    expression = configure["when"]
    settings = [
        {"attribute": "cfgUserAdminPrivilege", "value": "0x00000021", "base": 16},
        {"attribute": "cfgUserAdminIpmiLanPrivilege", "value": "15", "base": 10},
        {"attribute": "cfgUserAdminIpmiSerialPrivilege", "value": "15", "base": 10},
        {"attribute": "cfgUserAdminSolEnable", "value": "0", "base": 10},
        {"attribute": "cfgUserAdminEnable", "value": "1", "base": 10},
    ]
    current_config = "\n".join(
        f"{setting['attribute']}={setting['value']}" for setting in settings
    )
    for setting in settings:
        variables = {
            "bmc_console_user_existing": True,
            "bmc_console_user_current_config": current_config,
            "item": setting,
        }
        assert evaluate(expression, **variables) is False
        assert evaluate(
            expression,
            **{
                **variables,
                "bmc_console_user_current_config": current_config.replace(
                    f"{setting['attribute']}={setting['value']}",
                    f"{setting['attribute']}=99",
                ),
            },
        ) is True
        assert evaluate(
            expression,
            **{**variables, "bmc_console_user_existing": False},
        ) is True


def test_account_inventory_checks_all_slots_before_selecting_an_empty_one():
    reads = next(task for task in TASKS if task["name"].startswith("Read all iDRAC6 user slots"))
    assert reads["loop"] == "{{ range(1, 17) | list }}"
    assert reads["changed_when"] is False
    assert reads["check_mode"] is False
    assert reads["no_log"] is True
    find = next(task for task in TASKS if task["name"].startswith("Find the existing account"))
    state = render(
        find["ansible.builtin.set_fact"]["bmc_console_user_slot_state"],
        bmc_console_user_name="console-user",
        bmc_console_user_slot_reads={
            "results": [
                {"item": 2, "stdout": "# cfgUserAdminIndex=2\ncfgUserAdminUserName=someone\n"},
                {"item": 16, "stdout": "# cfgUserAdminIndex=16\ncfgUserAdminUserName=console-user\n"},
                {"item": 15, "stdout": "# cfgUserAdminIndex=15\ncfgUserAdminUserName=\n"},
            ]
        },
    )
    assert state["matches"] == [
        {"index": 16, "stdout": "# cfgUserAdminIndex=16\ncfgUserAdminUserName=console-user\n"}
    ]
    assert state["free"] == [15]

    select = next(task for task in TASKS if task["name"].startswith("Select the existing or preferred"))
    expression = select["ansible.builtin.set_fact"]["bmc_console_user_selected_index"]
    chosen = render(
        expression,
        bmc_console_user_slot_state={"matches": [], "free": [1, 3]},
        bmc_console_user_target={"user_index": 16},
    )
    assert str(chosen).strip() == "3"
