import subprocess
import os

env = os.environ.copy()
env["RUST_BACKTRACE"] = "1"

print("Running test_config_v4.py with backtrace...")
result = subprocess.run(
    ["venv/Scripts/python.exe", "scripts/test_config_v4.py"],
    capture_output=True,
    text=True,
    env=env,
    cwd=os.getcwd()
)

print("\n--- STDOUT ---")
print(result.stdout)
print("\n--- STDERR ---")
print(result.stderr)
