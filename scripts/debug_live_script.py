import subprocess
import os
import sys

print(f"Current Working Directory: {os.getcwd()}")
print(f"Python Executable: {sys.executable}")

try:
    # Use venv python explicitly
    venv_python = os.path.join(os.getcwd(), "venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        venv_python = "python" # fallback

    result = subprocess.run(
        [venv_python, "scripts/live_nautilus.py"],
        capture_output=True,
        text=True,
        cwd=os.getcwd()
    )
    
    print("\n--- STDOUT ---")
    print(result.stdout)
    print("\n--- STDERR ---")
    print(result.stderr)
    print("\n--- RETURN CODE ---")
    print(result.returncode)
except Exception as e:
    print(f"Error: {e}")
