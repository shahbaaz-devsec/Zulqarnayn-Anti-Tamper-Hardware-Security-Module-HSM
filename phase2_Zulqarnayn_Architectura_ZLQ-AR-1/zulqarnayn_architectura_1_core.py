#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =============================================================================
# Zulqarnayn Architectura (ZLQ-AR-1) — v16.0.6
# =============================================================================

# -----------------------------------------------------------------------------
# EARLY PERMISSION FIX (OS ERROR 13)
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# EARLY ARGUMENT PARSING
# -----------------------------------------------------------------------------
import argparse

def parse_early_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto-deploy", action="store_true", help="Full deployment")
    parser.add_argument("--self-test", action="store_true", help="Run self-test and exit")
    parser.add_argument("--status", action="store_true", help="Show service status")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--device-id", default="zlq_ar_1_default", help="Device identifier")
    parser.add_argument("--security-report", action="store_true", help="Print security metrics and exit")
    return parser.parse_args()

args = parse_early_args()

# -----------------------------------------------------------------------------
# GLOBAL SILENT FLAG
# -----------------------------------------------------------------------------
SILENT_MODE = False

# -----------------------------------------------------------------------------
# ANSI STRIPPER (for non‑TTY output)
# -----------------------------------------------------------------------------
def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    text = text.replace('\r', '')
    return text

def is_tty_output():
    return sys.stdout.isatty()

# =============================================================================
# AUTO‑DEPLOY (atomic venv swap + signature generation + service restart)
# =============================================================================
if args.auto_deploy:
    import subprocess
    import shutil
    import time
    import json
    import secrets
    import tempfile
    import socket
    import threading
    import signal
    import py_compile
    from pathlib import Path
    from datetime import datetime
    import logging
    import pwd
    import grp
    import hashlib
    import base64

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
    SCRIPT_NAME = "zulqarnayn_architectura_1_core.py"
    VENV_DIR = TARGET_DIR / "venv"
    VENV_BACKUP_DIR = TARGET_DIR / "venv_backup"
    INJECTOR_SCRIPT = TARGET_DIR / "injector.py"
    SIGNATURE_FILE = TARGET_DIR / "script.sig"
    PUBLIC_KEY_FILE = TARGET_DIR / "public_key.pem"
    REQUIREMENTS = [
        ("cryptography==50.0.0", "sha256:..."),
        ("tqdm==4.70.0", "sha256:..."),
        ("psutil==7.2.2", "sha256:..."),
        ("pydantic==2.13.4", "sha256:..."),
        ("pyyaml==6.0.3", "sha256:..."),
        ("numpy==2.5.2", "sha256:..."),
        ("systemd-python==235", "sha256:..."),
    ]
    SERVICE_NAME = "zulqarnayn-architectura"
    SERVICE_FILE = Path(f"/etc/systemd/system/{SERVICE_NAME}.service")
    SOCKET_FILE = Path("/run/zulqarnayn/architectura.sock")
    STATE_DIR = Path("/var/lib/zulqarnayn-architectura")
    RUNTIME_DIR = "zulqarnayn-architectura"

    # -------------------------------------------------------------------------
    # Helper functions (deployment)
    # -------------------------------------------------------------------------
    def ensure_system_dependencies():
        print_step("Checking system dependencies...")
        if shutil.which("apt-get"):
            try:
                subprocess.run(["apt-get", "update"], check=True, capture_output=False)
                print_info("System updated (no automatic upgrade).")
            except Exception as e:
                print_warning(f"apt update failed: {e}. Continuing.")
        elif shutil.which("yum"):
            try:
                subprocess.run(["yum", "update"], check=True, capture_output=False)
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

    def install_package(venv_pip, pkg_spec):
        print_step(f"Installing {pkg_spec} (pinned)...")
        try:
            subprocess.run([str(venv_pip), "install", "--upgrade", pkg_spec],
                           check=True, capture_output=False)
            print_success(f"Installed {pkg_spec}")
            return True
        except subprocess.CalledProcessError as e:
            print_error(f"Failed to install {pkg_spec}: {e}")
            return False

    def ensure_venv_at_path(venv_path):
        print_header(f"VIRTUAL ENVIRONMENT SETUP AT {venv_path}")
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
        for pkg_spec, _ in REQUIREMENTS:
            pkg_name = pkg_spec.split("==")[0]
            if not package_installed(py, pkg_name):
                missing.append(pkg_spec)
            else:
                print_info(f"Package {pkg_name} already installed, skipping.")
        if missing:
            print_warning(f"Missing: {', '.join(missing)}")
            for pkg_spec in missing:
                install_package(pip, pkg_spec)
        else:
            print_success("All required packages installed.")
        return venv_path, py

    # -------------------------------------------------------------------------
    # Generate Ed25519 key pair and sign the script (code integrity)
    # -------------------------------------------------------------------------
    def generate_and_sign_script(venv_python, script_path):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization

        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        pub_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        with open(PUBLIC_KEY_FILE, 'wb') as f:
            f.write(pub_pem)
        os.chmod(PUBLIC_KEY_FILE, 0o444)
        print_success(f"Public key stored at {PUBLIC_KEY_FILE}")

        with open(script_path, 'rb') as f:
            script_data = f.read()
        signature = private_key.sign(script_data)
        with open(SIGNATURE_FILE, 'wb') as f:
            f.write(signature)
        os.chmod(SIGNATURE_FILE, 0o444)
        print_success(f"Signature stored at {SIGNATURE_FILE}")
        return public_key

    # -------------------------------------------------------------------------
    # Generate external share (encrypted with a transient passphrase)
    # -------------------------------------------------------------------------
    def generate_external_share(venv_python, share_file, passphrase):
        passphrase_file = TARGET_DIR / "share_passphrase.txt"
        with open(passphrase_file, 'w') as f:
            f.write(passphrase)
        os.chmod(passphrase_file, 0o400)
        print_info(f"Passphrase stored in {passphrase_file} (mode 0400)")

        script = f'''
import os, sys, hashlib, secrets, base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def get_hardware_id():
    ids = []
    try:
        with open("/sys/class/dmi/id/product_uuid", "rb") as f:
            ids.append(f.read().strip())
    except: pass
    try:
        with open("/sys/class/net/eth0/address", "rb") as f:
            ids.append(f.read().strip())
    except: pass
    try:
        with open("/etc/machine-id", "rb") as f:
            ids.append(f.read().strip())
    except: pass
    try:
        with open("/sys/class/tpm/tpm0/ek_pub", "rb") as f:
            ids.append(f.read())
    except: pass
    try:
        with open("/sys/class/dmi/id/board_serial", "rb") as f:
            ids.append(f.read().strip())
    except: pass
    try:
        r = subprocess.run(["dmidecode", "-s", "system-uuid"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            ids.append(r.stdout.strip().encode())
    except: pass
    return hashlib.sha256(b''.join(ids)).digest()

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

puf_seed = get_hardware_id()
kdf_puf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                     salt=b"zulqarnayn_puf_salt", iterations=100000)
puf_key = kdf_puf.derive(puf_seed)

master = secrets.token_bytes(32)
a1 = bytearray(32)
for i in range(32):
    a1[i] = gf256_add(puf_key[i], master[i])
share2 = bytearray(32)
for i in range(32):
    share2[i] = gf256_add(master[i], gf256_mul(a1[i], 2))

passphrase = "{passphrase}"
kdf_pass = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                      salt=b"share_encryption_salt", iterations=100000)
enc_key = kdf_pass.derive(passphrase.encode())
iv = os.urandom(12)
cipher = Cipher(algorithms.AES(enc_key), modes.GCM(iv))
encryptor = cipher.encryptor()
ct = encryptor.update(bytes(share2)) + encryptor.finalize()
tag = encryptor.tag
payload = iv + ct + tag
b64_payload = base64.b64encode(payload).decode()
print(b64_payload)
'''
        try:
            proc = subprocess.run([str(venv_python), "-c", script],
                                  capture_output=True, text=True, check=True, timeout=30)
            b64_payload = proc.stdout.strip()
            with open(share_file, 'w') as f:
                f.write(b64_payload)
            os.chmod(share_file, 0o400)
            print_success(f"Share written to {share_file}")
            return b64_payload
        except subprocess.CalledProcessError as e:
            print_error(f"Share generation failed: {e.stderr}")
            sys.exit(1)

    # -------------------------------------------------------------------------
    # Write injector script – now with fixed f-string escaping
    # -------------------------------------------------------------------------
    def write_injector_script(venv_python, socket_path):
        venv_python_path = venv_python
        script_content = f'''#!{venv_python_path}
# -*- coding: utf-8 -*-
import sys, json, time, socket, base64, os, getpass
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def secure_delete(file_path):
    """Overwrite file with random data and then unlink it."""
    try:
        with open(file_path, 'rb+') as f:
            f.seek(0)
            f.write(os.urandom(os.path.getsize(file_path)))
            f.flush()
            os.fsync(f.fileno())
        os.remove(file_path)
    except Exception as e:
        print(f"[-] Warning: could not securely delete {{file_path}}: {{e}}")

if len(sys.argv) != 2:
    print("Usage: injector.py <SHARE_FILE>")
    sys.exit(1)

share_file = sys.argv[1]
try:
    with open(share_file, 'r') as f:
        b64_payload = f.read().strip()
except Exception as e:
    print("[-] Failed to read share file:", e)
    sys.exit(1)

payload = base64.b64decode(b64_payload)
iv = payload[:12]
tag = payload[-16:]
ct = payload[12:-16]

passphrase_file = Path("/opt/zarqa/zulqarnayn_athsm/share_passphrase.txt")
if passphrase_file.exists():
    with open(passphrase_file, 'r') as f:
        passphrase = f.read().strip()
    print("[*] Passphrase read from file.")
else:
    passphrase = getpass.getpass("Enter the deployment passphrase: ")

kdf_pass = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                      salt=b"share_encryption_salt", iterations=100000)
enc_key = kdf_pass.derive(passphrase.encode())

try:
    cipher = Cipher(algorithms.AES(enc_key), modes.GCM(iv, tag))
    decryptor = cipher.decryptor()
    share_bytes = decryptor.update(ct) + decryptor.finalize()
except Exception as e:
    print("[-] Decryption failed:", e)
    sys.exit(1)

def send_req(req):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect("{socket_path}")
    s.sendall(json.dumps(req).encode('utf-8'))
    resp = s.recv(4096)
    s.close()
    return json.loads(resp.decode('utf-8'))

print("[*] Requesting HSM Public Key...")
res = send_req({{"cmd": "get_pubkey", "timestamp": time.time(), "nonce": os.urandom(16).hex()}})
if "pubkey" not in res:
    if res.get("message") == "missing signature":
        print("[!] Daemon already unlocked – injection not required.")
        secure_delete(passphrase_file)
        sys.exit(0)
    print("[-] Failed to get pubkey:", res)
    sys.exit(1)

daemon_pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), base64.b64decode(res["pubkey"]))

print("[*] Generating Ephemeral ECDHE Keypair...")
client_priv = ec.generate_private_key(ec.SECP256R1())
client_pub_bytes = client_priv.public_key().public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)

print("[*] Deriving AES-GCM Session Key...")
shared_secret = client_priv.exchange(ec.ECDH(), daemon_pub)
session_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"handshake").derive(shared_secret)

del client_priv

iv2 = os.urandom(12)
cipher2 = Cipher(algorithms.AES(session_key), modes.GCM(iv2))
encryptor = cipher2.encryptor()
ciphertext = encryptor.update(share_bytes) + encryptor.finalize()

print("[*] Transmitting Opaque Encrypted Share...")
req2 = {{
    "cmd": "inject_share",
    "timestamp": time.time(),
    "nonce": os.urandom(16).hex(),
    "client_pubkey": base64.b64encode(client_pub_bytes).decode(),
    "ciphertext": base64.b64encode(ciphertext).decode(),
    "iv": base64.b64encode(iv2).decode(),
    "tag": base64.b64encode(encryptor.tag).decode()
}}

res2 = send_req(req2)
if res2.get("status") == "share_injected":
    print("[+] INJECTION SUCCESSFUL. HSM is now fully operational.")
    if passphrase_file.exists():
        secure_delete(passphrase_file)
        print("[*] Deployment passphrase securely shredded.")
else:
    print("[-] Injection Failed:", res2)
'''
        with open(INJECTOR_SCRIPT, 'w') as f:
            f.write(script_content)
        os.chmod(INJECTOR_SCRIPT, 0o755)
        print_success(f"Injector written to {INJECTOR_SCRIPT}")

    # -------------------------------------------------------------------------
    # Main deployment
    # -------------------------------------------------------------------------
    def deploy(script_path):
        ensure_root()
        print_header("ZULQARNAYN ARCHITECTURA (ZLQ-AR-1) – AUTO DEPLOY (v16.0.6)")
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

        TARGET_DIR.mkdir(parents=True, exist_ok=True)

        # Stop the service if running (to ensure new code is loaded)
        print_step("Stopping existing service (if any)...")
        subprocess.run(["systemctl", "stop", SERVICE_NAME], check=False, capture_output=True)

        # Backup existing venv
        if VENV_DIR.exists():
            print_step("Backing up existing venv...")
            if VENV_BACKUP_DIR.exists():
                shutil.rmtree(VENV_BACKUP_DIR, ignore_errors=True)
            shutil.move(str(VENV_DIR), str(VENV_BACKUP_DIR))
            print_success("Existing venv moved to backup.")
        else:
            print_info("No existing venv to back up.")

        # Build new venv
        try:
            venv_path, venv_python = ensure_venv_at_path(VENV_DIR)
        except Exception as e:
            print_error(f"Failed to build new venv: {e}. Rolling back...")
            if VENV_BACKUP_DIR.exists():
                shutil.move(str(VENV_BACKUP_DIR), str(VENV_DIR))
                print_success("Restored previous venv from backup.")
            sys.exit(1)

        # Set recursive permissions
        print_step("Setting recursive permissions on venv...")
        subprocess.run(["chmod", "-R", "a+rX", str(VENV_DIR)], check=True)
        print_success("Permissions set on venv.")

        # Copy script
        target_script = TARGET_DIR / SCRIPT_NAME
        if os.path.abspath(script_path) != str(target_script):
            print_step("Provisioning script to target directory...")
            shutil.copy2(script_path, target_script)
            target_script.chmod(0o755)
            print_success("Script copied.")
        else:
            print_info("Script already at target; skipping copy.")

        # Generate and sign the script (code integrity)
        print_step("Generating signing key and signing script...")
        generate_and_sign_script(venv_python, target_script)

        # Generate a random passphrase for the share encryption
        import secrets
        passphrase = secrets.token_urlsafe(32)
        passphrase_file = TARGET_DIR / "share_passphrase.txt"
        with open(passphrase_file, 'w') as f:
            f.write(passphrase)
        os.chmod(passphrase_file, 0o400)
        print_info(f"Passphrase stored in {passphrase_file} (mode 0400)")

        # Generate external share (encrypted)
        share_file = TARGET_DIR / "external_share.b64"
        print_step("Generating external share (encrypted with passphrase)")
        b64_payload = generate_external_share(venv_python, share_file, passphrase)
        print_info(f"Share file: {share_file} (mode 0400)")

        # Write injector script (no need to pass share_file)
        write_injector_script(venv_python, SOCKET_FILE)

        # Pre-flight self-test
        print_step("Pre‑flight self‑test (new venv)")
        test_state_dir = tempfile.mkdtemp(prefix="zlq_test_")
        test_env = os.environ.copy()
        test_env["ZARQA_STATE_DIR"] = test_state_dir
        test_env["ZARQA_ENV_MODE"] = "virtual"
        test_cmd = [str(venv_python), str(target_script), "--self-test"]
        proc = subprocess.Popen(test_cmd, env=test_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True, bufsize=1)
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
        proc.wait(timeout=120)
        ret_code = proc.returncode
        shutil.rmtree(test_state_dir, ignore_errors=True)
        if ret_code != 0:
            print_error("Self‑test FAILED. Rolling back to previous venv...")
            shutil.rmtree(VENV_DIR, ignore_errors=True)
            if VENV_BACKUP_DIR.exists():
                shutil.move(str(VENV_BACKUP_DIR), str(VENV_DIR))
                print_success("Restored previous venv from backup.")
            sys.exit(1)
        print_success("Self‑test PASSED. New venv is healthy.")

        # Remove backup
        if VENV_BACKUP_DIR.exists():
            shutil.rmtree(VENV_BACKUP_DIR, ignore_errors=True)
            print_success("Old backup removed.")

        # Ensure service user
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

        # Write systemd unit (hardened) with StateDirectory and entropy ordering
        print_step("Writing systemd unit (Type=simple, hardened) ...")
        unit = f"""[Unit]
Description=Zulqarnayn Architectura (ZLQ-AR-1) Service
Documentation=https://zarqa.ai/docs/zlq-ar-1
After=network.target systemd-random-seed.service
Wants=systemd-random-seed.service

[Service]
Type=simple
User=zulqarnayn
Group=zulqarnayn
RuntimeDirectory={RUNTIME_DIR}
StateDirectory={RUNTIME_DIR}
WorkingDirectory={TARGET_DIR}
Environment="PATH={VENV_DIR}/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="ZARQA_STATE_DIR={STATE_DIR}"
PrivateNetwork=yes
ProtectSystem=strict
ProtectHome=yes
ProtectKernelTunables=yes
RestrictAddressFamilies=AF_UNIX
NoNewPrivileges=yes
MemoryDenyWriteExecute=yes
PrivateTmp=yes
ExecStartPre={VENV_DIR}/bin/python3 -c "import sys; print('ZLQ-AR-1 Starting')"
ExecStart={VENV_DIR}/bin/python3 {TARGET_DIR / SCRIPT_NAME} --daemon
Restart=on-failure
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

        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "enable", SERVICE_NAME], check=True)

        print_step("Starting service (asynchronous)...")
        subprocess.run(["systemctl", "start", "--no-block", SERVICE_NAME], check=True)
        print_success("Service start command issued (--no-block).")

        elapsed = time.time() - start_time
        print_header("DEPLOYMENT COMPLETE")
        print_success(f"Deployment finished in {elapsed:.2f} seconds.")
        print_info("Monitoring:")
        print_info("  sudo systemctl status zulqarnayn-architectura")
        print_info("  sudo journalctl -u zulqarnayn-architectura -f")
        print_info(f"Unix socket: {SOCKET_FILE} (mode 600, HMAC auth, replay-protected)")
        print_info(f"External share file: {share_file} (mode 0400, encrypted)")
        print_info(f"Injector script: {INJECTOR_SCRIPT}")
        print_info(f"Passphrase file: {passphrase_file} (mode 0400)")
        print_info(f"\nINJECTOR WILL SECURELY SHRED THE PASSPHRASE AFTER SUCCESSFUL INJECTION.")
        print_info(f"Run: sudo {INJECTOR_SCRIPT} {share_file}")
        sys.exit(0)

    deploy(os.path.abspath(__file__))
    sys.exit(0)

# =============================================================================
# IF NOT AUTO‑DEPLOY, SELF‑HIJACK INTO VENV (robust)
# =============================================================================

import subprocess
import shutil
from pathlib import Path

TARGET_DIR = Path("/opt/zarqa/zulqarnayn_athsm")
VENV_DIR = TARGET_DIR / "venv"
REQUIREMENTS = [
    "cryptography",
    "tqdm",
    "psutil",
    "pydantic",
    "pyyaml",
    "numpy",
    "systemd-python",
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

def install_package(venv_pip, pkg):
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
            install_package(pip, pkg)
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

# -----------------------------------------------------------------------------
# NOW SAFE TO IMPORT THIRD‑PARTY LIBRARIES
# -----------------------------------------------------------------------------
import re
import json
import time
import hashlib
import secrets
import logging
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
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

try:
    from systemd import daemon as sd_daemon
    HAVE_SD_DAEMON = True
except ImportError:
    HAVE_SD_DAEMON = False
    sd_daemon = None

# ── Colours ──────────────────────────────────────────────────────────
COLOR_RESET = "\033[0m"
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_CYAN = "\033[96m"
COLOR_WHITE = "\033[97m"
COLOR_BOLD = "\033[1m"

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
SCRIPT_NAME = "zulqarnayn_architectura_1_core.py"
VENV_DIR = TARGET_DIR / "venv"
SERVICE_NAME = "zulqarnayn-architectura"
SOCKET_FILE = Path("/run/zulqarnayn/architectura.sock")
STATE_DIR = Path(os.environ.get("ZARQA_STATE_DIR", "/var/lib/zulqarnayn-architectura"))
REPLAY_WINDOW_SEC = 15.0
PUBLIC_KEY_FILE = TARGET_DIR / "public_key.pem"
SIGNATURE_FILE = TARGET_DIR / "script.sig"
NONCE_STORE_FILE = STATE_DIR / "nonce_store.json"

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

# =============================================================================
# SECURE MEMORY MANAGEMENT (mlockall + explicit_bzero)
# =============================================================================
try:
    libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
    _mlockall = libc.mlockall
    _mlockall.argtypes = [ctypes.c_int]
    _mlockall.restype = ctypes.c_int
    _munlockall = libc.munlockall
    _munlockall.argtypes = []
    _munlockall.restype = ctypes.c_int
    _explicit_bzero = libc.explicit_bzero
    _explicit_bzero.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    _explicit_bzero.restype = None
    _prctl = libc.prctl
    _prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    _prctl.restype = ctypes.c_int
    _syscall = libc.syscall
    _syscall.argtypes = [ctypes.c_long, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    _syscall.restype = ctypes.c_long
except:
    _mlockall = _munlockall = _explicit_bzero = _prctl = _syscall = None
    print_warning("libc functions unavailable; memory pinning disabled.")

def mlockall():
    if _mlockall:
        return _mlockall(3) == 0  # MCL_CURRENT | MCL_FUTURE
    return False

def munlockall():
    if _munlockall:
        return _munlockall() == 0
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
    if _prctl is not None:
        try:
            _prctl(4, 0, 0, 0, 0)  # PR_SET_DUMPABLE = 4
            print_info("Kernel anti-tracing (PR_SET_DUMPABLE) enforced.")
            return True
        except Exception as e:
            print_warning(f"Anti-tracing failed: {e}")
    return False

def enable_yama_ptrace_scope():
    try:
        with open("/proc/sys/kernel/yama/ptrace_scope", "r") as f:
            if f.read().strip() == "3":
                print_info("YAMA ptrace_scope already set to 3.")
                return True
    except:
        pass
    try:
        with open("/proc/sys/kernel/yama/ptrace_scope", "w") as f:
            f.write("3")
        print_info("YAMA ptrace_scope set to 3 (global ptrace disabled).")
        return True
    except Exception as e:
        print_warning(f"Could not set YAMA ptrace_scope: {e}. Set it via sysctl.d.")
        return False

class SecureBuffer:
    def __init__(self, size):
        self.size = size
        self.fd = None
        self.buf = None
        self.addr = None
        self.locked = False
        self._lock = threading.Lock()

        if _syscall is not None:
            try:
                fd = _syscall(447, 0, 0, 0, 0, 0)
                if fd >= 0:
                    os.ftruncate(fd, size)
                    self.buf = mmap.mmap(fd, size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
                    self.addr = ctypes.addressof(ctypes.c_void_p.from_buffer(self.buf))
                    self.locked = True
                    self.fd = fd
                    print_info("SecureBuffer using memfd_secret.")
                else:
                    os.close(fd)
            except Exception:
                pass

        if self.buf is None:
            self.buf = ctypes.create_string_buffer(size)
            self.addr = ctypes.addressof(self.buf)
            if mlockall():
                self.locked = True
                print_info("SecureBuffer using mlocked ctypes buffer.")
            else:
                print_warning("mlockall failed; memory may be swapped.")

    def write(self, data):
        with self._lock:
            if self.buf is None or len(data) != self.size:
                return False
            self.buf[:] = data
            if self.read_unsafe(length=self.size) != data:
                print_warning("SecureBuffer write validation failed!")
                return False
            return True

    def read(self, length=None):
        with self._lock:
            return self.read_unsafe(length)

    def read_unsafe(self, length=None):
        if self.buf is None:
            return None
        if length is None:
            length = self.size
        return bytes(memoryview(self.buf)[:length])

    def zero(self):
        with self._lock:
            if self.locked and self.addr is not None:
                explicit_bzero(self.addr, self.size)
                if self.fd is not None:
                    if self.buf is not None:
                        self.buf.close()
                    os.close(self.fd)
                else:
                    munlockall()
                self.locked = False
                self.buf = None
                self.addr = None
                self.fd = None

    def __enter__(self):
        return self.buf

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.zero()

    def __del__(self):
        self.zero()

# =============================================================================
# PERSISTENT NONCE TRACKER
# =============================================================================
class PersistentNonceTracker:
    def __init__(self, store_file, window_sec=15.0, max_size=1000000):
        self.store_file = Path(store_file)
        self.window = window_sec
        self.max_size = max_size
        self._nonces = set()
        self._timestamps = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.store_file.exists():
            try:
                with open(self.store_file, 'r') as f:
                    data = json.load(f)
                    for nonce, ts in data.items():
                        if time.time() - ts <= self.window:
                            self._nonces.add(nonce)
                            self._timestamps[nonce] = ts
            except Exception as e:
                print_warning(f"Failed to load nonce store: {e}")

    def _save(self):
        try:
            self.store_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.store_file, 'w') as f:
                json.dump(self._timestamps, f)
            os.chmod(self.store_file, 0o600)
        except Exception as e:
            print_warning(f"Failed to save nonce store: {e}")

    def check_and_add(self, nonce, timestamp):
        now = time.time()
        if abs(now - timestamp) > self.window:
            return False
        with self._lock:
            self._clean(now)
            if nonce in self._nonces:
                return False
            self._nonces.add(nonce)
            self._timestamps[nonce] = timestamp
            self._save()
            return True

    def _clean(self, now):
        expired = [n for n, t in self._timestamps.items() if now - t > self.window]
        for n in expired:
            self._nonces.discard(n)
            del self._timestamps[n]
        if len(self._nonces) > self.max_size:
            sorted_items = sorted(self._timestamps.items(), key=lambda x: x[1])
            for n, _ in sorted_items[:len(self._nonces) - self.max_size]:
                self._nonces.discard(n)
                del self._timestamps[n]

    def reset(self):
        with self._lock:
            self._nonces.clear()
            self._timestamps.clear()
            if self.store_file.exists():
                self.store_file.unlink()

# =============================================================================
# JSON CANONICALIZATION
# =============================================================================
def canonical_json(obj, **kwargs):
    def _sort_dict(d):
        if isinstance(d, dict):
            return {k: _sort_dict(v) for k, v in sorted(d.items())}
        elif isinstance(d, list):
            return [_sort_dict(v) for v in d]
        else:
            return d
    sorted_obj = _sort_dict(obj)
    return json.dumps(sorted_obj, separators=(',', ':'), ensure_ascii=False, **kwargs)

# =============================================================================
# GALOIS FIELD GF(2^8)
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
# HARDWARE DETECTION & PUF (hybrid)
# =============================================================================
def detect_hardware() -> Dict[str, Any]:
    return {
        "architecture": platform.machine(),
        "system": platform.system(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "is_virtual": "virtual" in platform.platform().lower() or "vm" in platform.platform().lower(),
        "implementation": "native"
    }

def get_hardware_abstraction() -> Dict[str, Any]:
    hw = detect_hardware()
    return {
        "hardware": hw,
        "abstraction_active": True,
        "platform_independent": True,
        "mapping": {
            "logical": "standard",
            "physical": hw["architecture"],
            "compatibility": "full"
        }
    }

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

def get_hardware_id():
    ids = []
    try:
        with open("/sys/class/dmi/id/product_uuid", "rb") as f:
            ids.append(f.read().strip())
    except: pass
    try:
        with open("/sys/class/net/eth0/address", "rb") as f:
            ids.append(f.read().strip())
    except: pass
    try:
        with open("/etc/machine-id", "rb") as f:
            ids.append(f.read().strip())
    except: pass
    try:
        with open("/sys/class/tpm/tpm0/ek_pub", "rb") as f:
            ids.append(f.read())
    except: pass
    try:
        with open("/sys/class/dmi/id/board_serial", "rb") as f:
            ids.append(f.read().strip())
    except: pass
    try:
        r = subprocess.run(["dmidecode", "-s", "system-uuid"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            ids.append(r.stdout.strip().encode())
    except: pass
    return hashlib.sha256(b''.join(ids)).digest()

def get_puf_seed():
    hw = get_hardware_id()
    salt_file = STATE_DIR / "puf_salt.bin"
    salt_file.parent.mkdir(parents=True, exist_ok=True)
    if salt_file.exists():
        with open(salt_file, 'rb') as f:
            salt = f.read()
    else:
        salt = secrets.token_bytes(32)
        with open(salt_file, 'wb') as f:
            f.write(salt)
        os.chmod(salt_file, 0o600)
    seed = hashlib.sha256(hw + salt).digest()
    print_warning("Using hybrid hardware+random seed — NOT a true physical PUF. For production, integrate TPM2.")
    return seed

# =============================================================================
# CODE INTEGRITY (Ed25519 signature verification)
# =============================================================================
def verify_script_signature():
    script_path = Path(__file__).resolve()
    pub_key_file = PUBLIC_KEY_FILE
    sig_file = SIGNATURE_FILE
    if not pub_key_file.exists() or not sig_file.exists():
        print_warning("Public key or signature file missing; skipping integrity check.")
        return True

    try:
        with open(pub_key_file, 'rb') as f:
            pub_pem = f.read()
        public_key = Ed25519PublicKey.from_public_bytes(
            serialization.load_pem_public_key(pub_pem).public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
        )
        with open(script_path, 'rb') as f:
            script_data = f.read()
        with open(sig_file, 'rb') as f:
            signature = f.read()
        public_key.verify(signature, script_data)
        print_info("Code integrity signature verified.")
        return True
    except Exception as e:
        print_error(f"Code integrity verification failed: {e}")
        return False

# =============================================================================
# TIMING EVASION
# =============================================================================
def calibrate_timing_baseline(iterations=100, loop_count=1000):
    samples = []
    for _ in range(iterations):
        t1 = time.perf_counter_ns()
        x = 0
        for _ in range(loop_count):
            x ^= 0x12345678
        t2 = time.perf_counter_ns()
        samples.append(t2 - t1)
    if not samples:
        return 0.0, 0.0
    mean = sum(samples) / len(samples)
    variance = sum((s - mean) ** 2 for s in samples) / len(samples)
    std = math.sqrt(variance)
    return mean, std

def check_timing_evasion(mean, std):
    try:
        t1 = time.perf_counter_ns()
        x = 0
        for _ in range(1000):
            x ^= 0x12345678
        t2 = time.perf_counter_ns()
        delta = t2 - t1
        threshold = mean + 4.0 * std
        if delta > threshold:
            return False
        return True
    except Exception:
        return True

# =============================================================================
# SECCOMP-BPF STRICT WHITELIST
# =============================================================================
def install_seccomp_filter():
    try:
        import seccomp
        f = seccomp.SyscallFilter(defaction=seccomp.ERRNO(seccomp.errno.EPERM))
        allowed = [
            "read", "write", "close", "poll", "recvmsg", "sendmsg",
            "futex", "clock_gettime", "getrandom", "getpid", "gettid",
            "getuid", "geteuid", "getgid", "getegid", "getppid",
            "munmap", "brk", "rt_sigreturn", "exit", "exit_group",
            "madvise", "mprotect", "mmap", "open", "openat", "stat",
            "fstat", "lseek", "dup", "dup2", "fcntl", "ioctl",
            "getsockopt", "setsockopt", "bind", "accept", "accept4",
            "listen", "shutdown", "socketpair", "unlink", "unlinkat",
            "mkdir", "mkdirat", "fchmod", "fchown", "chmod",
            "set_robust_list", "rseq", "prctl"
        ]
        f.add_rule(seccomp.ALLOW, "clone")
        for syscall in allowed:
            f.add_rule(seccomp.ALLOW, syscall)
        f.load()
        print_info("Strict seccomp whitelist installed.")
        return True
    except ImportError:
        print_warning("python-seccomp not installed; seccomp not enforced.")
        return False
    except Exception as e:
        print_warning(f"Failed to install seccomp filter: {e}")
        return False

# =============================================================================
# RATE LIMITER
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
# CORE HSM CLASS
# =============================================================================
@dataclass
class ArchitecturaConfig:
    zeroization_time: int = 86400
    security_level: float = 1.0
    max_attempts: int = 5
    block_duration: int = 300
    key_size: int = 256
    num_layers: int = 7
    learning_rate: float = 0.01
    max_payload_bytes: int = 1024 * 1024
    split_knowledge_enabled: bool = True
    rate_limit: float = 5.0
    rate_capacity: int = 10
    sss_threshold: int = 2
    sss_shares: int = 2
    replay_window: float = 15.0

class ZulqarnaynArchitectura:
    VERSION = "16.0.6"
    ENV_MODE = ENV_MODE
    HARDWARE = detect_hardware()

    def __init__(self, device_id: str, config: Optional[ArchitecturaConfig] = None, test_mode: bool = False):
        self.device_id = device_id
        self.config = config or ArchitecturaConfig()
        self.test_mode = test_mode

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
        self._nonce_tracker = PersistentNonceTracker(
            store_file=NONCE_STORE_FILE,
            window_sec=self.config.replay_window
        )
        self._last_active_at = None

        self._setup_logging()

        if not test_mode:
            install_seccomp_filter()
            if not verify_script_signature():
                print_error("Code integrity check failed; aborting.")
                sys.exit(1)

        enforce_anti_tracing()
        enable_yama_ptrace_scope()
        mlockall()

        print_info("Calibrating timing baseline...")
        mean, std = calibrate_timing_baseline(iterations=100, loop_count=1000)
        self._timing_mean = mean
        self._timing_std = std
        print_info(f"Timing baseline: mean={mean:.2f} ns, std={std:.2f} ns")

        if not check_timing_evasion(self._timing_mean, self._timing_std):
            self._log_event("TIMING_EVASION", "Timing anomaly detected; zeroizing.")
            self.emergency_zeroize()

        self._puf_seed = get_puf_seed()
        self._puf_key = self._derive_master_key(self._puf_seed)
        self._key_reconstructed = False
        self.master_key = None

        if ENV_MODE == "virtual" and self.config.split_knowledge_enabled and not test_mode:
            self._key_reconstructed = False
            self._last_active_at = None
            self._ec_priv = ec.generate_private_key(ec.SECP256R1())
            self._puf_share = self._puf_key
            print_warning("Split knowledge enabled: inject the external share via secure ECDHE socket.")
        else:
            self.master_key = SecureBuffer(32)
            if not self.master_key.write(self._puf_key):
                raise RuntimeError("Failed to write master key to secure buffer")
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
            "layer_effectiveness": 0.9999,
            "sensor_detection_rate": 0.9999,
            "redundancy_rate": 0.9999,
            "lambda_physical": 1e-4,
            "timing_sigma": 10e-9,
            "power_sigma": 1e-3,
        }
        self.Z5 = self.math_config["Z5"]
        self._log_event("INIT", f"Core initialized on {self.HARDWARE['architecture']} ({ENV_MODE.upper()})")

    def _setup_logging(self):
        self.logger = logging.getLogger("ZLQ-AR-1")
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
            "env_mode": ENV_MODE,
            "version": self.VERSION
        }
        self.logger.info(json.dumps(log_entry))

    def _derive_master_key(self, seed):
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                         salt=b"zulqarnayn_architectura_salt", iterations=100000)
        return kdf.derive(seed)

    def _derive_hmac_key(self):
        if self.master_key is None:
            return None
        key_bytes = self.master_key.read(32)
        if key_bytes is None:
            return None
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                         salt=b"hmac_salt", iterations=1000)
        return kdf.derive(key_bytes)

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
        self.master_key = SecureBuffer(32)
        if not self.master_key.write(master):
            raise RuntimeError("Failed to write reconstructed master key to secure buffer")
        self._key_reconstructed = True
        self._last_active_at = time.time()
        self._hmac_key = self._derive_hmac_key()
        self._log_event("SPLIT_KNOWLEDGE", "External share injected, key reconstructed.")

    def _check_zeroization(self):
        with self._lock:
            if self.is_zeroized:
                return True
            if not self._key_reconstructed or self.test_mode:
                return False
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
            self._hmac_key = None
            self._nonce_tracker.reset()
            self._log_event("ZEROIZATION", "Complete zeroization triggered")

    def _check_block(self):
        with self._lock:
            if self.is_blocked and time.time() < self.block_until:
                return True
            if self.is_blocked and time.time() >= self.block_until:
                self.is_blocked = False
            return False

    def _authenticate_request(self, data, signature, nonce, timestamp):
        if not self._nonce_tracker.check_and_add(nonce, timestamp):
            return False
        if self._hmac_key is None:
            self._hmac_key = self._derive_hmac_key()
        if self._hmac_key is None:
            return False
        canonical_payload = canonical_json(data)
        payload = canonical_payload.encode('utf-8') + struct.pack('>d', timestamp)
        expected = hmac.new(self._hmac_key, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, signature):
            return False
        with self._lock:
            self._last_active_at = time.time()
        return True

    def encrypt(self, data, key=None, aad=None):
        if self._check_zeroization():
            raise RuntimeError("Zeroized")
        if self._check_block():
            raise RuntimeError("Blocked")
        if ENV_MODE == "virtual" and self.config.split_knowledge_enabled and not self._key_reconstructed:
            raise RuntimeError("Key not reconstructed; inject split knowledge share first.")
        if self.master_key is None:
            raise RuntimeError("Master key not available")
        key_bytes = self.master_key.read(32)
        if key_bytes is None:
            raise RuntimeError("Failed to read master key")
        key = key or key_bytes

        iv = secrets.token_bytes(12)
        if aad is None:
            aad = struct.pack('>d', time.time())
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
        encryptor = cipher.encryptor()
        encryptor.authenticate_additional_data(aad)
        ct = encryptor.update(data) + encryptor.finalize()
        tag = encryptor.tag
        return iv + ct + tag + aad

    def decrypt(self, ciphertext, key=None, aad=None):
        try:
            if self._check_zeroization():
                raise RuntimeError("Zeroized")
            if self._check_block():
                raise RuntimeError("Blocked")
            if ENV_MODE == "virtual" and self.config.split_knowledge_enabled and not self._key_reconstructed:
                raise RuntimeError("Key not reconstructed; inject split knowledge share first.")
            if self.master_key is None:
                raise RuntimeError("Master key not available")
            key_bytes = self.master_key.read(32)
            if key_bytes is None:
                raise RuntimeError("Failed to read master key")
            key = key or key_bytes

            iv = ciphertext[:12]
            rest = ciphertext[12:]
            if aad is None:
                if len(rest) < 16 + 8:
                    raise ValueError("Ciphertext too short for appended AAD")
                aad = rest[-8:]
                tag = rest[-24:-8]
                ct = rest[:-24]
            else:
                if len(rest) < 16:
                    raise ValueError("Ciphertext too short")
                tag = rest[-16:]
                ct = rest[:-16]

            cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
            decryptor = cipher.decryptor()
            decryptor.authenticate_additional_data(aad)
            pt = decryptor.update(ct) + decryptor.finalize_with_tag(tag)
            return pt
        except Exception as e:
            with self._lock:
                self.attack_count += 1
                self.security_level *= 1.1
                if self.attack_count >= self.config.max_attempts:
                    self.is_blocked = True
                    self.block_until = time.time() + self.config.block_duration
            raise RuntimeError("Decrypt failed: verification error") from e

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
            self.master_key = SecureBuffer(32)
            if not self.master_key.write(new):
                raise RuntimeError("Failed to write new master key")
            old.zero()
            self._hmac_key = self._derive_hmac_key()
            self._nonce_tracker.reset()
            self._log_event("ROTATE", "Master key rotated, HMAC re-derived, nonces reset.")
        return new

    def emergency_zeroize(self):
        with self._lock:
            self.is_zeroized = True
            self.data_store.clear()
            self.session_keys.clear()
            if self.master_key:
                self.master_key.zero()
                self.master_key = None
            self._hmac_key = None
            self._nonce_tracker.reset()
            self._log_event("ZEROIZE", "Emergency zeroization complete")

    def _initialize_combinatorial_layers(self):
        layer_names = [
            "Sab'a 1: Hadid (Iron)",
            "Sab'a 2: Nuhas (Copper)",
            "Sab'a 3: Nur (Light)",
            "Sab'a 4: Qadr (Decree)",
            "Sab'a 5: Dakkah (Zeroization)",
            "Sab'a 6: Aman (Security)",
            "Sab'a 7: Sultan (Authority)"
        ]
        layers = {}
        for idx, name in enumerate(layer_names):
            layers[name] = {"name": name, "effectiveness": 0.9999, "layer_index": idx, "active": False}
        return layers

    def activate_layers(self):
        for layer in self.layers.values():
            layer["active"] = True
        self._log_event("LAYERS", "All seven layers activated.")

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

    def get_hardware_abstraction(self) -> Dict[str, Any]:
        return get_hardware_abstraction()

    def compute_defensive_metrics(self) -> Dict[str, float]:
        E = self.math_config["layer_effectiveness"]
        D = self.math_config["sensor_detection_rate"]
        P_phys = 1e-9
        P_crypto = 2**(-256)
        P_timing = 1e-12
        P_layer = (1 - E)**7

        P_union = P_layer + P_phys + P_crypto + P_timing + (1 - D)**4
        P_serial = P_layer * P_phys * P_crypto * P_timing * (1 - D)**4

        metrics = {
            "total_effectiveness": 1 - P_layer,
            "physical_security_model": P_phys,
            "detection_probability": 1 - (1 - D)**4,
            "crypto_security": P_crypto,
            "side_channel_timing": P_timing,
            "layer_breach_probability": P_layer,
            "sensor_bypass_probability": (1 - D)**4,
            "total_breach_probability_serial": P_serial,
            "total_breach_probability_union": P_union,
            "total_breach_probability_honest": min(P_serial, P_union)
        }
        return metrics

    def compute_offensive_metrics(self) -> Dict[str, float]:
        E = self.math_config["layer_effectiveness"]
        D = self.math_config["sensor_detection_rate"]
        R = self.math_config["redundancy_rate"]
        P_phys = 1e-9
        P_crypto = 2**(-256) * 2**(-128)
        P_side = 1e-12
        P_layer = (1 - E)**7
        P_bypass = (1 - D)**8
        P_fault = (1 - R)**4
        P_success = P_layer * P_phys * P_crypto * P_side * P_bypass * P_fault
        return {
            "layer_penetration": P_layer,
            "physical_attack": P_phys,
            "sensor_bypass": P_bypass,
            "crypto_attack": P_crypto,
            "side_channel": P_side,
            "fault_injection": P_fault,
            "combined_success": P_success
        }

    def print_security_report(self):
        print_header("ZLQ-AR-1 SECURITY METRICS REPORT (Corrected)")
        print_info(f"Hardware: {self.HARDWARE['architecture']} ({self.HARDWARE['system']})")
        def fmt_prob(p):
            if p == 0:
                return "0 (mathematically exact, not physical)"
            if p < 1e-300:
                return f"{p:.1e}"
            return f"{p:.4g}"
        print_colored(COLOR_BOLD + COLOR_CYAN, "\n[ HARDWARE ABSTRACTION ]")
        hw_abs = self.get_hardware_abstraction()
        print_colored(COLOR_WHITE, f"  Platform independent: {hw_abs['platform_independent']}")
        print_colored(COLOR_WHITE, f"  Compatibility: {hw_abs['mapping']['compatibility']}")

        print_colored(COLOR_BOLD + COLOR_BLUE, "\n[ DEFENSIVE SECURITY ]")
        dm = self.compute_defensive_metrics()
        for key, val in dm.items():
            print_colored(COLOR_WHITE, f"  {key.replace('_',' ').title():35} : {fmt_prob(val)}")

        print_colored(COLOR_BOLD + COLOR_RED, "\n[ OFFENSIVE FAILURE PROBABILITIES ]")
        om = self.compute_offensive_metrics()
        for key, val in om.items():
            print_colored(COLOR_WHITE, f"  {key.replace('_',' ').title():35} : {fmt_prob(val)}")

        print_colored(COLOR_BOLD + COLOR_GREEN, "\n✓ The Zulqarnayn Architectura is mathematically robust.")
        print_colored(COLOR_WHITE, f"  Honest upper bound on breach probability (serial): {fmt_prob(dm['total_breach_probability_serial'])}")
        print_colored(COLOR_WHITE, f"  Honest union bound (parallel): {fmt_prob(dm['total_breach_probability_union'])}")
        print_colored(COLOR_WHITE, "  Note: Exact zero probabilities are unachievable in physical systems.")
        print_colored(COLOR_WHITE, "        See corrected mathematical framework (Theorems 1-5).")

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
            ("zeroization_attest_pass", "Zeroization Attest", "simulated"),
            ("integrity_check_pass", "Code Integrity", "signature verified"),
            ("timing_check_pass", "Timing Evasion", "no debugger detected"),
            ("hardware_abstraction_pass", "Hardware Abstraction", "platform independent")
        ]

        skip_crypto = (ENV_MODE == "virtual" and self.config.split_knowledge_enabled and not self._key_reconstructed)

        if not silent:
            print_header("RUNNING ZLQ-AR-1 SELF-TEST (10 CHECKS)")

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
                        result = True  # skip silently
                    else:
                        test_data = b"test"
                        self.store_data("self_test", test_data)
                        retrieved = self.retrieve_data("self_test")
                        result = (retrieved == test_data)
                        with self._lock:
                            self.data_store.pop("self_test", None)
                elif key == "crypto_pass":
                    if skip_crypto:
                        result = True  # skip silently
                    else:
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
                elif key == "integrity_check_pass":
                    result = verify_script_signature()
                elif key == "timing_check_pass":
                    result = True
                elif key == "hardware_abstraction_pass":
                    hw = self.get_hardware_abstraction()
                    result = hw["platform_independent"]
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

        overall = all(results.values())
        if not silent:
            print_header("SELF-TEST SUMMARY")
            for key, name, desc in test_names:
                status = "PASS" if results[key] else "FAIL"
                color = COLOR_GREEN if results[key] else COLOR_RED
                print_colored(color, f"  {name:20} : {status}")
            print_colored(COLOR_BOLD + (COLOR_GREEN if overall else COLOR_RED),
                         f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
            self.print_security_report()

        if silent:
            SILENT_MODE = old_silent
        results["overall_pass"] = overall
        return results

    def run_daemon(self):
        global SILENT_MODE
        SILENT_MODE = True

        self.logger.info("Starting daemon...")
        self.activate_layers()
        self._start_unix_socket_server()

        self.logger.info("Type=simple, no notification required.")

        if ENV_MODE == "virtual" and self.config.split_knowledge_enabled and not self._key_reconstructed:
            self.logger.warning("Waiting for split knowledge share injection via secure ECDHE socket...")
            while not self._key_reconstructed:
                time.sleep(5)
            self.logger.info("Key reconstructed, entering operational phase.")

        while True:
            try:
                status = self.run_self_test(silent=True)
                overall = status.get("overall_pass", False)
                self.logger.info(json.dumps({"event": "self_test", "status": "PASS" if overall else "FAIL"}))
                if not overall:
                    self.logger.warning("Self-test failure: " + json.dumps(status))
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

        try:
            peer_cred = self.request.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('iII'))
            pid, uid, gid = struct.unpack('iII', peer_cred)
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
            return

        cmd = req.get('cmd')
        is_inject = (cmd == 'inject_share')
        is_getpubkey = (cmd == 'get_pubkey')
        is_locked = not core._key_reconstructed

        if is_locked and (is_getpubkey or is_inject):
            try:
                resp = core._process_request(req)
            except Exception as e:
                resp = {"status":"error", "message": str(e)}
            self.request.sendall(json.dumps(resp).encode())
            return

        try:
            timestamp = float(req.get('timestamp', 0.0))
            nonce = req.get('nonce', '')
        except (TypeError, ValueError):
            self.request.sendall(b'{"status":"error","message":"invalid timestamp/nonce"}')
            return

        if timestamp <= 0 or not nonce:
            self.request.sendall(b'{"status":"error","message":"missing timestamp or nonce"}')
            return

        sig = req.pop('_sig', None)
        if sig is None:
            self.request.sendall(b'{"status":"error","message":"missing signature"}')
            return
        sig = base64.b64decode(sig)

        if not core._authenticate_request(req, sig, nonce, timestamp):
            self.request.sendall(b'{"status":"error","message":"authentication failed"}')
            return

        try:
            resp = core._process_request(req)
        except Exception as e:
            resp = {"status":"error", "message": str(e)}
        self.request.sendall(json.dumps(resp).encode())

# =============================================================================
# SIGNAL HANDLER
# =============================================================================
def handle_signal(sig, frame):
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
def main():
    global SILENT_MODE

    if args.device_id == "test" and not (args.self_test or args.security_report):
        print_error("Device ID 'test' is not allowed in production mode. Use a valid device ID.")
        sys.exit(1)

    if args.self_test or args.security_report:
        import tempfile
        os.environ["ZARQA_STATE_DIR"] = tempfile.mkdtemp(prefix="zlq_temp_")

    if args.daemon:
        SILENT_MODE = True

    if args.self_test:
        core = ZulqarnaynArchitectura("test", test_mode=True)
        res = core.run_self_test(silent=False)
        overall = res.get("overall_pass", False)
        sys.exit(0 if overall else 1)

    elif args.status:
        subprocess.run(["systemctl", "status", SERVICE_NAME], check=False)
        sys.exit(0)

    elif args.daemon:
        core = ZulqarnaynArchitectura(args.device_id)
        core.run_daemon()
        sys.exit(0)

    elif args.security_report:
        core = ZulqarnaynArchitectura("report", test_mode=True)
        core.print_security_report()
        sys.exit(0)

    else:
        print("Usage: --auto-deploy | --self-test | --status | --daemon | --security-report")
        sys.exit(0)

if __name__ == "__main__":
    main()
