# Zulqarnayn-Anti-Tamper-Hardware-Security-Module-HSM
Production-grade enterprise HSM core featuring constant-time Galois Field SSS, kernel air-gapping, and secure ECDHE IPC.

## Phase 1: Zulqarnayn Initium Core (ZLQ-IN-0)

**Version:** 6.2.0

**Status:** Production-Ready / Enterprise Grade

---

### Overview

**Zulqarnayn Initium Core (ZLQ-IN-0)** is a high-security, software-defined Hardware Security Module (HSM) and Anti-Tamper cryptographic vault engineered for zero-trust environments. Designed to operate under severe threat models, ZLQ-IN-0 combines hardware-bound Physical Unclonable Functions (PUFs), constant-time Galois Field arithmetic, Shamir's Secret Sharing (SSS), and strict kernel-level isolation.

---

### Key Architectural Features

* **Constant-Time Galois Field Math ($GF(2^8)$):** Branchless, tableless Galois field arithmetic preventing cache-timing side-channel attacks during secret sharing and reconstruction.
* **Kernel-Level Air-Gapping:** Leverages native Linux Network Namespaces (`PrivateNetwork=yes`), `ProtectSystem=strict`, `ProtectKernelTunables=yes`, and restricted address families (`RestrictAddressFamilies=AF_UNIX`) via systemd hardening.
* **Out-of-Band ECDHE IPC:** Implements an Elliptic Curve Diffie-Hellman Ephemeral (ECDHE) handshake over UNIX domain sockets, securing split-knowledge key provisioning using AES-GCM encryption.
* **Anti-Tracing Enforcement:** Enforces `PR_SET_DUMPABLE = 0` via `prctl` at initialization to block all local debugging, tracing, and memory-dumping vectors (even from root actors).
* **Secure Memory Management:** Utilizes memory locking (`mlock`) to prevent sensitive cryptographic material from paging to disk, alongside explicit memory zeroization (`explicit_bzero`) to scrub transient variables.

---

### Directory Structure

```text
/opt/zarqa/zulqarnayn_athsm/
├── zulqarnayn_initium_0_core.py   # Main HSM Daemon & Deployment Orchestrator
├── injector.py                    # Secure ECDHE Key Provisioning Tool
└── venv/                          # Isolated Python Virtual Environment

```

---

### Prerequisites & System Dependencies

* **OS:** Ubuntu / Linux Kernel supporting systemd and network namespaces.
* **Privileges:** Root access (`sudo`) is required solely for initial deployment, user provisioning, and systemd service registration.
* **Dependencies:** Python 3.10+ with `cryptography`, `numpy`, and `psutil` (automatically provisioned inside a managed virtual environment during deployment).

---

### Installation & Deployment

#### 1. Provisioning the Core Script

Place the core script at the absolute production path:

```bash
sudo mkdir -p /opt/zarqa/zulqarnayn_athsm
# Place your zulqarnayn_initium_0_core.py into /opt/zarqa/zulqarnayn_athsm/
sudo chmod +x /opt/zarqa/zulqarnayn_athsm/zulqarnayn_initium_0_core.py

```

#### 2. Executing Auto-Deployment

Run the auto-deployment routine. This will perform syntax verification, environment cleanup, dependency resolution, virtual environment building, system user provisioning (`zulqarnayn`), and systemd unit registration:

```bash
sudo /opt/zarqa/zulqarnayn_athsm/zulqarnayn_initium_0_core.py --auto-deploy

```

Upon successful execution, the deployment script will output a unique **External Share (Base64)**. Save this securely; it represents the second half of the split-knowledge master key.

---

### Unlocking & Initializing the HSM (Split-Knowledge Injection)

In virtual deployment mode, the HSM boots into a locked state waiting for the external share. To provision the key securely via the ECDHE-encrypted UNIX socket injector:

```bash
sudo /opt/zarqa/zulqarnayn_athsm/injector.py '<YOUR_BASE64_EXTERNAL_SHARE>'

```

Once injected, the Master Key is mathematically reconstructed in pinned memory, transitioning the core into its active operational phase.

---

### Monitoring & Operations

* **Check Service Status:**
```bash
sudo systemctl status zulqarnayn-initium

```


* **Stream Structured JSON Audit Logs:**
```bash
sudo journalctl -u zulqarnayn-initium -f

```


* **Run Manual Self-Tests:**
```bash
sudo /opt/zarqa/zulqarnayn_athsm/venv/bin/python3 /opt/zarqa/zulqarnayn_athsm/zulqarnayn_initium_0_core.py --self-test

```



---

### License

This project is proprietary and confidential. Unauthorized copying, distribution, or reverse engineering is strictly prohibited.
