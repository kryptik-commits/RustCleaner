# RustCleaner
## Surgical Trace Removal for Rust & EasyAntiCheat

A minimal, transparent, and robust utility for removing Rust and EasyAntiCheat identifiers, caches, and system traces from Windows. Designed for players who require a clean local environment without unnecessary abstractions, hidden behaviors, or bloated feature sets.

---

### 📖 Core Philosophy
- **Explicit over Implicit:** Every action is logged, validated, and optionally previewed before execution.
- **Minimal over Maximist:** ~260 lines of standard-library Python. No external dependencies, no speculative abstractions, no silent assumptions.
- **Safety over Speed:** Return-code verification, timeout guards, permission-aware deletion, and mandatory dry-run capability.
- **Targeted over Destructive:** Only touches Rust (AppID `252490`) and EasyAntiCheat traces. All other Steam games and system files remain untouched.

---

### 🔍 What It Cleans
| Category | Targets | Scope |
|----------|---------|-------|
| **Processes** | `steam.exe`, `RustClient.exe`, EAC executables | Terminated with timeout & retry guards |
| **Steam Caches** | `appcache`, `depotcache`, `downloading`, `temp`, `logs`, `config` | Safe to regenerate |
| **Rust Game Data** | `shadercache/252490`, `workshop`, `userdata/*/252490`, `760/remote`, `il2cpp_cache`, `ScriptCache`, `EasyAntiCheat/` | Preserves core game folder unless `--full-wipe` |
| **Cloud/Profiles** | `Steam/remote/252490`, `Steam/screenshots/252490` | Local identifiers & screenshot caches |
| **EasyAntiCheat** | Services (`EAC`, `EAC_EOS`), official factory reset, program files, `%APPDATA%`, `%PROGRAMDATA%`, `Public`, `%WINDIR%\Temp` | Stops services before deletion |
| **Registry** | 17 targeted keys (`HKLM`/`HKCU`) under `EasyAntiCheat`, `Facepunch Studios`, `Valve\Steam\Apps\252490`, Uninstall entries | Explicit deletion, no backup |
| **System Traces** | `%TEMP%`, `%TMP%`, `%WINDIR%\Prefetch`, Deep Windows scan (excludes `System32`/`WinSxS`), GPU caches (NVIDIA/AMD/Intel/D3DSCache), WER reports, Scheduled tasks | Pattern-matched, permission-safe |

---

### 🛠 Usage

#### Quick Start
1. Place `start.bat` and `rust_clean.py` in the same directory.
2. Right-click `start.bat` → **Run as Administrator**.
3. Follow the interactive prompts, or run `--dry-run` first to audit.

#### Command-Line Flags
| Flag | Behavior |
|------|----------|
| *(none)* | **Interactive mode** (default). Step-by-step consent prompts. PC rename requires custom input. |
| `--dry-run` | **Preview only**. Lists every target with labels. Zero filesystem/registry modifications. |
| `--batch` | **Automated mode**. Skips prompts. Auto-generates a valid `WIN-XXXXXXX` hostname. |
| `--full-wipe` | **Nuclear mode**. Deletes the `steamapps/common/Rust` folder (~50GB). Requires Steam reinstall. |
| `--help` | Displays argument reference. |

#### Examples
```powershell
# Safe preview (recommended first run)
python rust_clean.py --dry-run

# Guided interactive cleanup (default when double-clicking start.bat)
python rust_clean.py

# Automated cleanup with forced rename
python rust_clean.py --batch

# Full wipe + automated + preview
python rust_clean.py --full-wipe --dry-run
```

---

### 🔄 Execution Flow
1. **Admin Check** → Auto-elevates via UAC if run without privileges.
2. **Process Termination** → Kills Steam/Rust/EAC with 10s timeout & 0.5s cooldown between calls.
3. **Steam & Game Cache Cleanup** → Removes Rust-specific caches, userdata, cloud identifiers, and internal game caches (`il2cpp`, `ScriptCache`).
4. **EAC Removal** → Stops/deletes services, attempts official `qa-factory-reset`, deletes known EAC directories.
5. **System & Registry Cleanup** → Deletes targeted registry keys, temp/prefetch, GPU caches, WER reports, and scheduled tasks.
6. **PC Rename** → Validates hostname against NetBIOS rules, queues change via PowerShell (applies on reboot).
7. **Reboot Prompt** → Offers immediate restart only after all operations complete.
8. **Audit Logging** → Writes timestamped success/fail status to `rust_clean.log`.

---

### 🛡 Safety & Transparency
| Feature | Implementation |
|---------|---------------|
| **Dry-Run Mode** | Every deletion target is printed with a descriptive label before execution. |
| **Input Validation** | Hostnames enforce Windows rules (1–15 chars, alphanumeric/hyphens, no leading/trailing hyphens). |
| **Return-Code Verification** | `taskkill`, `sc`, `reg`, `schtasks`, and PowerShell calls validate `returncode == 0`. |
| **Timeout Guards** | All subprocess calls enforce strict timeouts (10–30s) to prevent hangs. |
| **Permission-Aware** | `PermissionError` caught gracefully; locked files reported, not forced. |
| **Explicit Assumptions** | No registry backups, no firewall modifications, no speculative path scanning. |
| **Audit Trail** | `rust_clean.log` captures every action with timestamps for post-run verification. |

---

### ⚠️ Limitations & Explicit Notes
- **Local-Only Scope:** This tool cleans local identifiers, caches, and services. Game servers store ban/hardware data independently; local cleanup does not guarantee server-side state changes.
- **No Registry Backups:** Intentionally omitted. Use `--dry-run` to verify targets before execution.
- **Windows-Only:** Relies on `winreg`, `schtasks`, `sc`, and PowerShell. Not cross-platform.
- **PC Rename Requires Reboot:** Windows queues hostname changes until the next system restart.
- **Deep Temp Scan:** `WINDIR.rglob()` is thorough but intentionally skips `System32` and `WinSxS` for safety. May take additional time on large drives.

---

### 📦 Requirements
- **OS:** Windows 10/11 (64-bit)
- **Runtime:** Python 3.10+ (standard library only)
- **Permissions:** Administrator rights (mandatory for service/registry/hostname modifications)

---

### 📄 License & Disclaimer
Provided as-is for educational and personal use. The author assumes no responsibility for system modifications, data loss, or service disruptions. Always review `--dry-run` output and maintain backups of critical data before executing system-level cleanup tools.

---
> **Transparency First:** This script is deliberately minimal. If you need speculative features, silent automation, or automated rollbacks, this is not the tool you're looking for. If you want explicit, auditable, surgical cleanup with full control, proceed.
