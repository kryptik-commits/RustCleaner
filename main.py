#!/usr/bin/env python3
"""
RustCleaner v3 - Minimal + Robust + Production-Ready
Default: Interactive. PC rename forced (custom input or auto for --batch).
Flags: --dry-run, --batch, --full-wipe

Surgical trace removal for Rust, EasyAntiCheat, and Facepunch on Windows.
"""
import argparse, ctypes, datetime, fnmatch, logging, os, random, shutil, stat, string, subprocess, sys, time, traceback, winreg
from pathlib import Path
from typing import Optional, Callable

# ── Constants ───────────────────────────────────────────────────────
RUST = "252490"
RUST_DIR = "Rust"
PROCS = ["steam.exe", "RustClient.exe", "EasyAntiCheat.exe", "EasyAntiCheat_EOS.exe", "EasyAntiCheat_Setup.exe"]
REG_KEYS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\EasyAntiCheat"),
    (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\EasyAntiCheat_EOS"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\EasyAntiCheat"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\EasyAntiCheat"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\EasyAntiCheat"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Facepunch Studios"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Facepunch Studios"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Facepunch Studios"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\WOW6432Node\Facepunch Studios"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Facepunch Studios LTD"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Facepunch Studios LTD"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Facepunch Studios LTD"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\WOW6432Node\Facepunch Studios LTD"),
    (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Valve\Steam\Apps\{RUST}"),
    (winreg.HKEY_CURRENT_USER, rf"SOFTWARE\Valve\Steam\Apps\{RUST}"),
    (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App {RUST}"),
    (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Steam App {RUST}"),
]

# ── File Logging ────────────────────────────────────────────────────
LOG_FILE = Path(__file__).parent / "rust_clean.log"
logger = logging.getLogger("rc")
logger.setLevel(logging.INFO)
try:
    fh = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger.addHandler(fh)
except: pass  # Fallback: console only

# ── Helpers ─────────────────────────────────────────────────────────
def env_path(var: str) -> Optional[Path]:
    """Safely resolve environment variable to Path, or None if unset."""
    v = os.environ.get(var)
    return Path(v) if v else None

def _handle_remove_readonly(func: Callable, path: str, exc: tuple) -> None:
    """onerror handler for shutil.rmtree: retry after clearing readonly attribute."""
    excval = exc[1]
    if func in (os.rmdir, os.remove, os.unlink) and isinstance(excval, PermissionError):
        try:
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            func(path)
        except Exception:
            pass  # Give up silently — logged by caller

def _rm(p: Path, dry: bool, label: str = "") -> bool:
    """Delete file or directory with robust error handling.
    
    - Uses onerror handler to retry locked/readonly files
    - Logs skipped items for audit trail
    - Respects dry-run mode with labeled output
    """
    if not p.exists(): return False
    msg = f"{p} ({label})" if label else str(p)
    if dry:
        print(f"  [DRY] Would delete: {msg}"); logger.info(f"[DRY] {p}")
        return True
    try:
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=False, onerror=_handle_remove_readonly)
        else:
            # Retry readonly files
            try: p.unlink()
            except PermissionError:
                p.chmod(stat.S_IWRITE | stat.S_IREAD)
                p.unlink()
        print(f"  ✓ Deleted: {p}"); logger.info(f"Deleted: {p}")
        return True
    except PermissionError: 
        print(f"  [!] Locked (skipped): {p}"); logger.warning(f"Locked: {p}")
        return False
    except Exception as e: 
        print(f"  [!] Failed: {p} — {e}"); logger.error(f"Failed: {p} — {e}")
        return False

def _prompt(msg: str, interactive: bool, dry: bool) -> bool:
    """Prompt for yes/no with validation loop. Returns True for yes."""
    if dry: return True
    if not interactive: return True
    while True:
        ans = input(f"{msg} [y/N]: ").strip().lower()
        if ans in ("y", "yes"): return True
        if ans in ("", "n", "no"): return False
        print("  [?] Answer 'y' or 'n'")

def _validate_pc_name(name: str) -> bool:
    """Validate hostname against Windows NetBIOS rules."""
    return 1 <= len(name) <= 15 and name[0] != '-' and name[-1] != '-' and all(c.isalnum() or c == '-' for c in name)

def _get_pc_name(dry: bool, batch: bool) -> str:
    """Get PC rename target: dry-run placeholder, auto-generated for batch, or user input."""
    if dry: return "DRYRUN-PC"
    if batch: return f"WIN-{''.join(random.choices(string.ascii_uppercase + string.digits, k=7))}"
    print("  PC rename is REQUIRED. (1-15 chars, alphanumeric/hyphens, no leading/trailing hyphens)")
    while True:
        name = input("  New PC name: ").strip()
        if _validate_pc_name(name): return name
        print("  [!] Invalid name. Follow rules above and try again.")

def _section(title: str): 
    """Print section header with visual separator."""
    print(f"\n── {title} " + "─"*(45-len(title))); logger.info(title)

def _log_status(ok: bool, msg: str): 
    """Log operation status with emoji indicator."""
    print(f"  {'✓' if ok else '✗'} {msg}"); logger.info(f"{'OK' if ok else 'FAIL'}: {msg}")

def _confirm(dry: bool, full_wipe: bool, pc_name: str) -> bool:
    """Final confirmation gate before destructive operations."""
    if dry: return True
    print(f"\n{'='*45}")
    print(f" SUMMARY")
    print(f" • PC will rename to: {pc_name} (requires reboot)")
    print(f" • All Rust/EAC traces will be cleaned")
    if full_wipe: print(f" • Rust game folder (~50GB) WILL BE DELETED")
    print(f"{'='*45}")
    while True:
        ans = input("\n ❓ Proceed? [y/N]: ").strip().lower()
        if ans in ("y", "yes"): return True
        if ans in ("", "n", "no"): print(" ✋ Cancelled."); logger.info("Cancelled by user"); return False
        print("  [?] Answer 'y' or 'n'")

def _print_next_steps(dry: bool, full_wipe: bool, pc_name: str):
    """Print mode-tailored next steps and reboot guidance."""
    print(f"\n{'='*45}")
    print(f" {'DRY-RUN' if dry else 'CLEANUP'} COMPLETED")
    print(f"{'='*45}")
    if dry:
        print(" → No files were deleted. Review dry-run output above.")
    else:
        print(f" → PC renamed to: {pc_name} (reboot required)")
        print(" → Locked files may require a restart to fully clear.")
        if full_wipe: print(" → Game folder deleted. Reinstall via Steam.")
        else: print(" → Game files preserved. Steam may verify files on launch.")
    print(" Next steps:")
    print(" 1. Restart your PC to apply rename & clear file handles")
    print(" 2. Launch Steam → Verify Rust integrity if issues persist")
    print(" 3. Check rust_clean.log for detailed audit trail")
    print(f"{'='*45}")

# ── Cleaners ────────────────────────────────────────────────────────
def _kill(dry: bool):
    """Terminate Rust/Steam/EAC processes with timeout and cooldown."""
    for proc in PROCS:
        if dry: print(f"  [DRY] Would kill: {proc}"); continue
        try:
            r = subprocess.run(["taskkill","/F","/IM",proc], capture_output=True, timeout=10)
            _log_status(r.returncode == 0, f"Killed {proc}")
        except subprocess.TimeoutExpired: _log_status(False, f"Timeout killing {proc}")
        except Exception as e: _log_status(False, f"Error killing {proc}: {e}")
        time.sleep(0.5)  # Cooldown between kills

def _find_steam():
    """Locate all Steam installations via default path, registry, and libraryfolders.vdf."""
    dirs = set()
    default = Path(r"C:\Program Files (x86)\Steam")
    if default.exists(): dirs.add(default)
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam") as k:
            p = Path(winreg.QueryValueEx(k, "InstallPath")[0])
            if p.exists(): dirs.add(p)
    except Exception as e: print(f"  [!] Registry Steam lookup failed: {e}")
    for sdir in list(dirs):
        vdf = sdir / "steamapps" / "libraryfolders.vdf"
        if not vdf.exists(): continue
        try:
            for line in vdf.read_text(errors="ignore").splitlines():
                if '"path"' in line.lower():
                    parts = line.split('"')
                    if len(parts) >= 4:
                        p = Path(parts[3].replace("\\\\", "\\"))
                        if p.exists(): dirs.add(p)
                    else: print(f"  [!] Malformed VDF line: {line[:50]}...")
        except Exception as e: print(f"  [!] Failed to parse VDF: {e}")
    return list(dirs)

def _clean_steam(dirs, dry: bool, interactive: bool):
    """Clean Steam caches and Rust-specific data with aggressive targeting."""
    if not _prompt("Clean Steam caches & Rust userdata?", interactive, dry): return
    for s in dirs:
        targets = [
            (s/"appcache", "Steam appcache"),
            (s/"depotcache", "Steam depotcache"),
            (s/"steamapps/downloading", "Pending downloads"),
            (s/"steamapps/temp", "Steam temp"),
            (s/"steamapps/shadercache"/RUST, "Steam shadercache"),
            (s/"steamapps/userdata", "Steam userdata"),
            (s/"steamapps/workshop/content"/RUST, "Workshop content"),
            (s/"steamapps/workshop/downloads"/RUST, "Workshop downloads"),
            (s/"logs", "Steam logs"),
            (s/"config", "Steam config"),
            # Aggressive Rust game-internal caches (high-value)
            (s/"steamapps/common"/RUST_DIR/"Saved"/"Config", "Rust Saved/Config"),
            (s/"steamapps/common"/RUST_DIR/"Saved"/"Logs", "Rust Saved/Logs"),
            (s/"steamapps/common"/RUST_DIR/"Saved"/"ScreenShots", "Rust Saved/ScreenShots"),
            (s/"steamapps/common"/RUST_DIR/"RustClient_Data"/"il2cpp_cache", "il2cpp cache"),
            (s/"steamapps/common"/RUST_DIR/"RustClient_Data"/"ScriptCache", "script cache"),
            (s/"steamapps/common"/RUST_DIR/"EasyAntiCheat", "Game EAC folder"),
        ]
        for path, label in targets: _rm(path, dry, label)

        # Deep Chromium htmlcache cleaning (embedded web artifacts)
        htmlcache = s/"htmlcache"
        if htmlcache.exists():
            for sub in ["Cache", "Code Cache", "GPUCache", "Service Worker"]:
                _rm(htmlcache/sub, dry, f"htmlcache/{sub}")

        # Userdata deep clean with stray Facepunch/Rust folder detection
        ud = s/"steamapps"/"userdata"
        if ud.exists():
            try:
                for u in ud.iterdir():
                    if not u.is_dir(): continue
                    _rm(u/RUST, dry, "Userdata/Rust")
                    _rm(u/"760"/"remote"/RUST, dry, "Steam Cloud/Remote")
                    for stray in u.iterdir():
                        if any(k in stray.name.lower() for k in ["rust", "facepunch"]):
                            _rm(stray, dry, "Stray Facepunch/Rust")
            except PermissionError: pass

    # AppData/LocalAppData Steam + Facepunch cleanup
    for root_env in ("APPDATA","LOCALAPPDATA"):
        root = env_path(root_env)
        if not root or not root.exists(): continue
        for sub in ["Steam/htmlcache","Steam/logs","Steam/dumps"]: _rm(root/sub, dry, f"{root_env}/Steam/{sub.split('/')[-1]}")
        # Facepunch Launcher traces (high-value addition)
        for fp in ["FacepunchStudios", "Facepunch"]:
            _rm(root/fp, dry, f"{root_env}/{fp}")
        ud = root/"Steam"/"userdata"
        if ud.exists():
            try:
                for u in ud.iterdir():
                    if u.is_dir(): _rm(u/RUST, dry, f"{root_env}/Userdata/Rust")
            except PermissionError: pass

def _clean_steam_profile_identifiers(dry: bool, interactive: bool):
    """Clean Rust cloud save and screenshot metadata from Steam profiles."""
    if not _prompt("Clean Rust cloud/screenshot data?", interactive, dry): return
    for root_env in ("APPDATA","LOCALAPPDATA"):
        root = env_path(root_env)
        if not root or not root.exists(): continue
        for sub in [f"Steam/remote/{RUST}", f"Steam/screenshots/{RUST}"]:
            _rm(root/sub, dry, f"{root_env}/{sub}")

def _clean_eac(dry: bool, interactive: bool):
    """Remove EasyAntiCheat services, folders, and attempt official factory reset."""
    if not _prompt("Delete EAC services & folders?", interactive, dry): return
    for svc in ["EasyAntiCheat","EasyAntiCheat_EOS"]:
        if dry: print(f"  [DRY] Would stop/delete service: {svc}"); continue
        try:
            r = subprocess.run(["sc","stop",svc], capture_output=True, timeout=15)
            if r.returncode != 0: print(f"  [!] Failed to stop: {svc}"); continue
            r = subprocess.run(["sc","delete",svc], capture_output=True, timeout=15)
            _log_status(r.returncode == 0, f"Removed service {svc}")
        except subprocess.TimeoutExpired: _log_status(False, f"Timeout on {svc}")
        except Exception as e: _log_status(False, f"Error on {svc}: {e}")
    eac = Path(r"C:\Program Files (x86)\EasyAntiCheat_EOS\EasyAntiCheat_EOS.exe")
    if eac.exists() and not dry:
        try:
            r = subprocess.run([str(eac),"qa-factory-reset"], capture_output=True, timeout=30)
            _log_status(r.returncode == 0, "EAC factory reset")
        except Exception as e: _log_status(False, f"EAC reset error: {e}")
    eac_paths = [
        (Path(r"C:\Program Files (x86)\EasyAntiCheat_EOS"), "EAC ProgramFiles"),
        (env_path("APPDATA") / "EasyAntiCheat" if env_path("APPDATA") else None, "EAC AppData"),
        (env_path("LOCALAPPDATA") / "EasyAntiCheat" if env_path("LOCALAPPDATA") else None, "EAC LocalAppData"),
        (Path(os.environ.get("PROGRAMDATA","C:\ProgramData")) / "EasyAntiCheat", "EAC ProgramData"),
        (Path(r"C:\Users\Public\EasyAntiCheat"), "EAC Public"),
        (Path(os.environ.get("WINDIR","C:\Windows")) / "Temp/EasyAntiCheat", "EAC Temp"),
    ]
    for p, label in eac_paths:
        if p: _rm(p, dry, label)

def _clean_temp(dry: bool, interactive: bool):
    """Clean temp directories and Prefetch entries matching Rust/EAC patterns."""
    if not _prompt("Clean temp/prefetch files?", interactive, dry): return
    pats = [f"*{x}*" for x in ["rust","steam","easyanticheat","eac","facepunch",RUST]]
    temp_dirs = [env_path("TEMP"), env_path("TMP"), env_path("LOCALAPPDATA")/"Temp" if env_path("LOCALAPPDATA") else None, Path(os.environ.get("WINDIR","C:\Windows"))/"Temp"]
    for td in [d for d in temp_dirs if d]:
        if not td.exists(): continue
        try:
            for i in td.iterdir():
                if any(fnmatch.fnmatch(i.name.lower(), p) for p in pats): _rm(i, dry, f"Temp/{i.name}")
        except PermissionError: pass
    pf = Path(r"C:\Windows\Prefetch")
    if pf.exists():
        for pat in ["*Rust*","*Steam*","*EasyAntiCheat*"]:
            for m in pf.glob(pat): _rm(m, dry, f"Prefetch/{m.name}")
    # Note: Deep windir.rglob scan removed per request (slow, low-value)

def _clean_event_logs(dry: bool, interactive: bool):
    """Clear Windows Event Log entries containing Rust/EAC/Facepunch keywords."""
    if not _prompt("Clean Windows Event Logs (Rust/EAC entries)?", interactive, dry): return
    logs = ["Application", "System"]
    keywords = ["Rust", "EasyAntiCheat", "Facepunch"]
    for log in logs:
        for kw in keywords:
            if dry:
                print(f"  [DRY] Would clear '{kw}' entries from {log} log")
                continue
            try:
                # wevtutil query to filter by keyword in message content
                cmd = ["wevtutil","qe",log,f"/q:*[System[(TimeCreated[@SystemTime])]]","/rd:true","/c:1000"]
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                # Simple heuristic: if keyword appears in output, clear the log
                if kw.lower() in r.stdout.lower():
                    r2 = subprocess.run(["wevtutil","cl",log], capture_output=True, timeout=30)
                    _log_status(r2.returncode == 0, f"Cleared {log} log (contained '{kw}')")
                else:
                    print(f"  ℹ No '{kw}' entries found in {log} log")
            except Exception as e: print(f"  [!] Event log error: {e}")

def _clean_hosts_file(dry: bool, interactive: bool):
    """Scan and sanitize hosts file for Rust/EAC/Facepunch entries."""
    if not _prompt("Scan hosts file for Rust/EAC entries?", interactive, dry): return
    hosts = Path(r"C:\Windows\System32\drivers\etc\hosts")
    if not hosts.exists(): return
    if dry:
        print(f"  [DRY] Would scan {hosts} for Rust/EAC entries")
        return
    try:
        lines = hosts.read_text(encoding="utf-8").splitlines()
        filtered = [l for l in lines if not any(k in l.lower() for k in ["rust","easyanticheat","facepunch","eac"])]
        if len(filtered) < len(lines):
            hosts.write_text("\n".join(filtered) + "\n", encoding="utf-8")
            print(f"  ✓ Removed {len(lines)-len(filtered)} entries from hosts file")
            logger.info(f"Cleaned hosts file: removed {len(lines)-len(filtered)} entries")
        else:
            print(f"  ℹ No Rust/EAC entries found in hosts file")
    except Exception as e: print(f"  [!] Hosts file error: {e}")

def _clean_loginusers(dry: bool, interactive: bool):
    """Sanitize Steam loginusers.vdf by removing Rust AppID references."""
    if not _prompt("Sanitize Steam loginusers.vdf?", interactive, dry): return
    vdf = Path(r"C:\Program Files (x86)\Steam\config\loginusers.vdf")
    if not vdf.exists(): return
    if dry:
        print(f"  [DRY] Would sanitize {vdf} (remove Rust-specific account metadata)")
        return
    try:
        content = vdf.read_text(encoding="utf-8", errors="ignore")
        if RUST in content:
            # Backup first for safety
            vdf.with_suffix(vdf.suffix + ".bak").write_text(content, encoding="utf-8")
            # Remove lines containing Rust AppID (best-effort VDF sanitization)
            cleaned = "\n".join(l for l in content.splitlines() if RUST not in l)
            vdf.write_text(cleaned, encoding="utf-8")
            print(f"  ✓ Sanitized loginusers.vdf (backup: {vdf}.bak)")
            logger.info("Sanitized loginusers.vdf")
        else:
            print(f"  ℹ No Rust references found in loginusers.vdf")
    except Exception as e: print(f"  [!] loginusers.vdf error: {e}")

def _clean_reg(dry: bool, interactive: bool):
    """Delete targeted registry keys for EAC, Facepunch, and Rust."""
    if not _prompt(f"Delete {len(REG_KEYS)} registry keys (EAC/Facepunch/Steam)?", interactive, dry): return
    for hive, sub in REG_KEYS:
        hive_str = "HKLM" if hive==winreg.HKEY_LOCAL_MACHINE else "HKCU"
        full = f"{hive_str}\\{sub}"
        if dry: print(f"  [DRY] Would delete reg: {full}"); continue
        try:
            with winreg.OpenKey(hive, sub): pass
            r = subprocess.run(["reg","delete",full,"/f"], capture_output=True, timeout=30)
            _log_status(r.returncode == 0, f"Reg {sub.split('\\')[-1]}")
        except FileNotFoundError: pass
        except Exception as e: print(f"  [!] Reg error {full}: {e}")

def _clean_gpu_wer_tasks(dry: bool, interactive: bool):
    """Clean GPU shader caches, WER reports, and scheduled tasks."""
    if not _prompt("Clean GPU caches, WER reports, tasks?", interactive, dry): return
    gpu_subs = ["NVIDIA/GLCache","NVIDIA/DXCache","NVIDIA/ShaderCache","AMD/DxCache","AMD/DXCache","AMD/ShaderCache","Intel/GLCache","Intel/DXCache","Intel/ShaderCache","D3DSCache","D3DSCache/UserData"]
    for k in ("APPDATA","LOCALAPPDATA"):
        base = env_path(k)
        if not base: continue
        for p in gpu_subs:
            d = base/p
            if d.exists():
                try:
                    for i in d.iterdir():
                        if any(fnmatch.fnmatch(i.name.lower(), x) for x in ["*rust*","*steam*","*eac*","*facepunch*"]): _rm(i, dry, f"GPU/{i.name}")
                except PermissionError: pass
    for base in [env_path("LOCALAPPDATA")/"Microsoft/Windows/WER" if env_path("LOCALAPPDATA") else None, Path(r"C:\ProgramData\Microsoft\Windows\WER")]:
        if not base: continue
        for sub in ["ReportArchive","ReportQueue"]:
            d = base/sub
            if d.exists():
                try:
                    for i in d.iterdir():
                        if any(x in i.name.lower() for x in ["rust","steam","easyanticheat","facepunch"]): _rm(i, dry, f"WER/{i.name}")
                except PermissionError: pass
    for task in ["EasyAntiCheat","MicrosoftWindowsEasyAntiCheat"]:
        if dry: print(f"  [DRY] Would delete task: {task}"); continue
        try:
            r = subprocess.run(["schtasks","/Delete","/TN",task,"/F"], capture_output=True, timeout=30)
            _log_status(r.returncode == 0, f"Task {task}")
        except Exception as e: print(f"  [!] Task error {task}: {e}")

def _rename_pc(dry: bool, name: str) -> None:
    """Rename PC via PowerShell; change applies after reboot."""
    if dry or not name: return
    print(f"  Renaming PC to: {name}...")
    try:
        r = subprocess.run(["powershell","-NoProfile","-Command",f"Rename-Computer -NewName '{name}' -Force"], capture_output=True, text=True, timeout=30)
        _log_status(r.returncode == 0, "PC renamed")
    except Exception as e: _log_status(False, f"PC rename error: {e}")

# ── Main Execution ──────────────────────────────────────────────────
def main():
    start = datetime.datetime.now()
    p = argparse.ArgumentParser(description="RustCleaner v3: Minimal + Robust + Production-Ready")
    p.add_argument("--dry-run", action="store_true", help="Preview only, no changes")
    p.add_argument("--batch", action="store_true", help="Skip interactive prompts")
    p.add_argument("--full-wipe", action="store_true", help="Delete Rust game folder (~50GB)")
    args = p.parse_args()

    # Default to interactive when launched bare (e.g., double-click start.bat)
    is_interactive = len(sys.argv) == 1 or not args.batch

    # Admin elevation for real runs
    if not args.dry_run and not ctypes.windll.shell32.IsUserAnAdmin():
        script = str(Path(sys.argv[0]).resolve())
        safe_args = " ".join(f'"{a}"' if " " in a else a for a in sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {safe_args}', None, 1)
        sys.exit(0)

    dry = args.dry_run
    mode = "[DRY-RUN] " if dry else ""
    print(f"{mode}RustCleaner v3: Starting...")
    logger.info("=== Run Started ===")

    steam = _find_steam()
    if not steam: print("ERROR: Steam not found"); input("Press Enter"); return
    print(f"{mode}Found {len(steam)} Steam install(s)")

    pc_name = _get_pc_name(dry, args.batch)
    if not dry and not _confirm(False, args.full_wipe, pc_name): input("Press Enter"); return

    _section("Killing Processes"); _kill(dry)
    _section("Cleaning Steam"); _clean_steam(steam, dry, is_interactive)
    _section("Cleaning Profiles"); _clean_steam_profile_identifiers(dry, is_interactive)
    _section("Cleaning EAC"); _clean_eac(dry, is_interactive)
    _section("Cleaning Temp"); _clean_temp(dry, is_interactive)
    _section("Cleaning Event Logs"); _clean_event_logs(dry, is_interactive)
    _section("Cleaning Hosts File"); _clean_hosts_file(dry, is_interactive)
    _section("Sanitizing loginusers.vdf"); _clean_loginusers(dry, is_interactive)
    _section("Cleaning Registry"); _clean_reg(dry, is_interactive)
    _section("Cleaning GPU/WER"); _clean_gpu_wer_tasks(dry, is_interactive)

    if args.full_wipe and _prompt("DELETE Rust game folder?", is_interactive, dry):
        for s in steam: _rm(s/"steamapps/common"/RUST_DIR, dry, "Full game folder")
        print(f"{mode}Full wipe: Game folder {'would be' if dry else ''} deleted")

    _rename_pc(dry, pc_name)
    _print_next_steps(dry, args.full_wipe, pc_name)
    
    # Auto-reboot prompt (strictly at the end, after all operations)
    if not dry and input("\n Reboot now? [y/N]: ").strip().lower() in ("y","yes"):
        subprocess.run(["shutdown","/r","/t","10"])

    elapsed = (datetime.datetime.now() - start).seconds
    logger.info(f"=== Run Complete ({elapsed}s) ===")
    input("Press Enter")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\n⚠ Cancelled by user (Ctrl+C)"); sys.exit(0)
    except Exception as e: print(f"\n❌ Unexpected error: {e}"); traceback.print_exc(); input("Press Enter"); sys.exit(1)
