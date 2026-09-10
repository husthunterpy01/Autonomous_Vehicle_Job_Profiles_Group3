import json

import pytest

from app.utils.cli import input_parser, read_json, run_command


def test_shared_cli_reads_bom_json_and_prints_result(tmp_path, monkeypatch, capsys):
    path = tmp_path / "handoff.json"
    path.write_text('[{"functional_area": "Perception"}]', encoding="utf-8-sig")
    monkeypatch.setattr("sys.argv", ["command", str(path)])
    run_command(input_parser("Test input"), lambda args: {"read": len(read_json(args.input))})
    assert json.loads(capsys.readouterr().out) == {"read": 1}


def test_shared_cli_rejects_bad_json_with_nonzero_exit(tmp_path, monkeypatch, capsys):
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["command", str(path)])
    with pytest.raises(SystemExit) as raised:
        run_command(input_parser("Test input"), lambda args: read_json(args.input))
    assert raised.value.code == 2
    assert "error:" in capsys.readouterr().err
