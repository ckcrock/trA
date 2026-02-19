import subprocess
import os

env = os.environ.copy()
env["RUST_BACKTRACE"] = "1"

print("Running Backtest and logging to backtrace.log...")
with open("backtrace.log", "w", encoding="utf-8") as f:
    result = subprocess.run(
        ["venv/Scripts/python.exe", "scripts/backtest_nautilus.py"],
        capture_output=True,
        text=True,
        env=env,
        cwd=os.getcwd()
    )
    f.write("--- STDOUT ---\n")
    f.write(result.stdout)
    f.write("\n--- STDERR ---\n")
    f.write(result.stderr)
    f.write(f"\n--- RETURN CODE: {result.returncode} ---\n")
