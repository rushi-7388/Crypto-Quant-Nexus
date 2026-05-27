import subprocess
import sys

print("Launching Funding Radar — Crypto Quant Nexus 2.0")
subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"], check=False)
