# RustCleaner
## Surgical Trace Removal for Rust, EasyAntiCheat & Facepunch

A minimal, transparent, and production-ready utility for removing Rust, EasyAntiCheat, and Facepunch identifiers, caches, and system traces from Windows. Designed for players who require a clean local environment without unnecessary abstractions, hidden behaviors, or bloated feature sets.

**~480 lines. Standard library only. Zero external dependencies.**

---

### 📖 Core Philosophy
- **Explicit over Implicit:** Every action is logged, validated, and optionally previewed before execution.
- **Minimal over Maximalist:** ~480 lines of well-documented Python. No external dependencies, no speculative abstractions, no silent assumptions.
- **Safety over Speed:** Return-code verification, timeout guards, permission-aware deletion with retry logic, and mandatory dry-run capability.
- **Targeted over Destructive:** Only touches Rust (AppID `252490`), EasyAntiCheat, and Facepunch traces. All other Steam games and system files remain untouched.

---

### 🔍 What It Cleans ( Additions Highlighted)

| Category | Targets | Scope |
|----------|---------|-------|
| **Processes** | `steam.exe`, `RustClient.exe`, EAC executables | Terminated with 10s timeout & 0.5s cooldown |
| **Steam Caches** | `appcache`, `depotcache`, `downloading`, `temp`, `logs`, `config` | Safe to regenerate |
| **Rust Game Data** | `shadercache/252490`, `workshop`, `userdata/*/252490`, `760/remote`, `il2cpp_cache`, `ScriptCache`, `EasyAntiCheat/` | Preserves core game folder unless `--full-wipe` |
| **🆕 Rust Saved Folders** | `Saved/Config`, `Saved/Logs`, `Saved/ScreenShots` | **New in ** — common persistence points for settings & crash data |
| **🆕 Chromium htmlcache** | `Cache`, `Code Cache`, `GPUCache`, `Service Worker` subdirs | **New in ** — removes embedded web artifacts from Steam browser |
| **Cloud/Profiles** | `Steam/remote/252490`, `Steam/screenshots/252490` | Local identifiers & screenshot caches |
| **🆕 Facepunch Launcher** | `%APPDATA%/Facepunch*`, `%LOCALAPPDATA%/Facepunch*` | **New in ** — launcher metadata that may persist across reinstalls |
| **EasyAntiCheat** | Services (`EAC`, `EAC_EOS`), official `qa-factory-reset`, program files, `%APPDATA%`, `%PROGRAMDATA%`, `Public`, `%WINDIR%\Temp` | Stops services before deletion |
| **Registry** | 17 targeted keys (`HKLM`/`HKCU`) under `EasyAntiCheat`, `Facepunch Studios`, `Valve\Steam\Apps\252490`, Uninstall entries | Explicit deletion, **no backup** (intentional) |
| **🆕 Windows Event Logs** | `Application`/`System` entries containing "Rust", "EasyAntiCheat", "Facepunch" | **New in ** — removes audit trail via `wevtutil` |
| **🆕 Hosts File Scan** | `C:\Windows\System32\drivers\etc\hosts` entries matching Rust/EAC patterns | **New in ** — catches manual blocking attempts |
| **🆕 loginusers.vdf** | Steam account metadata containing Rust AppID references | **New in ** — sanitizes cached account data (with backup) |
| **System Traces** | `%TEMP%`, `%TMP%`, `%WINDIR%\Prefetch`, GPU caches (NVIDIA/AMD/Intel/D3DSCache), WER reports, Scheduled tasks | Pattern-matched, permission-safe |

---

### 🛠 Usage

#### Quick Start
1. Place `start.bat` and `main.py` in the same directory.
2. Right-click `start.bat` → **Run as Administrator**.
3. Follow the interactive prompts, or run `--dry-run` first to audit.

#### Command-Line Flags
| Flag | Behavior |
|------|----------|
| *(none)* | **Interactive mode** (default). Step-by-step consent prompts. PC rename requires custom input. |
| `--dry-run` | **Preview only**. Lists every target with descriptive labels. Zero filesystem/registry modifications. |
| `--batch` | **Automated mode**. Skips prompts. Auto-generates a valid `WIN-XXXXXXX` hostname. |
| `--full-wipe` | **Nuclear mode**. Deletes the `steamapps/common/Rust` folder (~50GB). Requires Steam reinstall. |
| `--help` | Displays argument reference. |

#### Examples
```powershell
# Safe preview (recommended first run)
python rust_clean.py --dry-run

# Guided interactive cleanup (default when double-clicking start.bat)
python main.py

# Automated cleanup with forced rename
python main.py --batch

# Full wipe + automated + preview
python main.py --full-wipe --dry-run
```

---

### 🔄 Execution Flow (Verified Order)
1. **Admin Check** → Auto-elevates via UAC if run without privileges.
2. **Process Termination** → Kills Steam/Rust/EAC with 10s timeout & 0.5s cooldown.
3. **Steam & Game Cache Cleanup** → Removes Rust-specific caches, userdata, cloud identifiers, internal game caches (`il2cpp`, `ScriptCache`), Saved folders, and Chromium htmlcache subdirs.
4. **Profile & Launcher Cleanup** → Removes Facepunch launcher traces, sanitizes `loginusers.vdf`.
5. **EAC Removal** → Stops/deletes services, attempts official `qa-factory-reset`, deletes known EAC directories.
6. **System Cleanup** → Deletes temp/prefetch, GPU caches, WER reports, scheduled tasks, Event Log entries, and hosts file entries.
7. **Registry Cleanup** → Deletes 17 targeted keys (explicit, no backup).
8. **PC Rename** → Validates hostname against NetBIOS rules, queues change via PowerShell (applies on reboot).
9. **Reboot Prompt** → Offers immediate restart **only after all operations complete**.
10. **Audit Logging** → Writes timestamped success/fail status to `rust_clean.log`.

> ✅ **Reboot is strictly at the end.** All deletions and the PC rename command execute before the reboot prompt appears.

---

### 🛡 Safety & Transparency

| Feature | Implementation |
|---------|---------------|
| **Dry-Run Mode** | Every deletion target is printed with a descriptive label: `[DRY] Would delete: path (label)` |
| **Robust Deletion** | `_rm()` uses `shutil.rmtree(onerror=...)` to retry locked/readonly files; logs skips for audit |
| **Input Validation** | Hostnames enforce Windows NetBIOS rules (1–15 chars, alphanumeric/hyphens, no leading/trailing hyphens) |
| **Return-Code Verification** | `taskkill`, `sc`, `reg`, `schtasks`, `wevtutil`, and PowerShell calls validate `returncode == 0` |
| **Timeout Guards** | All subprocess calls enforce strict timeouts (10–30s) to prevent hangs |
| **Permission-Aware** | `PermissionError` caught gracefully; locked files reported, not forced |
| **Explicit Assumptions** | No registry backups, no firewall modifications, no speculative path scanning |
| **Audit Trail** | `rust_clean.log` captures every action with timestamps for post-run verification |
| **Interactive Gates** | Each major cleaning phase asks for consent; final summary + confirmation before destructive ops |

---

### ⚠️ Limitations & Explicit Notes
- **Local-Only Scope:** This tool cleans local identifiers, caches, and services. Game servers store ban/hardware data independently; local cleanup does not guarantee server-side state changes.
- **No Registry Backups:** Intentionally omitted to maintain minimalism. Use `--dry-run` to verify targets before execution.
- **Windows-Only:** Relies on `winreg`, `schtasks`, `sc`, `wevtutil`, and PowerShell. Not cross-platform.
- **PC Rename Requires Reboot:** Windows queues hostname changes until the next system restart. The script prompts for reboot only after all cleaning completes.
- **Event Log Cleaning is Best-Effort:** Uses keyword heuristics; may not catch all relevant entries.
- **loginusers.vdf Sanitization is Heuristic:** Simple line-filtering; complex VDF structures may not be fully parsed.

---

### 📦 Requirements
- **OS:** Windows 10/11 (64-bit)
- **Runtime:** Python 3.10+ (standard library only)
- **Permissions:** Administrator rights (mandatory for service/registry/hostname modifications)

---

### 📄 License & Disclaimer
Provided as-is for educational and personal use. The author assumes no responsibility for system modifications, data loss, or service disruptions. Always review `--dry-run` output and maintain backups of critical data before executing system-level cleanup tools.

---

> **Transparency First:** This script is deliberately minimal and explicit. If you need speculative features, silent automation, or automated rollbacks, this is not the tool you're looking for. If you want auditable, surgical cleanup with full control and zero hidden behavior, proceed.

```bash
# Always start with a dry-run audit
python rust_clean.py --dry-run

# Then run interactively (default) or with --batch for automation
python rust_clean.py
```
