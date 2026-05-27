import subprocess
import sys

print("Launching Crypto Quant Nexus Hub 2.0")
subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"], check=False)
