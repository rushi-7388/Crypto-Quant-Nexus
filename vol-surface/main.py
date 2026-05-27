import subprocess
import sys

print("Launching Vol Surface — Crypto Quant Nexus 2.0")
subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"], check=False)
