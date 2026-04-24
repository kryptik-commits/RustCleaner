#!/usr/bin/env python3
"""
RustCleaner - Minimal + Robust
Default: Interactive. PC rename forced (custom input or auto for --batch).
Flags: --dry-run, --batch, --full-wipe
"""
import argparse, ctypes, datetime, fnmatch, logging, os, random, shutil, string, subprocess, sys, time, traceback, winreg
from pathlib import Path
from typing import Optional

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

# ── Error Logging ────────────────────────────────────────────────────
def _log_error(error: Exception, context: str = ""):
    """Log detailed error information for user support"""
    error_log = Path(__file__).parent / "rust_clean_error.log"
    timestamp = datetime.datetime.now().isoformat()

    # Gather system info
    import platform
    sys_info = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hostname": platform.node(),
        "cwd": os.getcwd(),
        "script_path": str(Path(__file__).resolve()),
        "arguments": sys.argv,
        "environment": {
            "APPDATA": os.environ.get("APPDATA", "N/A"),
            "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", "N/A"),
            "TEMP": os.environ.get("TEMP", "N/A"),
            "TMP": os.environ.get("TMP", "N/A"),
            "PROGRAMDATA": os.environ.get("PROGRAMDATA", "N/A"),
            "WINDIR": os.environ.get("WINDIR", "N/A"),
        }
    }

    error_details = {
        "type": type(error).__name__,
        "message": str(error),
        "context": context,
        "traceback": traceback.format_exc(),
    }

    log_content = f"""
{'='*70}
ERROR REPORT - {timestamp}
{'='*70}

SYSTEM INFORMATION:
 Python Version: {sys_info['python_version']}
 Platform: {sys_info['platform']}
 Machine: {sys_info['machine']}
 Processor: {sys_info['processor']}
 Hostname: {sys_info['hostname']}
 Working Directory: {sys_info['cwd']}
 Script Path: {sys_info['script_path']}

COMMAND LINE ARGUMENTS:
 {' '.join(sys_info['arguments'])}

ENVIRONMENT VARIABLES:
 APPDATA: {sys_info['environment']['APPDATA']}
 LOCALAPPDATA: {sys_info['environment']['LOCALAPPDATA']}
 TEMP: {sys_info['environment']['TEMP']}
 TMP: {sys_info['environment']['TMP']}
 PROGRAMDATA: {sys_info['environment']['PROGRAMDATA']}
 WINDIR: {sys_info['environment']['WINDIR']}

ERROR DETAILS:
 Type: {error_details['type']}
 Message: {error_details['message']}
 Context: {error_details['context']}

FULL TRACEBACK:
{error_details['traceback']}

{'='*70}
END OF ERROR REPORT
{'='*70}
"""

    try:
        with open(error_log, "w", encoding="utf-8") as f:
            f.write(log_content)
        logger.error(f"Error logged to: {error_log}")
        print(f"\n [!] An error occurred. Details saved to: rust_clean_error.log")
        print(f" Please send this file to support for assistance.")
    except Exception as log_err:
        print(f"\n [!] CRITICAL: Failed to write error log: {log_err}")
        print(f" Original error: {error}")
        traceback.print_exc()

# ── File Logging ────────────────────────────────────────────────────
LOG_FILE = Path(__file__).parent / "rust_clean.log"
logger = logging.getLogger("rc")
logger.setLevel(logging.INFO)
try:
    fh = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger.addHandler(fh)
except Exception as e:
    logger.warning(f"Logging setup failed: {e}")  # FIX: bare except → logged warning

# ── Helpers ─────────────────────────────────────────────────────────
def env_path(var: str) -> Optional[Path]:
    v = os.environ.get(var)
    return Path(v) if v else None

def _rm(p: Path, dry: bool, label: str = "") -> bool:
    if not p.exists(): return False
    msg = f"{p} ({label})" if label else str(p)
    if dry:
        print(f" [DRY] Would delete: {msg}"); logger.info(f"[DRY] {p}")
        return True
    try:
        shutil.rmtree(p) if p.is_dir() else p.unlink()
        print(f" ✓ Deleted: {p}"); logger.info(f"Deleted: {p}")
        return True
    except PermissionError: print(f" [!] Locked: {p}"); return False
    except Exception as e: print(f" [!] Failed: {p} — {e}"); return False

def _prompt(msg: str, interactive: bool, dry: bool) -> bool:
    if dry: return True
    if not interactive: return True
    while True:
        ans = input(f"{msg} [y/N]: ").strip().lower()
        if ans in ("y", "yes"): return True
        if ans in ("", "n", "no"): return False
        print(" [?] Answer 'y' or 'n'")

def _validate_pc_name(name: str) -> bool:
    return 1 <= len(name) <= 15 and name[0] != '-' and name[-1] != '-' and all(c.isalnum() or c == '-' for c in name)

def _get_pc_name(dry: bool, batch: bool) -> str:
    if dry: return "DRYRUN-PC"
    if batch: return f"WIN-{''.join(random.choices(string.ascii_uppercase + string.digits, k=7))}"
    print(" PC rename is REQUIRED. (1-15 chars, alphanumeric/hyphens, no leading/trailing hyphens)")
    while True:
        name = input(" New PC name: ").strip()
        if _validate_pc_name(name): return name
        print(" [!] Invalid name. Follow rules above and try again.")

def _section(title: str): print(f"\n── {title} " + "─"*(45-len(title))); logger.info(title)
def _log_status(ok: bool, msg: str): print(f" {'✓' if ok else '✗'} {msg}"); logger.info(f"{'OK' if ok else 'FAIL'}: {msg}")

def _confirm(dry: bool, full_wipe: bool, pc_name: str) -> bool:
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
        print(" [?] Answer 'y' or 'n'")

def _print_next_steps(dry: bool, full_wipe: bool, pc_name: str):
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
    for proc in PROCS:
        if dry: print(f" [DRY] Would kill: {proc}"); continue
        try:
            r = subprocess.run(["taskkill","/F","/IM",proc], capture_output=True, timeout=10)
            _log_status(r.returncode == 0, f"Killed {proc}")
        except subprocess.TimeoutExpired:
            err_msg = f"Timeout killing {proc}"
            _log_status(False, err_msg)
            logger.error(err_msg)
        except Exception as e:
            err_msg = f"Error killing {proc}: {e}"
            _log_status(False, err_msg)
            logger.error(err_msg, exc_info=True)
        time.sleep(0.5)

def _find_steam():
    dirs = set()
    default = Path(r"C:\Program Files (x86)\Steam")
    if default.exists(): dirs.add(default)
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam") as k:
            p = Path(winreg.QueryValueEx(k, "InstallPath")[0])
            if p.exists(): dirs.add(p)
    except Exception as e:
        err_msg = f"Registry Steam lookup failed: {e}"
        print(f" [!] {err_msg}")
        logger.error(err_msg, exc_info=True)
    for sdir in list(dirs):
        vdf = sdir / "steamapps" / "libraryfolders.vdf"
        if not vdf.exists(): continue
        try:
            for line in vdf.read_text(errors="ignore").splitlines():
                if '"path"' in line.lower():
                    parts = line.split('"')
                    if len(parts) >= 4:
                        # FIX: unterminated string literal → proper escape
                        p = Path(parts[3].replace("\\\\", "\\"))
                        if p.exists(): dirs.add(p)
                    else: print(f" [!] Malformed VDF line: {line[:50]}...")
        except Exception as e:
            err_msg = f"Failed to parse VDF: {e}"
            print(f" [!] {err_msg}")
            logger.error(err_msg, exc_info=True)
    return list(dirs)

def _clean_steam(dirs, dry: bool, interactive: bool):
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
            (s/"steamapps/common"/RUST_DIR/"RustClient_Data"/"il2cpp_cache", "il2cpp cache"),
            (s/"steamapps/common"/RUST_DIR/"RustClient_Data"/"ScriptCache", "script cache"),
            (s/"steamapps/common"/RUST_DIR/"EasyAntiCheat", "Game EAC folder"),
        ]
        for path, label in targets: _rm(path, dry, label)

        ud = s/"steamapps"/"userdata"
        if ud.exists():
            try:
                for u in ud.iterdir():
                    if not u.is_dir(): continue
                    _rm(u/RUST, dry, "Userdata/Rust")
                    _rm(u/"760"/"remote"/RUST, dry, "Steam Cloud/Remote")
                    try:
                        for stray in u.iterdir():
                            if any(k in stray.name.lower() for k in ["rust", "facepunch"]):
                                _rm(stray, dry, "Stray Facepunch/Rust")
                    except PermissionError: pass
            except PermissionError: pass

    for root_env in ("APPDATA","LOCALAPPDATA"):
        root = env_path(root_env)
        if not root or not root.exists(): continue
        for sub in ["Steam/htmlcache","Steam/logs","Steam/dumps"]: _rm(root/sub, dry, f"{root_env}/Steam/{sub.split('/')[-1]}")
        ud = root/"Steam"/"userdata"
        if ud.exists():
            try:
                for u in ud.iterdir():
                    if u.is_dir(): _rm(u/RUST, dry, f"{root_env}/Userdata/Rust")
            except PermissionError: pass

def _clean_steam_profile_identifiers(dry: bool, interactive: bool):
    if not _prompt("Clean Rust cloud/screenshot data?", interactive, dry): return
    for root_env in ("APPDATA","LOCALAPPDATA"):
        root = env_path(root_env)
        if not root or not root.exists(): continue
        for sub in [f"Steam/remote/{RUST}", f"Steam/screenshots/{RUST}"]:
            _rm(root/sub, dry, f"{root_env}/{sub}")

def _clean_eac(dry: bool, interactive: bool):
    if not _prompt("Delete EAC services & folders?", interactive, dry): return
    for svc in ["EasyAntiCheat","EasyAntiCheat_EOS"]:
        if dry: print(f" [DRY] Would stop/delete service: {svc}"); continue
        try:
            r = subprocess.run(["sc","stop",svc], capture_output=True, timeout=15)
            if r.returncode != 0: print(f" [!] Failed to stop: {svc}"); continue
            r = subprocess.run(["sc","delete",svc], capture_output=True, timeout=15)
            _log_status(r.returncode == 0, f"Removed service {svc}")
        except subprocess.TimeoutExpired:
            err_msg = f"Timeout on {svc}"
            _log_status(False, err_msg)
            logger.error(err_msg)
        except Exception as e:
            err_msg = f"Error on {svc}: {e}"
            _log_status(False, err_msg)
            logger.error(err_msg, exc_info=True)
    eac = Path(r"C:\Program Files (x86)\EasyAntiCheat_EOS\EasyAntiCheat_EOS.exe")
    if eac.exists() and not dry:
        try:
            r = subprocess.run([str(eac),"qa-factory-reset"], capture_output=True, timeout=30)
            _log_status(r.returncode == 0, "EAC factory reset")
        except Exception as e:
            err_msg = f"EAC reset error: {e}"
            _log_status(False, err_msg)
            logger.error(err_msg, exc_info=True)
    _appdata = env_path("APPDATA")
    _localappdata = env_path("LOCALAPPDATA")
    eac_paths = [
        (Path(r"C:\Program Files (x86)\EasyAntiCheat_EOS"), "EAC ProgramFiles"),
        (_appdata / "EasyAntiCheat" if _appdata else None, "EAC AppData"),
        (_localappdata / "EasyAntiCheat" if _localappdata else None, "EAC LocalAppData"),
        (Path(os.environ.get("PROGRAMDATA",r"C:\ProgramData")) / "EasyAntiCheat", "EAC ProgramData"),
        (Path(r"C:\Users\Public\EasyAntiCheat"), "EAC Public"),
        (Path(os.environ.get("WINDIR",r"C:\Windows")) / "Temp/EasyAntiCheat", "EAC Temp"),
    ]
    for p, label in eac_paths:
        if p: _rm(p, dry, label)

def _clean_temp(dry: bool, interactive: bool):
    if not _prompt("Clean temp/prefetch files?", interactive, dry): return
    pats = [f"*{x}*" for x in ["rust","steam","easyanticheat","facepunch",RUST]]
    _localappdata = env_path("LOCALAPPDATA")
    temp_dirs = [env_path("TEMP"), env_path("TMP"), _localappdata/"Temp" if _localappdata else None, Path(os.environ.get("WINDIR",r"C:\Windows"))/"Temp"]
    for td in [d for d in temp_dirs if d]:
        if not td.exists(): continue
        try:
            for i in td.iterdir():
                if any(fnmatch.fnmatch(i.name.lower(), p) for p in pats): _rm(i, dry, f"Temp/{i.name}")
        except PermissionError: pass
    pf = Path(r"C:\Windows\Prefetch")
    if pf.exists():
        prefetch_exes = [
            "RUST.EXE", "RUSTCLIENT.EXE",
            "STEAM.EXE", "STEAMSERVICE.EXE", "STEAMWEBHELPER.EXE",
            "STEAMERRORREPORTER64.EXE", "STEAMSYSINFO.EXE",
            "EASYANTICHEAT.EXE", "EASYANTICHEAT_EOS.EXE", "EASYANTICHEAT_SETUP.EXE",
        ]
        for exe in prefetch_exes:
            for m in pf.glob(f"{exe}-*.pf"): _rm(m, dry, f"Prefetch/{m.name}")

def _clean_reg(dry: bool, interactive: bool):
    if not _prompt(f"Delete {len(REG_KEYS)} registry keys (EAC/Facepunch/Steam)?", interactive, dry): return
    for hive, sub in REG_KEYS:
        hive_str = "HKLM" if hive==winreg.HKEY_LOCAL_MACHINE else "HKCU"
        full = f"{hive_str}\\{sub}"
        if dry: print(f" [DRY] Would delete reg: {full}"); continue
        try:
            with winreg.OpenKey(hive, sub): pass
            r = subprocess.run(["reg","delete",full,"/f"], capture_output=True, timeout=30)
            # FIX: defensive split for log message
            key_name = sub.split('\\')[-1] if '\\' in sub else sub
            _log_status(r.returncode == 0, f"Reg {key_name}")
        except FileNotFoundError: pass
        except Exception as e:
            err_msg = f"Reg error {full}: {e}"
            print(f" [!] {err_msg}")
            logger.error(err_msg, exc_info=True)

def _clean_gpu_wer_tasks(dry: bool, interactive: bool):
    if not _prompt("Clean GPU caches, WER reports, tasks?", interactive, dry): return
    _localappdata = env_path("LOCALAPPDATA")
    gpu_subs = ["NVIDIA/GLCache","NVIDIA/DXCache","NVIDIA/ShaderCache","AMD/DxCache","AMD/DXCache","AMD/ShaderCache","Intel/GLCache","Intel/DXCache","Intel/ShaderCache","D3DSCache","D3DSCache/UserData"]
    for k in ("APPDATA","LOCALAPPDATA"):
        base = env_path(k)
        if not base: continue
        for p in gpu_subs:
            d = base/p
            if d.exists():
                try:
                    for i in d.iterdir():
                        if any(fnmatch.fnmatch(i.name.lower(), x) for x in ["*rust*","*steam*","*easyanticheat*","*facepunch*"]): _rm(i, dry, f"GPU/{i.name}")
                except PermissionError: pass
    for base in [_localappdata/"Microsoft/Windows/WER" if _localappdata else None, Path(r"C:\ProgramData\Microsoft\Windows\WER")]:
        if not base: continue
        for sub in ["ReportArchive","ReportQueue"]:
            d = base/sub
            if d.exists():
                try:
                    for i in d.iterdir():
                        if any(x in i.name.lower() for x in ["rust","steam","easyanticheat","facepunch"]): _rm(i, dry, f"WER/{i.name}")
                except PermissionError: pass
    for task in ["EasyAntiCheat","Microsoft\Windows\EasyAntiCheat"]:
        if dry: print(f" [DRY] Would delete task: {task}"); continue
        try:
            r = subprocess.run(["schtasks","/Delete","/TN",task,"/F"], capture_output=True, timeout=30)
            _log_status(r.returncode == 0, f"Task {task}")
        except Exception as e:
            err_msg = f"Task error {task}: {e}"
            print(f" [!] {err_msg}")
            logger.error(err_msg, exc_info=True)

def _rename_pc(dry: bool, name: str) -> None:
    if dry or not name: return
    print(f" Renaming PC to: {name}...")
    try:
        r = subprocess.run(["powershell","-NoProfile","-Command",f"Rename-Computer -NewName '{name}' -Force"], capture_output=True, text=True, timeout=30)
        _log_status(r.returncode == 0, "PC renamed")
    except Exception as e:
        err_msg = f"PC rename error: {e}"
        _log_status(False, err_msg)
        logger.error(err_msg, exc_info=True)

# ── Main Execution ──────────────────────────────────────────────────
def main():
    start = datetime.datetime.now()
    p = argparse.ArgumentParser(description="RustCleaner: Minimal + Robust")
    p.add_argument("--dry-run", action="store_true", help="Preview only")
    p.add_argument("--batch", action="store_true", help="Skip prompts")
    p.add_argument("--full-wipe", action="store_true", help="Delete game folder")
    args = p.parse_args()

    is_interactive = len(sys.argv) == 1 or not args.batch
    if not args.dry_run and not ctypes.windll.shell32.IsUserAnAdmin():
        script = str(Path(sys.argv[0]).resolve())
        safe_args = " ".join(f'"{a}"' if " " in a else a for a in sys.argv[1:])
        result = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {safe_args}', None, 1)
        if result <= 32:
            print(f"\n[!] Elevation failed or was cancelled (code {result}). Please run as Administrator manually.")
            input("Press Enter to exit")
            sys.exit(0)

    # ── Banner ───────────────────────────────────────────────────────
    print("=" * 60)
    print(" HARAM CLEANER - NBT EDITION")
    print("=" * 60)
    print()
    print(" This tool helps clean Rust-related files and traces from your system.")
    print("-" * 60)

    # ── Interactive menu (overrides CLI flags if running interactively) ──
    if is_interactive and not args.batch:
        print()
        print(" OPTION 1: DRY-RUN MODE (recommended for first use)")
        print("-" * 60)
        print(" → Dry-run shows what would be deleted without actually deleting anything.")
        print()
        dry_ans = input(" ? Enable DRY-RUN mode (preview only)? (y/n): ").strip().lower()
        if "--dry-run" not in sys.argv:
            args.dry_run = dry_ans in ("y", "yes")
        print()
        print(" OPTION 2: CLEANING MODE")
        print("-" * 60)
        print(" → SMART MODE (recommended): Cleans identifiers but keeps the ~50GB game files.")
        print(" → FULL-WIPE MODE: Deletes everything including the game (requires re-download).")
        print()
        wipe_ans = input(" ? Use FULL-WIPE mode (delete the entire game)? (y/n): ").strip().lower()
        if "--full-wipe" not in sys.argv:
            args.full_wipe = wipe_ans in ("y", "yes")
        print()
        print("=" * 60)

    dry = args.dry_run
    mode = "[DRY-RUN] " if dry else ""
    print(f"{mode}RustCleaner: Starting...")
    logger.info("=== Run Started ===")

    steam = _find_steam()
    if not steam: print("ERROR: Steam not found"); input("Press Enter"); return
    print(f"{mode}Found {len(steam)} Steam install(s)")

    pc_name = _get_pc_name(dry, args.batch)
    if not dry and not _confirm(dry, args.full_wipe, pc_name): input("Press Enter"); return

    _section("Killing Processes"); _kill(dry)
    _section("Cleaning Steam"); _clean_steam(steam, dry, is_interactive)
    _section("Cleaning Profiles"); _clean_steam_profile_identifiers(dry, is_interactive)
    _section("Cleaning EAC"); _clean_eac(dry, is_interactive)
    _section("Cleaning Temp"); _clean_temp(dry, is_interactive)
    _section("Cleaning Registry"); _clean_reg(dry, is_interactive)
    _section("Cleaning GPU/WER"); _clean_gpu_wer_tasks(dry, is_interactive)

    if args.full_wipe and _prompt("DELETE Rust game folder?", is_interactive, dry):
        for s in steam: _rm(s/"steamapps/common"/RUST_DIR, dry, "Full game folder")
        print(f"{mode}Full wipe: Game folder {'would be' if dry else ''} deleted")

    # PC Rename (applied after cleaning, queued for reboot)
    _rename_pc(dry, pc_name)

    _print_next_steps(dry, args.full_wipe, pc_name)

    # Auto-reboot prompt (strictly at the end)
    if not dry and input("\n Reboot now? [y/N]: ").strip().lower() in ("y","yes"):
        subprocess.run(["shutdown","/r","/t","10"], timeout=15)

    elapsed = (datetime.datetime.now() - start).seconds
    logger.info(f"=== Run Complete ({elapsed}s) ===")
    input("Press Enter")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\n⚠ Cancelled by user (Ctrl+C)"); sys.exit(0)
    except Exception as e:
        _log_error(e, "Main execution")
        print(f"\n❌ Unexpected error: {e}")
        traceback.print_exc()
        input("Press Enter")
        sys.exit(1)
