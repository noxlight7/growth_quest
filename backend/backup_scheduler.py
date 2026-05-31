import os
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
import subprocess

_LOCK = threading.Lock()
_STARTED = False


def _should_start():
    if os.environ.get("DISABLE_LOCAL_BACKUPS") == "1":
        return False
    if os.environ.get("RUN_MAIN") != "true":
        return False
    if "runserver" not in sys.argv:
        return False
    return True


def _backup_dir():
    from django.conf import settings

    default_dir = Path(settings.BASE_DIR).parent / "backups"
    return Path(os.environ.get("BACKUP_DIR", default_dir))


def _run_backup():
    backup_dir = _backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)

    db_host = os.environ.get("POSTGRES_HOST", "localhost")
    db_port = os.environ.get("POSTGRES_PORT", "5432")
    db_name = os.environ.get("POSTGRES_DB", "app_db")
    db_user = os.environ.get("POSTGRES_USER", "app_user")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"{db_name}_{timestamp}.sql.gz"

    env = os.environ.copy()
    env["PGPASSWORD"] = os.environ.get("POSTGRES_PASSWORD", "")

    dump_cmd = ["pg_dump", "-h", db_host, "-p", db_port, "-U", db_user, db_name]
    try:
        with backup_file.open("wb") as out_file:
            dump_proc = subprocess.Popen(dump_cmd, stdout=subprocess.PIPE, env=env)
            gzip_proc = subprocess.Popen(["gzip", "-c"], stdin=dump_proc.stdout, stdout=out_file)
            if dump_proc.stdout:
                dump_proc.stdout.close()
            dump_rc = dump_proc.wait()
            gzip_rc = gzip_proc.wait()
            if dump_rc != 0 or gzip_rc != 0:
                print("[backup] pg_dump/gzip failed", flush=True)
                if backup_file.exists():
                    backup_file.unlink(missing_ok=True)
                return
    except FileNotFoundError:
        print("[backup] pg_dump not found; install postgres client tools", flush=True)
        return
    except Exception as exc:
        print(f"[backup] failed: {exc}", flush=True)
        return

    backups = sorted(backup_dir.glob("*.sql.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[7:]:
        try:
            old.unlink()
        except OSError:
            continue

    print(f"[backup] created {backup_file}", flush=True)


def _seconds_until(hour=3, minute=0):
    now = datetime.now()
    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)
    return (next_run - now).total_seconds()


def _scheduler_loop():
    _run_backup()
    while True:
        time.sleep(_seconds_until(3, 0))
        _run_backup()


def start_backup_scheduler():
    global _STARTED
    if not _should_start():
        return
    with _LOCK:
        if _STARTED:
            return
        _STARTED = True
    thread = threading.Thread(target=_scheduler_loop, name="backup-scheduler", daemon=True)
    thread.start()
    print("[backup] scheduler started", flush=True)
