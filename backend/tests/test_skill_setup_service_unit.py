from __future__ import annotations

import pytest

from app.services.skills.import_models import SkillPreflightRecord
from app.services.skills.import_store import SkillImportStore
from app.services.skills.setup_service import SkillSetupService


def _record(skill_ref: str, source_path: str) -> SkillPreflightRecord:
    return SkillPreflightRecord(
        skill_name=skill_ref.split(":")[0],
        skill_version="1.0.0",
        skill_ref=skill_ref,
        source_path=source_path,
        source_layer="workspace",
        status="available",
        setup_capable=True,
        setup_required=True,
        setup_runtime="python",
        setup_supported_runtimes=["python"],
        last_setup_commands=["python -m venv .yue/python/venv"],
        package_fingerprint="sha256:test",
        isolated_env_path=f"{source_path}/.yue/python/venv",
    )


def test_parse_install_setup_phase1_validation():
    invalid = SkillSetupService.parse_install_setup({"setup": {"runtime": "shell", "commands": []}})
    assert invalid.valid is False
    assert invalid.errors

    valid = SkillSetupService.parse_install_setup(
        {"setup": {"runtime": "python", "commands": ["python -m venv .yue/python/venv"]}}
    )
    assert valid.valid is True
    assert valid.setup is not None
    assert valid.setup.runtime == "python"


def test_setup_requires_trust_and_updates_state(tmp_path):
    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    service = SkillSetupService(import_store=store, command_runner=lambda **_: type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})())

    try:
        service.run_setup("demo:1.0.0")
        assert False, "expected trust guard"
    except PermissionError:
        pass

    trusted = service.trust_skill("demo:1.0.0")
    assert trusted.trust_status == "trusted"
    assert trusted.setup_status == "available"

    done = service.run_setup("demo:1.0.0")
    assert done.setup_status == "succeeded"
    assert done.setup_last_error is None
    assert done.last_setup_started_at is not None
    assert done.last_setup_finished_at is not None


@pytest.mark.parametrize(
    "command",
    [
        "python -V\npython -V",
        "python -c \"print('hi')\"",
        "node -e \"console.log('hi')\"",
        "python -m venv ../escape",
    ],
)
def test_setup_rejects_shell_chaining_inline_code_and_path_escape(tmp_path, command):
    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.trust_status = "trusted"
    record.last_setup_commands = [command]
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    calls: list[dict] = []

    def _runner(**kwargs):
        calls.append(kwargs)
        return type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    service = SkillSetupService(import_store=store, command_runner=_runner)

    result = service.run_setup("demo:1.0.0")

    assert result.setup_status == "failed"
    assert "Phase 1 policy" in (result.setup_last_error or "")
    assert calls == []


@pytest.mark.parametrize(
    "command",
    [
        ".yue/python/venv/bin/pip install --user -r requirements.txt",
        "npm install -g pnpm",
    ],
)
def test_setup_rejects_global_install_flags(tmp_path, command):
    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.trust_status = "trusted"
    record.setup_runtime = "python" if "pip" in command else "node"
    record.setup_supported_runtimes = [record.setup_runtime]
    record.last_setup_commands = [command]
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    calls: list[dict] = []
    service = SkillSetupService(
        import_store=store,
        command_runner=lambda **kwargs: calls.append(kwargs) or type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})(),
    )

    result = service.run_setup("demo:1.0.0")

    assert result.setup_status == "failed"
    assert calls == []


def test_package_fingerprint_changes_when_setup_inputs_change(tmp_path):
    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    (source / "manifest.yaml").write_text("name: demo\n", encoding="utf-8")
    (source / "requirements.txt").write_text("requests==1.0.0\n", encoding="utf-8")

    before = SkillSetupService.compute_package_fingerprint(str(source))

    (source / "requirements.txt").write_text("requests==2.0.0\n", encoding="utf-8")
    after = SkillSetupService.compute_package_fingerprint(str(source))

    assert before != after


def test_setup_requires_retrust_when_package_changes_after_trust(tmp_path):
    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    (source / "manifest.yaml").write_text("name: demo\n", encoding="utf-8")
    (source / "requirements.txt").write_text("requests==1.0.0\n", encoding="utf-8")
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.trust_status = "trusted"
    record.last_setup_commands = [".yue/python/venv/bin/pip install -r requirements.txt"]
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    (source / "requirements.txt").write_text("requests==2.0.0\n", encoding="utf-8")

    service = SkillSetupService(
        import_store=store,
        command_runner=lambda **_: type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})(),
    )

    with pytest.raises(PermissionError):
        service.run_setup("demo:1.0.0")

    updated = store.get_preflight_record("demo:1.0.0")
    assert updated is not None
    assert updated.trust_status == "untrusted"


def test_trust_requires_rescan_when_package_changes_after_preflight(tmp_path):
    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    (source / "manifest.yaml").write_text("name: demo\n", encoding="utf-8")
    (source / "requirements.txt").write_text("requests==1.0.0\n", encoding="utf-8")
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    (source / "requirements.txt").write_text("requests==2.0.0\n", encoding="utf-8")

    service = SkillSetupService(import_store=store)

    with pytest.raises(RuntimeError):
        service.trust_skill("demo:1.0.0")

    updated = store.get_preflight_record("demo:1.0.0")
    assert updated is not None
    assert updated.trust_status == "untrusted"


def test_node_setup_creates_isolated_directory_before_execution(tmp_path):
    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.trust_status = "trusted"
    record.setup_runtime = "node"
    record.setup_supported_runtimes = ["node"]
    record.last_setup_commands = ["npm install --prefix .yue/node"]
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    seen: list[str] = []

    def _runner(**kwargs):
        seen.append(kwargs["cwd"])
        return type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    service = SkillSetupService(import_store=store, command_runner=_runner)
    result = service.run_setup("demo:1.0.0")

    assert result.setup_status == "succeeded"
    assert seen == [str(source)]


def test_pnpm_setup_positive_path(tmp_path):
    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.trust_status = "trusted"
    record.setup_runtime = "node"
    record.setup_supported_runtimes = ["node"]
    record.last_setup_commands = ["pnpm install --dir .yue/node"]
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    seen: list[dict] = []

    def _runner(**kwargs):
        seen.append(kwargs)
        return type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    service = SkillSetupService(import_store=store, command_runner=_runner)
    result = service.run_setup("demo:1.0.0")

    assert result.setup_status == "succeeded"
    assert len(seen) == 1
    assert seen[0]["cwd"] == str(source)


def test_yarn_setup_positive_path(tmp_path):
    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.trust_status = "trusted"
    record.setup_runtime = "node"
    record.setup_supported_runtimes = ["node"]
    record.last_setup_commands = ["yarn install --cwd .yue/node"]
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    seen: list[dict] = []

    def _runner(**kwargs):
        seen.append(kwargs)
        return type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    service = SkillSetupService(import_store=store, command_runner=_runner)
    result = service.run_setup("demo:1.0.0")

    assert result.setup_status == "succeeded"
    assert len(seen) == 1
    assert seen[0]["cwd"] == str(source)


def test_uv_setup_positive_path(tmp_path):
    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    (source / "requirements.txt").write_text("", encoding="utf-8")
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.trust_status = "trusted"
    record.last_setup_commands = [
        "uv venv .yue/python/venv",
        "uv pip install --python .yue/python/venv/bin/python -r requirements.txt",
    ]
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    seen: list[dict] = []

    def _runner(**kwargs):
        seen.append(kwargs)
        return type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    service = SkillSetupService(import_store=store, command_runner=_runner)
    result = service.run_setup("demo:1.0.0")

    assert result.setup_status == "succeeded"
    assert [item["command"] for item in seen] == [
        ["uv", "venv", ".yue/python/venv"],
        ["uv", "pip", "install", "--python", ".yue/python/venv/bin/python", "-r", "requirements.txt"],
    ]
    assert [item["cwd"] for item in seen] == [str(source), str(source)]


def test_venv_python_and_pip_positive_paths(tmp_path):
    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    (source / "requirements.txt").write_text("", encoding="utf-8")
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.trust_status = "trusted"
    record.last_setup_commands = [
        "python -m venv .yue/python/venv",
        ".yue/python/venv/bin/python -m pip install -r requirements.txt",
        ".yue/python/venv/bin/pip install -r requirements.txt",
    ]
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    seen: list[dict] = []

    def _runner(**kwargs):
        seen.append(kwargs)
        return type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    service = SkillSetupService(import_store=store, command_runner=_runner)
    result = service.run_setup("demo:1.0.0")

    assert result.setup_status == "succeeded"
    assert [item["command"] for item in seen] == [
        ["python", "-m", "venv", ".yue/python/venv"],
        [".yue/python/venv/bin/python", "-m", "pip", "install", "-r", "requirements.txt"],
        [".yue/python/venv/bin/pip", "install", "-r", "requirements.txt"],
    ]
    assert [item["cwd"] for item in seen] == [str(source), str(source), str(source)]


def test_node_script_setup_positive_path(tmp_path):
    source = tmp_path / "skill"
    scripts_dir = source / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "setup-local.mjs").write_text("console.log('setup');\n", encoding="utf-8")
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.trust_status = "trusted"
    record.setup_runtime = "node"
    record.setup_supported_runtimes = ["node"]
    record.last_setup_commands = ["node scripts/setup-local.mjs"]
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    seen: list[dict] = []

    def _runner(**kwargs):
        seen.append(kwargs)
        return type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    service = SkillSetupService(import_store=store, command_runner=_runner)
    result = service.run_setup("demo:1.0.0")

    assert result.setup_status == "succeeded"
    assert len(seen) == 1
    assert seen[0]["command"] == ["node", "scripts/setup-local.mjs"]
    assert seen[0]["cwd"] == str(source)


@pytest.mark.parametrize(
    "command",
    [
        "npm install --prefix",
        "pnpm install --dir",
        "yarn install --cwd",
    ],
)
def test_node_setup_rejected_when_path_flag_has_no_value(tmp_path, command):
    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.trust_status = "trusted"
    record.setup_runtime = "node"
    record.setup_supported_runtimes = ["node"]
    record.last_setup_commands = [command]
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    calls: list[dict] = []
    service = SkillSetupService(
        import_store=store,
        command_runner=lambda **kwargs: calls.append(kwargs) or type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})(),
    )

    result = service.run_setup("demo:1.0.0")

    assert result.setup_status == "failed"
    assert "Phase 1 policy" in (result.setup_last_error or "")
    assert calls == []


@pytest.mark.parametrize(
    "command,setup_runtime",
    [
        ("npm install", "node"),
        ("npm run build", "node"),
        ("npm install -g express", "node"),
    ],
)
def test_npm_setup_rejected_without_prefix_or_without_install(tmp_path, command, setup_runtime):
    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.trust_status = "trusted"
    record.setup_runtime = setup_runtime
    record.setup_supported_runtimes = [setup_runtime]
    record.last_setup_commands = [command]
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    calls: list[dict] = []
    service = SkillSetupService(
        import_store=store,
        command_runner=lambda **kwargs: calls.append(kwargs) or type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})(),
    )

    result = service.run_setup("demo:1.0.0")
    assert result.setup_status == "failed"
    assert calls == []


def test_run_setup_audit_entries_populated_on_success(tmp_path):
    from datetime import datetime

    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.trust_status = "trusted"
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    def _runner(**kwargs):
        return type("R", (), {"returncode": 0, "stderr": "install log\n", "stdout": "ok\n"})()

    service = SkillSetupService(import_store=store, command_runner=_runner)
    result = service.run_setup("demo:1.0.0")

    assert result.setup_status == "succeeded"
    assert len(result.setup_audit_entries) == 1
    entry = result.setup_audit_entries[0]
    assert entry.command == "python -m venv .yue/python/venv"
    assert len(entry.argv) == 4
    assert entry.exit_code == 0
    assert entry.stdout_size > 0
    assert entry.stderr_size > 0
    assert entry.duration_ms >= 0
    assert isinstance(entry.started_at, datetime)
    assert isinstance(entry.finished_at, datetime)
    assert entry.finished_at >= entry.started_at


def test_run_setup_audit_entries_captures_failure_before_raise(tmp_path):
    from datetime import datetime

    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.trust_status = "trusted"
    record.last_setup_commands = [
        record.last_setup_commands[0],
        "python -m venv .yue/python/venv",
    ]
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    call_count = [0]

    def _runner(**kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return type("R", (), {"returncode": 0, "stderr": "", "stdout": "first ok\n"})()
        return type("R", (), {"returncode": 1, "stderr": "boom\n", "stdout": ""})()

    service = SkillSetupService(import_store=store, command_runner=_runner)
    result = service.run_setup("demo:1.0.0")

    assert result.setup_status == "failed"
    assert len(result.setup_audit_entries) == 2
    assert result.setup_audit_entries[0].exit_code == 0
    assert result.setup_audit_entries[0].stdout_size > 0
    assert result.setup_audit_entries[1].exit_code == 1
    assert result.setup_audit_entries[1].stderr_size > 0
    assert result.setup_audit_entries[1].duration_ms >= 0
    assert isinstance(result.setup_audit_entries[1].started_at, datetime)
    assert "boom" in (result.setup_last_error or "")


def test_run_setup_audit_entries_reset_on_rerun(tmp_path):
    from app.services.skills.import_models import SetupAuditEntry

    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.trust_status = "trusted"
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    record.setup_audit_entries = [
        SetupAuditEntry(command="stale", argv=["stale"], cwd="/tmp", exit_code=0, stdout_size=1, stderr_size=0, duration_ms=1)
    ]
    store.save_preflight_record(record)

    def _runner(**kwargs):
        return type("R", (), {"returncode": 0, "stderr": "", "stdout": "fresh\n"})()

    service = SkillSetupService(import_store=store, command_runner=_runner)
    result = service.run_setup("demo:1.0.0")

    assert result.setup_status == "succeeded"
    assert len(result.setup_audit_entries) == 1
    assert result.setup_audit_entries[0].command == "python -m venv .yue/python/venv"


@pytest.mark.parametrize(
    "command",
    [
        "pnpm install",
        "pnpm install --prefix .yue/node",
        "pnpm run build --dir .yue/node",
    ],
)
def test_pnpm_setup_rejected_without_dir_or_without_install(tmp_path, command):
    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.trust_status = "trusted"
    record.setup_runtime = "node"
    record.setup_supported_runtimes = ["node"]
    record.last_setup_commands = [command]
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    calls: list[dict] = []
    service = SkillSetupService(
        import_store=store,
        command_runner=lambda **kwargs: calls.append(kwargs) or type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})(),
    )

    result = service.run_setup("demo:1.0.0")
    assert result.setup_status == "failed"
    assert calls == []


@pytest.mark.parametrize(
    "command",
    [
        "yarn install",
        "yarn install --prefix .yue/node",
        "yarn run build --cwd .yue/node",
    ],
)
def test_yarn_setup_rejected_without_cwd_or_without_install(tmp_path, command):
    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.trust_status = "trusted"
    record.setup_runtime = "node"
    record.setup_supported_runtimes = ["node"]
    record.last_setup_commands = [command]
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    calls: list[dict] = []
    service = SkillSetupService(
        import_store=store,
        command_runner=lambda **kwargs: calls.append(kwargs) or type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})(),
    )

    result = service.run_setup("demo:1.0.0")
    assert result.setup_status == "failed"
    assert calls == []


@pytest.mark.parametrize(
    "command",
    [
        "npm install --prefix ../escape",
        "pnpm install --dir /tmp/out",
        "yarn install --cwd ../escape",
    ],
)
def test_node_setup_rejected_when_env_path_escapes_root(tmp_path, command):
    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.trust_status = "trusted"
    record.setup_runtime = "node"
    record.setup_supported_runtimes = ["node"]
    record.last_setup_commands = [command]
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    calls: list[dict] = []
    service = SkillSetupService(
        import_store=store,
        command_runner=lambda **kwargs: calls.append(kwargs) or type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})(),
    )

    result = service.run_setup("demo:1.0.0")
    assert result.setup_status == "failed"
    assert calls == []


def test_node_setup_rejected_with_non_node_executable(tmp_path):
    source = tmp_path / "skill"
    source.mkdir(parents=True, exist_ok=True)
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _record("demo:1.0.0", str(source))
    record.trust_status = "trusted"
    record.setup_runtime = "node"
    record.setup_supported_runtimes = ["node"]
    record.last_setup_commands = ["python -m venv .yue/python/venv"]
    record.package_fingerprint = SkillSetupService.compute_package_fingerprint(str(source))
    store.save_preflight_record(record)

    calls: list[dict] = []
    service = SkillSetupService(
        import_store=store,
        command_runner=lambda **kwargs: calls.append(kwargs) or type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})(),
    )

    result = service.run_setup("demo:1.0.0")
    assert result.setup_status == "failed"
    assert calls == []
