import subprocess
import os

env = os.environ.copy()
env["RUST_BACKTRACE"] = "1"

print("Running Backtest with RUST_BACKTRACE=1...")
result = subprocess.run(
    ["venv/Scripts/python.exe", "scripts/backtest_nautilus.py"],
    capture_output=True,
    env=env,
    cwd=os.getcwd()
)

stdout = result.stdout.decode("utf-8", errors="replace") if result.stdout else ""
stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""

# Save full output for inspection
with open("backtest_output.txt", "w", encoding="utf-8") as f:
    f.write("=== STDOUT ===\n")
    f.write(stdout)
    f.write("\n=== STDERR ===\n")
    f.write(stderr)
    f.write(f"\n=== EXIT CODE: {result.returncode} ===\n")

print("\n--- STDOUT (last 3000 chars) ---")
print(stdout[-3000:] if len(stdout) > 3000 else stdout)
print("\n--- STDERR (last 3000 chars) ---")
print(stderr[-3000:] if len(stderr) > 3000 else stderr)
print(f"\nExit code: {result.returncode}")
print(f"Full output saved to: backtest_output.txt")
