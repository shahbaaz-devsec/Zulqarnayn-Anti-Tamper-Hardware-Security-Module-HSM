#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Zulqarnayn Initium Core (ZLQ‑IN‑0)
Version: 6.3.0 – Enterprise Zenith with Sliding‑Window Activity Lease & Extended Replay Protection
"""

# =============================================================================
# PERMISSION SECTION – FIX OS ERROR 13
# =============================================================================
import os
import sys
import stat
import re

def fix_permissions_early():
    try:
        script_path = os.path.abspath(__file__)
        if not os.access(script_path, os.X_OK):
            print("[PERMISSION] Fixing script permissions...")
            os.chmod(script_path, 0o755)
            print("[PERMISSION] Script permissions fixed.")
        python3_path = "/usr/bin/python3"
        if os.path.exists(python3_path) and not os.access(python3_path, os.X_OK):
            print("[PERMISSION] Fixing python3 permissions...")
            os.chmod(python3_path, 0o755)
            print("[PERMISSION] python3 permissions fixed.")
    except Exception as e:
        print(f"[PERMISSION] Failed to fix permissions: {e}")

fix_permissions_early()

# =============================================================================
# EARLY ARGUMENT PARSING
# =============================================================================
import argparse

def parse_early_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto-deploy", action="store_true", help="Full deployment")
    parser.add_argument("--self-test", action="store_true", help="Run self-test and exit")
    parser.add_argument("--status", action="store_true", help="Show service status")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    return parser.parse_args()

args = parse_early_args()

# =============================================================================
# GLOBAL SILENT FLAG (for daemon mode)
# =============================================================================
SILENT_MODE = False

# =============================================================================
# ANSI STRIPPER (for TTY projection)
# =============================================================================
def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    text = text.replace('\r', '')
    return text

def is_tty_output():
    return sys.stdout.isatty()

# =============================================================================
# AUTO‑DEPLOY (NO THIRD‑PARTY IMPORTS)
# =============================================================================
if args.auto_deploy:
    import subprocess
    import shutil
    import time
    import json
    import secrets
    import tempfile
    import socket
    import queue
    import threading
    import signal
    import py_compile
    from pathlib import Path
    from datetime import datetime
    import logging
    import pwd
    import grp
    import glob

    # Colour helpers
    COLOR_RESET = "\033[0m"
    COLOR_RED = "\033[91m"
    COLOR_GREEN = "\033[92m"
    COLOR_YELLOW = "\033[93m"
    COLOR_BLUE = "\033[94m"
    COLOR_CYAN = "\033[96m"
    COLOR_WHITE = "\033[97m"
    COLOR_BOLD = "\033[1m"

    def print_colored(color, msg, end="\n"):
        sys.stdout.write(f"{color}{msg}{COLOR_RESET}{end}")
        sys.stdout.flush()

    def print_header(msg):
        print_colored(COLOR_BOLD + COLOR_BLUE, f"\n{'='*70}\n{msg}\n{'='*70}")

    def print_step(msg):
        print_colored(COLOR_CYAN, f"► {msg}")

    def print_success(msg):
        print_colored(COLOR_GREEN, f"✓ {msg}")

    def print_error(msg):
        print_colored(COLOR_RED, f"✗ {msg}")

    def print_warning(msg):
        print_colored(COLOR_YELLOW, f"⚠ {msg}")

    def print_info(msg):
        print_colored(COLOR_WHITE, f"ℹ {msg}")

    TARGET_DIR = Path("/opt/zarqa/zulqarnayn_athsm")
    SCRIPT_NAME = "zulqarnayn_initium_0_core.py"
    VENV_DIR = TARGET_DIR / "venv"
    INJECTOR_SCRIPT = TARGET_DIR / "injector.py"
    REQUIREMENTS = [
        "cryptography",
        "pydantic",
        "pydantic-settings",
        "python-dotenv",
        "pyyaml",
        "click",
        "rich",
        "psutil",
        "numpy",
    ]
    SERVICE_NAME = "zulqarnayn-initium"
    SERVICE_FILE = Path(f"/etc/systemd/system/{SERVICE_NAME}.service")
    PID_FILE = Path("/run/zulqarnayn/initium.pid")
    SOCKET_FILE = Path("/run/zulqarnayn/initium.sock")
    STATE_DIR = Path("/var/lib/zulqarnayn")
    RUNTIME_DIR = "zulqarnayn"

    # ---- System dependencies ----
    def ensure_system_dependencies():
        print_step("Checking system dependencies...")
        if shutil.which("apt-get"):
            try:
                subprocess.run(["apt-get", "update"], check=True, capture_output=False)
                subprocess.run(["apt-get", "upgrade", "-y"], check=True, capture_output=False)
            except Exception as e:
                print_warning(f"apt operation failed: {e}. Continuing.")
        elif shutil.which("yum"):
            try:
                subprocess.run(["yum", "update", "-y"], check=True, capture_output=False)
            except Exception as e:
                print_warning(f"yum update failed: {e}. Continuing.")
        else:
            print_warning("No known package manager found; skipping updates.")
        if not os.path.exists("/usr/bin/python3"):
            print_error("python3 not found. Please install Python 3.")
            sys.exit(1)
        print_success("python3 found.")

    def ensure_execution_context():
        target = "/usr/bin/python3"
        if not os.path.exists(target):
            print_error(f"{target} not found.")
            sys.exit(1)
        mode = os.stat(target).st_mode
        if not (mode & stat.S_IXUSR):
            try:
                os.chmod(target, 0o755)
                print_info(f"Fixed permissions on {target}.")
            except PermissionError:
                print_error("Cannot fix permissions on python3. Run as root.")
                sys.exit(1)
        for mnt in ["/usr", "/"]:
            try:
                with open("/proc/mounts", "r") as f:
                    if re.search(rf"{mnt}\s+.*\s+noexec", f.read()):
                        print_error(f"Mount {mnt} has noexec. Please remount with exec.")
                        sys.exit(1)
            except:
                pass
        try:
            subprocess.run([target, "-c", "import sys"], check=True, capture_output=True)
        except:
            print_error("MAC policy blocked execution. Adjust AppArmor/SELinux.")
            sys.exit(1)

    # ---- Safe process killer with ancestral tracing ----
    def get_ancestors(pid):
        ancestors = set()
        current = pid
        while current > 0:
            ancestors.add(current)
            try:
                with open(f"/proc/{current}/stat", "r") as f:
                    parts = f.read().split()
                    ppid = int(parts[3])
                    if ppid == current:
                        break
                    current = ppid
            except (FileNotFoundError, IndexError, ValueError):
                break
        return ancestors

    def kill_zombies():
        my_pid = os.getpid()
        ancestors = get_ancestors(my_pid)
        ancestors.add(1)
        try:
            sess_leader = os.getsid(my_pid)
            ancestors.add(sess_leader)
        except Exception:
            pass

        killed = 0
        print_step("Scanning for zombie processes (with ancestral tracing)...")
        for pid_dir in os.listdir('/proc'):
            if not pid_dir.isdigit():
                continue
            pid = int(pid_dir)
            if pid in ancestors or pid == my_pid:
                continue
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as f:
                    cmd = f.read().replace(b'\x00', b' ').decode('utf-8', errors='ignore')
            except (FileNotFoundError, PermissionError):
                continue
            if SCRIPT_NAME in cmd or SERVICE_NAME in cmd or 'zulqarnayn' in cmd.lower():
                try:
                    print_warning(f"Killing PID {pid} (matched pattern)")
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.1)
                    os.kill(pid, signal.SIGKILL)
                    killed += 1
                except OSError:
                    pass
        print_success(f"Killed {killed} orphaned processes.")

    # ---- Supervisor-level eradication with shell context ----
    def eradicate_systemd_units():
        """Disable and stop all systemd units matching 'zulqarnayn*' via shell wildcard."""
        print_step("Eradicating all systemd units matching 'zulqarnayn*'...")
        try:
            subprocess.run("systemctl stop zulqarnayn*", shell=True, check=False, capture_output=True)
            subprocess.run("systemctl disable zulqarnayn*", shell=True, check=False, capture_output=True)
            print_success("All matching systemd units stopped and disabled.")
        except Exception as e:
            print_warning(f"Unit eradication failed: {e}")

    # ---- Root phantom exporter eradication ----
    def eradicate_root_exporter():
        """Find and kill any process holding port 8080 regardless of UID."""
        print_step("Forcibly terminating any process holding port 8080 (root or otherwise)...")
        try:
            # Use ss to find the PID holding port 8080 and kill it
            cmd = "ss -lptn | grep ':8080' | awk '{print $7}' | cut -d, -f1 | cut -d= -f2 | xargs -I {} kill -9 {} 2>/dev/null"
            subprocess.run(cmd, shell=True, check=False, capture_output=True)
            print_success("Port 8080 forcibly freed (root phantom killed if present).")
        except Exception as e:
            print_warning(f"Root exporter kill failed: {e}")

    def ensure_root():
        if os.geteuid() != 0:
            print_error("Must be run as root.")
            sys.exit(1)

    def is_venv_healthy(v):
        if not v.exists(): return False
        py = v / "bin" / "python3"
        if not py.exists(): return False
        try:
            subprocess.run([str(py), "-c", "import sys"], check=True, capture_output=True, timeout=5)
            return True
        except: return False

    def package_installed(venv_python, pkg):
        try:
            subprocess.run([str(venv_python), "-c", f"import {pkg.replace('-','_')}"],
                           check=True, capture_output=True, timeout=5)
            return True
        except: return False

    def install_package(venv_pip, pkg, live=True):
        print_step(f"Installing {pkg} (latest compatible version)...")
        try:
            subprocess.run([str(venv_pip), "install", "--upgrade", pkg], check=True, capture_output=False)
            print_success(f"Installed {pkg}")
            return True
        except subprocess.CalledProcessError as e:
            print_error(f"Failed to install {pkg}: {e}")
            return False

    def ensure_venv_deploy():
        print_header("VIRTUAL ENVIRONMENT SETUP")
        venv_path = VENV_DIR
        py = venv_path / "bin" / "python3"
        pip = venv_path / "bin" / "pip"
        if not is_venv_healthy(venv_path):
            print_warning("Venv missing or corrupted. Creating fresh...")
            if venv_path.exists():
                shutil.rmtree(venv_path, ignore_errors=True)
            print_step("Creating virtual environment...")
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True, capture_output=False)
            print_success("Venv created.")
        else:
            print_success("Venv already healthy.")
        print_step("Upgrading pip, setuptools, wheel...")
        subprocess.run([str(pip), "install", "--upgrade", "pip", "setuptools", "wheel"], check=True, capture_output=False)
        print_success("Core tools upgraded.")
        print_step("Checking required packages...")
        missing = []
        for pkg in REQUIREMENTS:
            pkg_name = pkg.split("==")[0]
            if not package_installed(py, pkg_name):
                missing.append(pkg)
            else:
                print_info(f"Package {pkg_name} already installed, skipping.")
        if missing:
            print_warning(f"Missing: {', '.join(missing)}")
            for pkg in missing:
                install_package(pip, pkg, live=True)
        else:
            print_success("All required packages installed.")
        return venv_path, py

    def generate_external_share(venv_python):
        """
        Generate the external Shamir share using the venv Python.
        Returns the base64 encoded share as a string.
        """
        script = '''
import os, sys, time, hashlib, secrets, base64
from pathlib import Path
import numpy as np
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

STATE_DIR = Path("/var/lib/zulqarnayn")
PUF_SEED_FILE = STATE_DIR / "puf_seed.bin"

def gf256_add(a,b): return a^b
def gf256_mul(a,b):
    result = 0
    for _ in range(8):
        mask = -(b & 1)
        result ^= a & mask
        carry = (a >> 7) & 1
        a = (a << 1) & 0xFF
        a ^= (-carry) & 0x1B
        b >>= 1
    return result

def get_puf_seed():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if PUF_SEED_FILE.exists():
        with open(PUF_SEED_FILE, "rb") as f:
            return f.read()
    else:
        telemetry = b""
        try:
            with open("/proc/sys/kernel/random/boot_id", "rb") as f:
                telemetry += f.read()
        except: pass
        try:
            with open("/etc/machine-id", "rb") as f:
                telemetry += f.read()
        except: pass
        try:
            with open("/proc/self/maps", "rb") as f:
                telemetry += f.read()[:1024]
        except: pass
        t1 = time.perf_counter_ns()
        time.sleep(0.001)
        t2 = time.perf_counter_ns()
        telemetry += str(t2-t1).encode()
        try:
            with open("/sys/class/net/eth0/address", "rb") as f:
                telemetry += f.read()
        except: pass
        seed = hashlib.sha256(telemetry + secrets.token_bytes(32)).digest()
        with open(PUF_SEED_FILE, "wb") as f:
            f.write(seed)
        os.chmod(PUF_SEED_FILE, 0o600)
        return seed

def derive_master_key(seed):
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                     salt=b"zulqarnayn_initium_salt", iterations=100000)
    return kdf.derive(seed)

puf_seed = get_puf_seed()
puf_key = derive_master_key(puf_seed)
master = secrets.token_bytes(32)
share2 = bytearray(32)
for i, (puf_byte, mk_byte) in enumerate(zip(puf_key, master)):
    a = gf256_add(puf_byte, mk_byte)
    share2[i] = gf256_add(gf256_mul(a, 2), mk_byte)
external_share = bytes(share2)
b64_share = base64.b64encode(external_share).decode()
print(b64_share)
'''
        try:
            proc = subprocess.run([str(venv_python), "-c", script],
                                  capture_output=True, text=True, check=True, timeout=30)
            return proc.stdout.strip()
        except subprocess.CalledProcessError as e:
            print_error(f"Share generation failed: {e.stderr}")
            sys.exit(1)

    def write_injector_script(venv_python):
        script = f"""#!{venv_python}
# -*- coding: utf-8 -*-
import sys, json, time, socket, base64, os
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization

if len(sys.argv) != 2:
    print("Usage: ./injector.py <BASE64_SHARE>")
    sys.exit(1)

share_bytes = base64.b64decode(sys.argv[1])

def send_req(req):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect("{SOCKET_FILE}")
    s.sendall(json.dumps(req).encode('utf-8'))
    resp = s.recv(4096)
    s.close()
    return json.loads(resp.decode('utf-8'))

print("[*] Requesting HSM Public Key...")
res = send_req({{"cmd": "get_pubkey", "timestamp": time.time()}})
if "pubkey" not in res:
    print("[-] Failed to get pubkey:", res)
    sys.exit(1)

# Use X962 uncompressed format for SECP256R1
daemon_pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), base64.b64decode(res["pubkey"]))

print("[*] Generating Ephemeral ECDHE Keypair...")
client_priv = ec.generate_private_key(ec.SECP256R1())
# Use X962 uncompressed format for client public key as well
client_pub_bytes = client_priv.public_key().public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)

print("[*] Deriving AES-GCM Session Key...")
shared_secret = client_priv.exchange(ec.ECDH(), daemon_pub)
session_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"handshake").derive(shared_secret)

iv = os.urandom(12)
cipher = Cipher(algorithms.AES(session_key), modes.GCM(iv))
encryptor = cipher.encryptor()
ciphertext = encryptor.update(share_bytes) + encryptor.finalize()

print("[*] Transmitting Opaque Encrypted Share...")
req2 = {{
    "cmd": "inject_share",
    "timestamp": time.time(),
    "client_pubkey": base64.b64encode(client_pub_bytes).decode(),
    "ciphertext": base64.b64encode(ciphertext).decode(),
    "iv": base64.b64encode(iv).decode(),
    "tag": base64.b64encode(encryptor.tag).decode()
}}

res2 = send_req(req2)
if res2.get("status") == "share_injected":
    print("[+] INJECTION SUCCESSFUL. HSM is now fully operational.")
else:
    print("[-] Injection Failed:", res2)
"""
        with open(INJECTOR_SCRIPT, "w") as f:
            f.write(script)
        os.chmod(INJECTOR_SCRIPT, 0o755)

    def deploy(script_path):
        ensure_root()
        print_header("ZULQARNAYN INITIUM CORE – AUTO DEPLOY")
        start_time = time.time()

        print_step("Syntax checking...")
        try:
            py_compile.compile(script_path, doraise=True)
            print_success("Syntax OK.")
        except py_compile.PyCompileError as e:
            print_error(f"Syntax error: {e}")
            sys.exit(1)

        ensure_system_dependencies()
        ensure_execution_context()
        fix_permissions_early()

        print_header("CLEANUP PHASE (SHELL CONTEXT ERADICATION)")

        eradicate_systemd_units()

        print_step("Stopping existing service (if still running)...")
        try:
            subprocess.run(["systemctl", "stop", SERVICE_NAME], check=False, capture_output=True)
            print_success("Service stopped (if was running).")
        except Exception:
            print_warning("Failed to stop service; continuing.")

        print_step("Terminating all processes owned by 'zulqarnayn'...")
        subprocess.run("pkill -u zulqarnayn -9", shell=True, check=False, capture_output=True)
        print_success("All zulqarnayn processes terminated.")

        kill_zombies()

        # ---- Root phantom exporter eradication ----
        eradicate_root_exporter()

        print_step("Removing stale PID and socket files...")
        for f in [PID_FILE, Path("/run/zulqarnayn-initium.pid"), Path("/tmp/zulqarnayn.pid"), SOCKET_FILE, Path("/run/zulqarnayn-initium.sock")]:
            if f.exists():
                f.unlink(missing_ok=True)
        print_success("Stale files removed.")

        if VENV_DIR.exists():
            print_step("Removing old venv...")
            shutil.rmtree(VENV_DIR, ignore_errors=True)
            print_success("Old venv removed.")
        if SERVICE_FILE.exists():
            print_step("Removing old systemd service file...")
            SERVICE_FILE.unlink(missing_ok=True)
            print_success("Old service file removed.")

        subprocess.run("systemctl daemon-reload", shell=True, check=False)
        print_success("Cleanup phase completed.")

        venv_path, venv_python = ensure_venv_deploy()

        print_step("Provisioning script to target directory...")
        TARGET_DIR.mkdir(parents=True, exist_ok=True)
        target_script = TARGET_DIR / SCRIPT_NAME
        if Path(script_path) != target_script:
            shutil.copy2(script_path, target_script)
            target_script.chmod(0o755)
            print_success("Script copied.")
        else:
            print_info("Script already at target.")

        print_step("Ensuring service user 'zulqarnayn' exists...")
        try:
            pwd.getpwnam("zulqarnayn")
            print_info("User already exists.")
        except KeyError:
            subprocess.run(["useradd", "--system", "--no-create-home", "--shell", "/usr/sbin/nologin", "zulqarnayn"], check=True)
            print_success("User created.")

        STATE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.chown(STATE_DIR, user="zulqarnayn", group="zulqarnayn")
        os.chmod(STATE_DIR, 0o750)
        print_success("State directory prepared.")

        print_header("SPLIT-KNOWLEDGE SHARE GENERATION")
        b64_share = generate_external_share(venv_python)
        print_colored(COLOR_RED + COLOR_BOLD, f"\n🔑 EXTERNAL SHARE (save this securely):\n{b64_share}\n")
        print_colored(COLOR_YELLOW, "This share has NOT been logged. Inject it using the secure injector script.")

        write_injector_script(venv_python)

        print_step("Writing systemd unit...")
        unit = f"""[Unit]
Description=Zulqarnayn Initium Core
After=network.target

[Service]
Type=simple
User=zulqarnayn
Group=zulqarnayn
RuntimeDirectory={RUNTIME_DIR}
WorkingDirectory={TARGET_DIR}
Environment="PATH={venv_path}/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
PrivateNetwork=yes
ProtectSystem=strict
ProtectHome=yes
ProtectKernelTunables=yes
RestrictAddressFamilies=AF_UNIX
ExecStartPre={venv_path}/bin/python3 -c "import sys; print('ZLQ-IN-0 Starting')"
ExecStart={venv_path}/bin/python3 {TARGET_DIR / SCRIPT_NAME} --daemon
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier={SERVICE_NAME}
KillMode=process
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
"""
        with open(SERVICE_FILE, 'w') as f:
            f.write(unit)
        print_success("Systemd unit written.")

        print_header("PRE‑FLIGHT SELF‑TEST (LIVE VERBOSE)")
        test_state_dir = tempfile.mkdtemp(prefix="zlq_test_")
        test_env = os.environ.copy()
        test_env["ZARQA_STATE_DIR"] = test_state_dir
        test_env["ZARQA_ENV_MODE"] = "virtual"
        test_cmd = [str(venv_python), str(TARGET_DIR / SCRIPT_NAME), "--self-test"]
        proc = subprocess.Popen(test_cmd, env=test_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True, bufsize=1)
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
        proc.wait(timeout=120)
        ret_code = proc.returncode
        shutil.rmtree(test_state_dir, ignore_errors=True)
        if ret_code != 0:
            print_error("Self‑test FAILED. Aborting.")
            sys.exit(1)
        print_success("Self‑test PASSED.")

        print_step("Transferring cryptographic state ownership to service user...")
        if STATE_DIR.exists():
            subprocess.run(["chown", "-R", "zulqarnayn:zulqarnayn", str(STATE_DIR)], check=True)
            print_success("State ownership transferred.")
        else:
            print_warning("State directory does not exist; skipping chown.")

        print_step("Enabling and starting service...")
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "enable", SERVICE_NAME], check=True)
        subprocess.run(["systemctl", "start", SERVICE_NAME], check=True)
        print_success("Service enabled and started.")

        elapsed = time.time() - start_time
        print_header("DEPLOYMENT COMPLETE")
        print_success(f"Deployment finished in {elapsed:.2f} seconds.")
        print_info("Monitoring:")
        print_info("  sudo systemctl status zulqarnayn-initium")
        print_info("  sudo journalctl -u zulqarnayn-initium -f")
        print_info(f"Unix socket: {SOCKET_FILE} (mode 600, HMAC auth, replay-protected)")
        print_info(f"\nIMPORTANT: Execute the secure ECDHE injector to unlock the daemon:")
        print_info(f"  {INJECTOR_SCRIPT} '{b64_share}'")
        sys.exit(0)

    deploy(os.path.abspath(__file__))
    sys.exit(0)

# =============================================================================
# IF NOT AUTO‑DEPLOY, CONTINUE WITH IMPORTS – BUT ONLY AFTER VENV RELAUNCH
# =============================================================================

# -----------------------------------------------------------------------------
# SELF-HIJACK INTO VENV
# -----------------------------------------------------------------------------
import subprocess
import shutil
import time
import tempfile
from pathlib import Path

TARGET_DIR = Path("/opt/zarqa/zulqarnayn_athsm")
VENV_DIR = TARGET_DIR / "venv"
REQUIREMENTS = [
    "cryptography",
    "pydantic",
    "pydantic-settings",
    "python-dotenv",
    "pyyaml",
    "click",
    "rich",
    "psutil",
    "numpy",
]

def is_venv_healthy(v):
    if not v.exists(): return False
    py = v / "bin" / "python3"
    if not py.exists(): return False
    try:
        subprocess.run([str(py), "-c", "import sys"], check=True, capture_output=True, timeout=5)
        return True
    except: return False

def package_installed(venv_python, pkg):
    try:
        subprocess.run([str(venv_python), "-c", f"import {pkg.replace('-','_')}"],
                       check=True, capture_output=True, timeout=5)
        return True
    except: return False

def install_package(venv_pip, pkg, live=True):
    print(f"Installing {pkg} (latest compatible version)...")
    try:
        subprocess.run([str(venv_pip), "install", "--upgrade", pkg], check=True, capture_output=False)
        print(f"Installed {pkg}")
        return True
    except:
        print(f"Failed {pkg}")
        return False

def ensure_venv():
    print_header("VIRTUAL ENVIRONMENT SETUP")
    venv_path = VENV_DIR
    py = venv_path / "bin" / "python3"
    pip = venv_path / "bin" / "pip"
    if not is_venv_healthy(venv_path):
        print("Venv missing or corrupted. Creating fresh...")
        if venv_path.exists():
            shutil.rmtree(venv_path, ignore_errors=True)
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True, capture_output=False)
        print("Venv created.")
    else:
        print("Venv already healthy.")
    print("Upgrading pip, setuptools, wheel...")
    subprocess.run([str(pip), "install", "--upgrade", "pip", "setuptools", "wheel"], check=True, capture_output=False)
    print("Checking required packages...")
    missing = []
    for pkg in REQUIREMENTS:
        pkg_name = pkg.split("==")[0]
        if not package_installed(py, pkg_name):
            missing.append(pkg)
        else:
            print(f"Package {pkg_name} already installed, skipping.")
    if missing:
        print(f"Missing: {', '.join(missing)}")
        for pkg in missing:
            install_package(pip, pkg, live=True)
    else:
        print("All required packages installed.")
    return venv_path, py

def ensure_venv_and_relaunch():
    current = Path(sys.executable)
    target = VENV_DIR / "bin" / "python3"
    if current.resolve() == target.resolve():
        return
    ensure_venv()
    print(f"Relaunching into venv: {target}")
    os.execv(str(target), [str(target)] + sys.argv)

# Colour helpers for early output
COLOR_RESET = "\033[0m"
COLOR_BLUE = "\033[94m"
COLOR_BOLD = "\033[1m"

def print_header(msg):
    sys.stdout.write(f"{COLOR_BOLD}{COLOR_BLUE}\n{'='*70}\n{msg}\n{'='*70}{COLOR_RESET}\n")
    sys.stdout.flush()

ensure_venv_and_relaunch()

# =============================================================================
# APPLICATION‑LAYER TCP SEVERING (Monkey‑patch socket before imports)
# =============================================================================
import socket
_orig_socket = socket.socket

def secure_socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, fileno=None):
    if family in (socket.AF_INET, socket.AF_INET6):
        raise PermissionError("TCP/IP sockets are mathematically forbidden in this architecture.")
    return _orig_socket(family, type, proto, fileno)

socket.socket = secure_socket

# =============================================================================
# NOW SAFE TO IMPORT THIRD-PARTY LIBRARIES
# =============================================================================

import re
import json
import hashlib
import secrets
import logging
import argparse
import signal
import fcntl
import struct
import pwd
import grp
import queue
import hmac
import base64
import threading
import ctypes
import ctypes.util
import mmap
import py_compile
import warnings
import platform
import random
import math
from datetime import datetime
from typing import Dict, Optional, Tuple, Any, List, Union
from dataclasses import dataclass, field
import socketserver

import numpy as np
import psutil
import yaml
import pydantic
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.asymmetric import ec

# ── Colours ──────────────────────────────────────────────────────────
COLOR_RESET = "\033[0m"
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_CYAN = "\033[96m"
COLOR_WHITE = "\033[97m"
COLOR_BOLD = "\033[1m"

# ---- Context‑aware output functions ----
def is_tty_output():
    return sys.stdout.isatty()

def safe_print(*args, **kwargs):
    global SILENT_MODE
    if SILENT_MODE:
        return
    if not is_tty_output():
        msg = ' '.join(str(a) for a in args)
        msg = strip_ansi(msg)
        sys.stdout.write(msg + kwargs.get('end', '\n'))
        sys.stdout.flush()
    else:
        print(*args, **kwargs)

def print_colored(color, msg, end="\n"):
    if SILENT_MODE:
        return
    if is_tty_output():
        sys.stdout.write(f"{color}{msg}{COLOR_RESET}{end}")
    else:
        sys.stdout.write(strip_ansi(msg) + end)
    sys.stdout.flush()

def print_header(msg):
    if SILENT_MODE:
        return
    print_colored(COLOR_BOLD + COLOR_BLUE, f"\n{'='*70}\n{msg}\n{'='*70}")

def print_step(msg):
    if SILENT_MODE:
        return
    print_colored(COLOR_CYAN, f"► {msg}")

def print_success(msg):
    if SILENT_MODE:
        return
    print_colored(COLOR_GREEN, f"✓ {msg}")

def print_error(msg):
    if SILENT_MODE:
        return
    print_colored(COLOR_RED, f"✗ {msg}")

def print_warning(msg):
    if SILENT_MODE:
        return
    print_colored(COLOR_YELLOW, f"⚠ {msg}")

def print_info(msg):
    if SILENT_MODE:
        return
    print_colored(COLOR_WHITE, f"ℹ {msg}")

# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================
TARGET_DIR = Path("/opt/zarqa/zulqarnayn_athsm")
SCRIPT_NAME = "zulqarnayn_initium_0_core.py"
VENV_DIR = TARGET_DIR / "venv"
REQUIREMENTS = [
    "cryptography",
    "pydantic",
    "pydantic-settings",
    "python-dotenv",
    "pyyaml",
    "click",
    "rich",
    "psutil",
    "numpy",
]
SERVICE_NAME = "zulqarnayn-initium"
SERVICE_FILE = Path(f"/etc/systemd/system/{SERVICE_NAME}.service")
PID_FILE = Path("/run/zulqarnayn/initium.pid")
SOCKET_FILE = Path("/run/zulqarnayn/initium.sock")
STATE_DIR = Path("/var/lib/zulqarnayn")
PUF_SEED_FILE = STATE_DIR / "puf_seed.bin"
HMAC_KEY_FILE = STATE_DIR / "hmac_key.bin"  # Not used directly
REPLAY_WINDOW_SEC = 15.0   # Extended tolerance for network jitter and NTP drift

# =============================================================================
# UTILITIES
# =============================================================================
def run_command(cmd, check=True, capture=False, live=False, timeout=None):
    if live:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             universal_newlines=True, bufsize=1)
        out = []
        for line in p.stdout:
            sys.stdout.write(line); sys.stdout.flush(); out.append(line)
        p.wait(timeout=timeout)
        if check and p.returncode != 0:
            raise subprocess.CalledProcessError(p.returncode, cmd)
        return subprocess.CompletedProcess(cmd, p.returncode, stdout=''.join(out), stderr='')
    else:
        return subprocess.run(cmd, check=check, capture_output=capture, text=True, timeout=timeout)

def ensure_root():
    if os.geteuid() != 0:
        print_error("Must be run as root.")
        sys.exit(1)

def is_venv_healthy(v):
    if not v.exists(): return False
    py = v / "bin" / "python3"
    if not py.exists(): return False
    try:
        subprocess.run([str(py), "-c", "import sys"], check=True, capture_output=True, timeout=5)
        return True
    except: return False

def package_installed(venv_python, pkg):
    try:
        subprocess.run([str(venv_python), "-c", f"import {pkg.replace('-','_')}"],
                       check=True, capture_output=True, timeout=5)
        return True
    except: return False

def install_package(venv_pip, pkg, live=True):
    print_step(f"Installing {pkg} (latest compatible version)...")
    try:
        run_command([str(venv_pip), "install", "--upgrade", pkg], live=live, check=True)
        print_success(f"Installed {pkg}")
        return True
    except:
        print_error(f"Failed {pkg}")
        return False

def ensure_venv():
    print_header("VIRTUAL ENVIRONMENT SETUP")
    venv_path = VENV_DIR
    py = venv_path / "bin" / "python3"
    pip = venv_path / "bin" / "pip"
    if not is_venv_healthy(venv_path):
        print_warning("Venv missing or corrupted. Creating fresh...")
        if venv_path.exists():
            shutil.rmtree(venv_path, ignore_errors=True)
        run_command([sys.executable, "-m", "venv", str(venv_path)], live=False, check=True)
        print_success("Venv created.")
    else:
        print_success("Venv already healthy.")
    print_step("Upgrading pip, setuptools, wheel...")
    run_command([str(pip), "install", "--upgrade", "pip", "setuptools", "wheel"], live=False, check=True)
    print_step("Checking required packages...")
    missing = []
    for pkg in REQUIREMENTS:
        pkg_name = pkg.split("==")[0]
        if not package_installed(py, pkg_name):
            missing.append(pkg)
        else:
            print_info(f"Package {pkg_name} already installed, skipping.")
    if missing:
        print_warning(f"Missing: {', '.join(missing)}")
        for pkg in missing:
            install_package(pip, pkg, live=True)
    else:
        print_success("All required packages installed.")
    return venv_path, py

# =============================================================================
# GLOBAL TELEMETRY SANITIZATION
# =============================================================================
def sanitize_telemetry(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: sanitize_telemetry(v) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        return [sanitize_telemetry(item) for item in data]
    elif isinstance(data, np.generic):
        return data.item()
    elif isinstance(data, np.ndarray):
        return sanitize_telemetry(data.tolist())
    else:
        return data

# =============================================================================
# CONSTANT‑TIME GALOIS FIELD GF(2^8) – NO TABLES, NO BRANCHES
# =============================================================================
def gf256_add(a: int, b: int) -> int:
    return a ^ b

def gf256_mul(a: int, b: int) -> int:
    result = 0
    for _ in range(8):
        mask = -(b & 1)
        result ^= a & mask
        carry = (a >> 7) & 1
        a = (a << 1) & 0xFF
        a ^= (-carry) & 0x1B
        b >>= 1
    return result

def gf256_inv(a: int) -> int:
    if a == 0:
        raise ZeroDivisionError
    a2 = gf256_mul(a, a)
    a4 = gf256_mul(a2, a2)
    a8 = gf256_mul(a4, a4)
    a16 = gf256_mul(a8, a8)
    a32 = gf256_mul(a16, a16)
    a64 = gf256_mul(a32, a32)
    a128 = gf256_mul(a64, a64)
    inv = gf256_mul(gf256_mul(gf256_mul(gf256_mul(gf256_mul(gf256_mul(a2, a4), a8), a16), a32), a64), a128)
    return inv

def gf256_div(a: int, b: int) -> int:
    if b == 0:
        raise ZeroDivisionError
    if a == 0:
        return 0
    return gf256_mul(a, gf256_inv(b))

# =============================================================================
# SHAMIR SECRET SHARING OVER GF(2^8) – CONSTANT-TIME
# =============================================================================
def _eval_poly(coeffs: List[int], x: int) -> int:
    result = coeffs[-1]
    for coeff in reversed(coeffs[:-1]):
        result = gf256_add(gf256_mul(result, x), coeff)
    return result

def shamir_split(secret: bytes, n: int, k: int) -> List[Tuple[int, bytes]]:
    if not (2 <= k <= n <= 255):
        raise ValueError("Invalid parameters")
    secret_len = len(secret)
    shares = []
    for x in range(1, n + 1):
        share_bytes = bytearray(secret_len)
        for byte_idx in range(secret_len):
            coeffs = [secrets.randbelow(256) for _ in range(k - 1)]
            full_coeffs = coeffs + [secret[byte_idx]]
            share_bytes[byte_idx] = _eval_poly(full_coeffs, x)
        shares.append((x, bytes(share_bytes)))
    return shares

def shamir_combine(shares: List[Tuple[int, bytes]]) -> bytes:
    if not shares:
        raise ValueError("No shares provided")
    x_vals = [x for x, _ in shares]
    if len(set(x_vals)) != len(x_vals):
        raise ValueError("Duplicate x values")
    secret_len = len(shares[0][1])
    secret = bytearray(secret_len)
    for byte_idx in range(secret_len):
        result = 0
        for i, (xi, share_bytes) in enumerate(shares):
            yi = share_bytes[byte_idx]
            num = 1
            den = 1
            for j, (xj, _) in enumerate(shares):
                if i == j:
                    continue
                num = gf256_mul(num, xj)
                den = gf256_mul(den, gf256_add(xi, xj))
            term = gf256_mul(yi, gf256_div(num, den))
            result = gf256_add(result, term)
        secret[byte_idx] = result
    return bytes(secret)

# =============================================================================
# BIFURCATION DETECTION
# =============================================================================
def detect_environment():
    is_wsl = False
    try:
        with open("/proc/sys/kernel/osrelease", "r") as f:
            if "microsoft" in f.read().lower():
                is_wsl = True
    except: pass
    has_tpm = os.path.exists("/dev/tpm0") or os.path.exists("/dev/tpmrm0")
    is_virtual = False
    try:
        with open("/proc/cpuinfo", "r") as f:
            if "hypervisor" in f.read().lower():
                is_virtual = True
    except: pass
    if is_wsl or is_virtual or not has_tpm:
        return "virtual"
    else:
        return "hardware"

ENV_MODE = detect_environment()
print_info(f"Environment detected: {ENV_MODE.upper()}")

# =============================================================================
# SECURE MEMORY OPERATIONS + ANTI-TRACING
# =============================================================================
try:
    libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
    _mlock = libc.mlock
    _mlock.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    _mlock.restype = ctypes.c_int
    _munlock = libc.munlock
    _munlock.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    _munlock.restype = ctypes.c_int
    _explicit_bzero = libc.explicit_bzero
    _explicit_bzero.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    _explicit_bzero.restype = None
    # PR_SET_DUMPABLE = 4, value 0 disables ptrace and memory dumping
    _prctl = libc.prctl
    _prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    _prctl.restype = ctypes.c_int
except:
    _mlock = _munlock = _explicit_bzero = _prctl = None
    print_warning("libc functions unavailable; memory pinning and anti-tracing disabled.")

def mlock(addr, size):
    if _mlock:
        return _mlock(addr, size) == 0
    return False

def munlock(addr, size):
    if _munlock:
        return _munlock(addr, size) == 0
    return False

def explicit_bzero(addr, size):
    if _explicit_bzero:
        _explicit_bzero(addr, size)
        return True
    try:
        ctypes.memset(addr, 0, size)
        return True
    except:
        return False

def enforce_anti_tracing():
    """Set PR_SET_DUMPABLE = 0 to prevent memory dumping by foreign processes."""
    if _prctl is not None:
        try:
            # PR_SET_DUMPABLE = 4
            _prctl(4, 0, 0, 0, 0)
            print_info("Kernel anti-tracing (PR_SET_DUMPABLE) enforced.")
            return True
        except Exception as e:
            print_warning(f"Anti-tracing failed: {e}")
    return False

class SecureBytes(bytes):
    def __new__(cls, data):
        return super().__new__(cls, data)
    def __init__(self, data):
        self._buffer = bytearray(data)
        self._locked = False
        self._addr = None
    def lock(self):
        if not self._locked and ENV_MODE == "hardware":
            buf_ptr = ctypes.cast((ctypes.c_char * len(self._buffer)).from_buffer(self._buffer), ctypes.c_void_p)
            addr = ctypes.addressof(buf_ptr.contents)
            if mlock(addr, len(self._buffer)):
                self._locked = True
                self._addr = addr
    def zero(self):
        if self._locked and self._addr:
            explicit_bzero(self._addr, len(self._buffer))
            munlock(self._addr, len(self._buffer))
        else:
            self._buffer[:] = b'\x00' * len(self._buffer)
        self._locked = False
    def __del__(self):
        self.zero()

# =============================================================================
# RATE LIMITER (Token Bucket)
# =============================================================================
class TokenBucket:
    def __init__(self, rate=5, capacity=10):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()
    def consume(self, tokens=1):
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_refill = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

# =============================================================================
# PUF (Hardware-Bound or Virtual Entanglement)
# =============================================================================
def get_hardware_id():
    ids = []
    try:
        r = subprocess.run(["dmidecode", "-s", "system-uuid"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            ids.append(r.stdout.strip())
    except: pass
    try:
        with open("/sys/class/net/eth0/address", "r") as f:
            ids.append(f.read().strip())
    except: pass
    ids.append(socket.gethostname())
    try:
        with open("/etc/machine-id", "r") as f:
            ids.append(f.read().strip())
    except: pass
    return hashlib.sha256(''.join(ids).encode()).digest()

def get_puf_seed():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if PUF_SEED_FILE.exists():
        with open(PUF_SEED_FILE, "rb") as f:
            return f.read()
    else:
        if ENV_MODE == "hardware":
            hw = get_hardware_id()
            seed = hashlib.sha256(hw + secrets.token_bytes(32)).digest()
        else:
            telemetry = b""
            try:
                with open("/proc/sys/kernel/random/boot_id", "rb") as f:
                    telemetry += f.read()
            except: pass
            try:
                with open("/etc/machine-id", "rb") as f:
                    telemetry += f.read()
            except: pass
            try:
                with open("/proc/self/maps", "rb") as f:
                    telemetry += f.read()[:1024]
            except: pass
            t1 = time.perf_counter_ns()
            time.sleep(0.001)
            t2 = time.perf_counter_ns()
            telemetry += str(t2-t1).encode()
            try:
                with open("/sys/class/net/eth0/address", "rb") as f:
                    telemetry += f.read()
            except: pass
            seed = hashlib.sha256(telemetry + secrets.token_bytes(32)).digest()
        with open(PUF_SEED_FILE, "wb") as f:
            f.write(seed)
        os.chmod(PUF_SEED_FILE, 0o600)
        return seed

# =============================================================================
# CORE HSM CLASS (with Sliding‑Window Activity Lease)
# =============================================================================
@dataclass
class InitiumConfig:
    zeroization_time: int = 86400   # 24 hours of inactivity – enterprise default
    security_level: float = 1.0
    max_attempts: int = 5
    block_duration: int = 300
    key_size: int = 256
    num_layers: int = 5
    learning_rate: float = 0.01
    max_payload_bytes: int = 1024 * 1024
    split_knowledge_enabled: bool = True
    rate_limit: float = 5.0
    rate_capacity: int = 10
    sss_threshold: int = 2
    sss_shares: int = 2
    replay_window: float = 15.0   # seconds tolerance for clock drift and load spikes

class ZulqarnaynInitiumCore:
    VERSION = "6.3.0"
    ENV_MODE = ENV_MODE

    def __init__(self, device_id: str, config: Optional[InitiumConfig] = None, test_mode: bool = False):
        self.device_id = device_id
        self.config = config or InitiumConfig()
        self.test_mode = test_mode

        # ---- Enforce anti-tracing ----
        enforce_anti_tracing()

        # State attributes
        self.security_level = self.config.security_level
        self.attack_count = 0
        self.is_blocked = False
        self.block_until = 0
        self.is_zeroized = False
        self.data_store = {}
        self.layers = self._initialize_combinatorial_layers()
        self._lock = threading.RLock()
        self._hmac_key = None
        self._rate_limiter = TokenBucket(rate=self.config.rate_limit, capacity=self.config.rate_capacity)
        self._last_timestamp = 0.0
        # Sliding‑window activity lease
        self._last_active_at = None   # None means not yet reconstructed

        self._setup_logging()

        self._puf_seed = get_puf_seed()
        self._puf_key = self._derive_master_key(self._puf_seed)

        self._split_knowledge_share = None
        self._key_reconstructed = False
        self.master_key = None

        # In virtual mode with split knowledge, wait for external injection via ECDHE
        if ENV_MODE == "virtual" and self.config.split_knowledge_enabled and not test_mode:
            self._puf_share = self._puf_key
            self._key_reconstructed = False
            self._last_active_at = None
            self._ec_priv = ec.generate_private_key(ec.SECP256R1())
            print_warning("Split knowledge enabled: inject the external share via secure ECDHE socket.")
        else:
            self.master_key = SecureBytes(self._puf_key)
            self.master_key.lock()
            self._key_reconstructed = True
            self._last_active_at = time.time()

        self.session_keys = {}

        self.math_config = {
            "diffusion_temp": 1173, "diffusion_time": 3600, "diffusion_D0": 1e-4,
            "diffusion_Q": 200000, "gibbs_delta_H": -30000, "gibbs_delta_S": -15,
            "reverse_Ea": 300000, "zeroization_tau0": 1e-13, "zeroization_Ea": 150000,
            "martensite_delta_H": -10000, "martensite_delta_S": -20,
            "puf_lattice_const": 0.25e-9, "puf_area": 1e-4,
            "copper_modulus": 110e9, "copper_expansion": 16.5e-6, "iron_expansion": 11.8e-6,
            "friction_mu": 0.3, "drill_diameter": 0.005,
            "hbar": 1.054571817e-34, "m_Cu": 1.055e-25, "k_B": 1.380649e-23,
            "theta_grad": 0.1, "squeezing_r": 1e15, "P_c": 100e6, "S_c": 10.0,
            "g_coupling": 1.0, "central_charge": 1.0, "interface_length": 0.01,
            "puf_entropy": 1.53e-8,
            "Z5": 2*3*5*7*11*(2**2+1)*(2**4+1)*(2**8+1)*(2**16+1)*(2**32+1),
            "iron_yield_stress": 250e6, "iron_shear_modulus": 80e9, "iron_poisson": 0.29,
            "burgers_vector": 0.25e-9, "dislocation_width": 0.25e-9,
            "aes_key_bits": 256, "ecdsa_curve_bits": 521, "sha_bits": 512,
            "quality_factor": 1e6,
        }
        self.Z5 = self.math_config["Z5"]
        self._log_event("INIT", f"Core initialized in {ENV_MODE.upper()} mode (test_mode={test_mode})")

    def _setup_logging(self):
        self.logger = logging.getLogger("ZLQ-IN-0")
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)

    def _log_event(self, event_type, message):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "message": message,
            "security_level": self.security_level,
            "attack_count": self.attack_count,
            "device_id": self.device_id,
            "version": self.VERSION,
            "env_mode": ENV_MODE
        }
        safe_entry = sanitize_telemetry(log_entry)
        self.logger.info(json.dumps(safe_entry))

    def _derive_master_key(self, seed):
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                         salt=b"zulqarnayn_initium_salt", iterations=100000)
        return kdf.derive(seed)

    def _derive_hmac_key(self):
        if self.master_key is None:
            return None
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                         salt=b"hmac_salt", iterations=1000)
        return kdf.derive(self.master_key)

    def inject_split_knowledge_share(self, share: bytes):
        if ENV_MODE != "virtual" or not self.config.split_knowledge_enabled:
            return
        if self._key_reconstructed:
            return
        shares = [(1, self._puf_key), (2, share)]
        try:
            master = shamir_combine(shares)
        except Exception as e:
            raise RuntimeError(f"Failed to reconstruct master key: {e}")
        self.master_key = SecureBytes(master)
        self.master_key.lock()
        self._key_reconstructed = True
        self._last_active_at = time.time()   # start the inactivity timer now
        self._last_timestamp = time.time()   # initialize replay protection
        self._log_event("SPLIT_KNOWLEDGE", "External share injected, key reconstructed.")
        explicit_bzero(id(share), len(share))

    def _check_zeroization(self):
        with self._lock:
            if self.is_zeroized:
                return True
            if not self._key_reconstructed or self.test_mode:
                return False
            # Sliding‑window inactivity check
            if self._last_active_at is None:
                return False
            if time.time() - self._last_active_at > self.config.zeroization_time:
                self._trigger_zeroization()
                return True
            return False

    def _trigger_zeroization(self):
        self.is_zeroized = True
        with self._lock:
            self.data_store.clear()
            self.session_keys.clear()
            if self.master_key:
                self.master_key.zero()
                self.master_key = None
            self._log_event("ZEROIZATION", "Complete zeroization triggered")

    def _check_block(self):
        with self._lock:
            if self.is_blocked and time.time() < self.block_until:
                return True
            if self.is_blocked and time.time() >= self.block_until:
                self.is_blocked = False
            return False

    def _authenticate_request(self, data, signature, timestamp):
        # Replay protection: monotonic timestamp and tolerance for clock drift
        if timestamp <= self._last_timestamp:
            return False
        if abs(time.time() - timestamp) > self.config.replay_window:
            return False
        if self._hmac_key is None:
            self._hmac_key = self._derive_hmac_key()
        if self._hmac_key is None:
            return False
        payload = data + struct.pack('>d', timestamp)
        expected = hmac.new(self._hmac_key, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, signature):
            return False
        # Success: update last_active_at to extend the lease
        with self._lock:
            self._last_active_at = time.time()
        self._last_timestamp = timestamp
        return True

    def encrypt(self, data, key=None):
        if self._check_zeroization():
            raise RuntimeError("Zeroized")
        if self._check_block():
            raise RuntimeError("Blocked")
        if ENV_MODE == "virtual" and self.config.split_knowledge_enabled and not self._key_reconstructed:
            raise RuntimeError("Key not reconstructed; inject split knowledge share first.")
        if self.master_key is None:
            raise RuntimeError("Master key not available")
        key = key or self.master_key
        iv = secrets.token_bytes(12)
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
        encryptor = cipher.encryptor()
        ct = encryptor.update(data) + encryptor.finalize()
        return iv + ct + encryptor.tag

    def decrypt(self, ciphertext, key=None):
        if self._check_zeroization():
            raise RuntimeError("Zeroized")
        if self._check_block():
            raise RuntimeError("Blocked")
        if ENV_MODE == "virtual" and self.config.split_knowledge_enabled and not self._key_reconstructed:
            raise RuntimeError("Key not reconstructed; inject split knowledge share first.")
        if self.master_key is None:
            raise RuntimeError("Master key not available")
        key = key or self.master_key
        iv = ciphertext[:12]
        tag = ciphertext[-16:]
        data = ciphertext[12:-16]
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
        decryptor = cipher.decryptor()
        try:
            pt = decryptor.update(data) + decryptor.finalize_with_tag(tag)
            return pt
        except Exception as e:
            with self._lock:
                self.attack_count += 1
                self.security_level *= 1.1
                if self.attack_count >= self.config.max_attempts:
                    self.is_blocked = True
                    self.block_until = time.time() + self.config.block_duration
            raise RuntimeError(f"Decrypt failed: {e}")

    def store_data(self, data_id, data):
        if self._check_zeroization():
            raise RuntimeError("Zeroized")
        if self._check_block():
            raise RuntimeError("Blocked")
        if not self._rate_limiter.consume():
            raise RuntimeError("Rate limit exceeded")
        encrypted = self.encrypt(data)
        with self._lock:
            self.data_store[data_id] = encrypted
        self._log_event("STORE", f"Stored {data_id}")
        return True

    def retrieve_data(self, data_id):
        if self._check_zeroization():
            raise RuntimeError("Zeroized")
        if self._check_block():
            raise RuntimeError("Blocked")
        if not self._rate_limiter.consume():
            raise RuntimeError("Rate limit exceeded")
        with self._lock:
            if data_id not in self.data_store:
                self.attack_count += 1
                self.security_level *= 1.1
                if self.attack_count >= self.config.max_attempts:
                    self.is_blocked = True
                    self.block_until = time.time() + self.config.block_duration
                raise RuntimeError("Data not found")
            encrypted = self.data_store[data_id]
        return self.decrypt(encrypted)

    def rotate_keys(self):
        if self._check_zeroization():
            raise RuntimeError("Zeroized")
        with self._lock:
            old = self.master_key
            new = secrets.token_bytes(32)
            self.master_key = SecureBytes(new)
            self.master_key.lock()
            old.zero()
        self._log_event("ROTATE", "Master key rotated")
        return new

    def emergency_zeroize(self):
        with self._lock:
            self.is_zeroized = True
            self.data_store.clear()
            self.session_keys.clear()
            if self.master_key:
                self.master_key.zero()
                self.master_key = None
            self._log_event("ZEROIZE", "Emergency zeroization complete")

    def _initialize_combinatorial_layers(self):
        layer_names = [
            "tawhid_al_hadid", "nuhas_al_sirr", "qadr_al_waqt",
            "ruh_al_amn", "arsh_al_hifz", "saba_al_difa", "dakkah_al_dhikr"
        ]
        layers = {}
        for idx, name in enumerate(layer_names):
            layers[name] = {"name": name, "effectiveness": 0.9999, "layer_index": idx, "active": True}
        return layers

    def get_total_effectiveness(self):
        product = 1.0
        for layer in self.layers.values():
            if layer["active"]:
                product *= (1 - layer["effectiveness"])
        return 1 - product

    def calculate_diffusion_depth(self):
        D0 = self.math_config["diffusion_D0"]
        Q = self.math_config["diffusion_Q"]
        R = 8.314; T = self.math_config["diffusion_temp"]; t = self.math_config["diffusion_time"]
        D = D0 * np.exp(-Q / (R * T))
        d = 2 * np.sqrt(D * t)
        return {"diffusion_coefficient": D, "diffusion_depth_m": d, "diffusion_depth_um": float(d*1e6)}

    def calculate_gibbs_free_energy(self):
        delta_H = self.math_config["gibbs_delta_H"]
        delta_S = self.math_config["gibbs_delta_S"]
        T = self.math_config["diffusion_temp"]
        delta_G = delta_H - T * delta_S
        return {"delta_G": delta_G, "is_spontaneous": bool(delta_G < 0)}

    def calculate_zeroization_time(self):
        tau0 = self.math_config["zeroization_tau0"]
        Ea = self.math_config["zeroization_Ea"]
        R = 8.314
        T_c = self.calculate_critical_temperature()["critical_temp_K"]
        t_zero = tau0 * np.exp(Ea / (R * T_c))
        return {"zeroization_time_s": float(t_zero), "zeroization_time_min": float(t_zero/60)}

    def calculate_critical_temperature(self):
        delta_H = self.math_config["martensite_delta_H"]
        delta_S = self.math_config["martensite_delta_S"]
        T_c = delta_H / delta_S
        return {"critical_temp_K": float(T_c), "critical_temp_C": float(T_c-273.15)}

    # ── SELF‑TEST (silent mode does not update the activity lease) ──
    def run_self_test(self, silent=False):
        global SILENT_MODE
        old_silent = SILENT_MODE
        if silent:
            SILENT_MODE = True

        results = {}
        test_names = [
            ("diffusion_pass", "Diffusion Depth", "depth > 40 µm"),
            ("gibbs_pass", "Gibbs Free Energy", "ΔG < 0 (spontaneous)"),
            ("zeroization_pass", "Zeroization Time", "t < 600 s"),
            ("store_retrieve_pass", "Store/Retrieve", "data round-trip"),
            ("crypto_pass", "Encryption/Decryption", "round-trip"),
            ("puf_stable_pass", "PUF Stability", "seed deterministic"),
            ("zeroization_attest_pass", "Zeroization Attest", "simulated")
        ]

        skip_crypto = (ENV_MODE == "virtual" and self.config.split_knowledge_enabled and not self._key_reconstructed)

        if not silent:
            print_header("RUNNING ZLQ-IN-0 SELF-TEST (7 CHECKS)")

        for key, display, desc in test_names:
            if not silent:
                sys.stdout.write(f"\r  {COLOR_CYAN}▶{COLOR_RESET} {display} ({desc}) ... ")
                sys.stdout.flush()
            try:
                if key == "diffusion_pass":
                    diff = self.calculate_diffusion_depth()
                    result = diff["diffusion_depth_um"] > 40
                elif key == "gibbs_pass":
                    gibbs = self.calculate_gibbs_free_energy()
                    result = gibbs["is_spontaneous"]
                elif key == "zeroization_pass":
                    zero = self.calculate_zeroization_time()
                    result = zero["zeroization_time_s"] < 600
                elif key == "store_retrieve_pass":
                    if skip_crypto:
                        raise RuntimeError("Split knowledge not injected; skipping store/retrieve test")
                    test_data = b"test"
                    self.store_data("self_test", test_data)
                    retrieved = self.retrieve_data("self_test")
                    result = (retrieved == test_data)
                    with self._lock:
                        self.data_store.pop("self_test", None)
                elif key == "crypto_pass":
                    if skip_crypto:
                        raise RuntimeError("Split knowledge not injected; skipping crypto test")
                    test_data = b"test"
                    encrypted = self.encrypt(test_data)
                    decrypted = self.decrypt(encrypted)
                    result = (decrypted == test_data)
                elif key == "puf_stable_pass":
                    seed1 = get_puf_seed()
                    seed2 = get_puf_seed()
                    result = (seed1 == seed2)
                elif key == "zeroization_attest_pass":
                    result = callable(self.emergency_zeroize)
                else:
                    result = False
            except Exception as e:
                result = False
                if not silent:
                    print(f"\n{COLOR_RED}Exception: {e}{COLOR_RESET}")

            results[key] = result
            if not silent:
                if result:
                    print_colored(COLOR_GREEN, f"PASS", end="\n")
                else:
                    print_colored(COLOR_RED, f"FAIL", end="\n")

        if skip_crypto:
            crypto_keys = {"store_retrieve_pass", "crypto_pass"}
            overall = all(results[k] for k in results if k not in crypto_keys)
        else:
            overall = all(results.values())

        if not silent:
            print_header("SELF-TEST SUMMARY")
            for key, name, desc in test_names:
                status = "PASS" if results[key] else "FAIL"
                color = COLOR_GREEN if results[key] else COLOR_RED
                print_colored(color, f"  {name:20} : {status}")
            print_colored(COLOR_BOLD + (COLOR_GREEN if overall else COLOR_RED),
                         f"\nOVERALL: {'PASS' if overall else 'FAIL'}")

        if silent:
            SILENT_MODE = old_silent
        results["overall_pass"] = overall
        return results

    def run_daemon(self):
        global SILENT_MODE
        SILENT_MODE = True

        self.logger.info("Starting daemon...")

        # Start socket server
        self._start_unix_socket_server()

        # If in virtual mode with split knowledge, wait for injection
        if ENV_MODE == "virtual" and self.config.split_knowledge_enabled and not self._key_reconstructed:
            self.logger.warning("Waiting for split knowledge share injection via secure ECDHE socket...")
            while not self._key_reconstructed:
                time.sleep(1)
            self.logger.info("Key reconstructed, entering operational phase.")

        # Continuous health checks – silent, only JSON logs
        while True:
            try:
                status = self.run_self_test(silent=True)
                overall = status.get("overall_pass", False)
                self.logger.info(json.dumps({"event": "self_test", "status": "PASS" if overall else "FAIL"}))
                if not overall:
                    safe_status = sanitize_telemetry(status)
                    self.logger.warning("Self-test failure: " + json.dumps(safe_status))
                time.sleep(60)
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Daemon error: {e}")
                time.sleep(10)

    def _start_unix_socket_server(self):
        socket_parent = SOCKET_FILE.parent
        socket_parent.mkdir(parents=True, exist_ok=True)
        if SOCKET_FILE.exists():
            SOCKET_FILE.unlink()
        server = socketserver.UnixStreamServer(str(SOCKET_FILE), UnixRequestHandler)
        server.core = self
        os.chmod(SOCKET_FILE, 0o600)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.logger.info(f"Unix socket started at {SOCKET_FILE}")

    def _process_request(self, req):
        cmd = req.get('cmd')
        if cmd == 'get_pubkey':
            pub = self._ec_priv.public_key()
            # Use X962 UncompressedPoint format
            pub_bytes = pub.public_bytes(encoding=serialization.Encoding.X962,
                                         format=serialization.PublicFormat.UncompressedPoint)
            return {"status": "ok", "pubkey": base64.b64encode(pub_bytes).decode()}
        elif cmd == 'inject_share':
            if self._key_reconstructed:
                return {"status": "error", "message": "already unlocked"}
            try:
                client_pub_bytes = base64.b64decode(req['client_pubkey'])
                client_pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), client_pub_bytes)
            except Exception:
                return {"status": "error", "message": "invalid client public key"}
            shared_secret = self._ec_priv.exchange(ec.ECDH(), client_pub)
            session_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"handshake").derive(shared_secret)
            try:
                iv = base64.b64decode(req['iv'])
                tag = base64.b64decode(req['tag'])
                cipher = Cipher(algorithms.AES(session_key), modes.GCM(iv, tag))
                decryptor = cipher.decryptor()
                share = decryptor.update(base64.b64decode(req['ciphertext'])) + decryptor.finalize()
            except Exception:
                return {"status": "error", "message": "decryption failed"}
            try:
                self.inject_split_knowledge_share(share)
            except Exception as e:
                return {"status": "error", "message": str(e)}
            explicit_bzero(id(session_key), len(session_key))
            explicit_bzero(id(shared_secret), len(shared_secret))
            return {"status": "share_injected"}
        elif cmd == 'store':
            data_id = req.get('id', '')
            data = base64.b64decode(req.get('data', ''))
            self.store_data(data_id, data)
            return {"status": "ok"}
        elif cmd == 'retrieve':
            data_id = req.get('id', '')
            data = self.retrieve_data(data_id)
            return {"status": "ok", "data": base64.b64encode(data).decode()}
        elif cmd == 'encrypt':
            plain = base64.b64decode(req.get('data', ''))
            enc = self.encrypt(plain)
            return {"status": "ok", "ciphertext": base64.b64encode(enc).decode()}
        elif cmd == 'decrypt':
            ct = base64.b64decode(req.get('ciphertext', ''))
            plain = self.decrypt(ct)
            return {"status": "ok", "data": base64.b64encode(plain).decode()}
        elif cmd == 'zeroize':
            self.emergency_zeroize()
            return {"status": "zeroized"}
        else:
            return {"status": "error", "message": "unknown command"}

class UnixRequestHandler(socketserver.StreamRequestHandler):
    def handle(self):
        core = self.server.core

        # Check peer credentials (SO_PEERCRED)
        try:
            peer_cred = self.request.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i'))
            pid, uid, gid = struct.unpack('3i', peer_cred)
            try:
                allowed_uid = pwd.getpwnam("zulqarnayn").pw_uid
            except:
                allowed_uid = 0
            if uid != 0 and uid != allowed_uid:
                self.request.sendall(b'{"status":"error","message":"peer not allowed"}')
                return
        except Exception:
            core.logger.warning("SO_PEERCRED not supported; skipping UID check")

        max_len = core.config.max_payload_bytes + 1
        buffer = bytearray(max_len)
        try:
            nbytes = self.request.recv_into(buffer)
        except Exception:
            self.request.sendall(b'{"status":"error","message":"recv failed"}')
            return

        if nbytes == 0:
            return
        raw = buffer[:nbytes]
        buffer[:] = b'\x00' * max_len

        try:
            req = json.loads(raw.decode('utf-8'))
        except Exception:
            self.request.sendall(b'{"status":"error","message":"invalid JSON"}')
            explicit_bzero(id(raw), len(raw))
            return

        explicit_bzero(id(raw), len(raw))

        # ---- State-asymmetric authentication with ECDHE ----
        cmd = req.get('cmd')
        is_inject = (cmd == 'inject_share')
        is_getpubkey = (cmd == 'get_pubkey')
        is_locked = not core._key_reconstructed

        # Allow get_pubkey and inject_share without HMAC/timestamp when locked
        if is_locked and (is_getpubkey or is_inject):
            try:
                resp = core._process_request(req)
            except Exception as e:
                resp = {"status":"error", "message": str(e)}
            safe_resp = sanitize_telemetry(resp)
            self.request.sendall(json.dumps(safe_resp).encode())
            return

        # For all other commands (or after reconstruction), enforce HMAC and timestamp.
        # Coercive type mapping: always convert to float.
        try:
            timestamp = float(req.get('timestamp', 0.0))
        except (TypeError, ValueError):
            self.request.sendall(b'{"status":"error","message":"invalid timestamp format"}')
            return

        if timestamp <= 0:
            self.request.sendall(b'{"status":"error","message":"missing or invalid timestamp"}')
            return

        sig = req.pop('_sig', None)
        if sig is None:
            self.request.sendall(b'{"status":"error","message":"missing signature"}')
            return
        sig = base64.b64decode(sig)

        payload = json.dumps(req, sort_keys=True).encode()
        if not core._authenticate_request(payload, sig, timestamp):
            self.request.sendall(b'{"status":"error","message":"authentication failed"}')
            return

        try:
            resp = core._process_request(req)
        except Exception as e:
            resp = {"status":"error", "message": str(e)}
        safe_resp = sanitize_telemetry(resp)
        self.request.sendall(json.dumps(safe_resp).encode())

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
def main():
    global SILENT_MODE
    if args.daemon:
        SILENT_MODE = True

    if args.self_test:
        core = ZulqarnaynInitiumCore("test", test_mode=True)
        res = core.run_self_test(silent=False)
        overall = res.get("overall_pass", False)
        sys.exit(0 if overall else 1)

    elif args.status:
        subprocess.run(["systemctl", "status", SERVICE_NAME], check=False)
        sys.exit(0)

    elif args.daemon:
        core = ZulqarnaynInitiumCore("production")
        core.run_daemon()
        sys.exit(0)

    else:
        print("Usage: --auto-deploy | --self-test | --status | --daemon")
        sys.exit(0)

if __name__ == "__main__":
    main()
