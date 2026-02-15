import os
import subprocess
import sys


def test_main_runs_weekly_dry_run():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cw_dir = os.path.abspath(os.path.join(base_dir, ".."))
    main_py = os.path.join(cw_dir, "Main.py")

    cmd = [sys.executable, main_py, "--run-date", "2026-02-14", "--frequency", "weekly", "--dry-run"]
    res = subprocess.run(cmd, capture_output=True, text=True)

    assert res.returncode == 0
    assert "run_log_written_to" in res.stdout
