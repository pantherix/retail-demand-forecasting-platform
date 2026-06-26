import os
import sqlite3
from datetime import datetime
from pathlib import Path


def get_db_path():
    import sys
    root = Path(__file__).resolve().parents[2]
    is_testing = (
        "pytest" in sys.modules
        or os.getenv("TESTING", "false").lower() == "true"
        or (len(sys.argv) > 0 and "pytest" in sys.argv[0])
    )
    db_name = "retailgpt_test.db" if is_testing else "retailgpt.db"
    return root / db_name


def get_backup_dir():
    root = Path(__file__).resolve().parents[2]
    backup_dir = root / "data" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def prune_old_backups(keep_count: int = 5):
    backup_dir = get_backup_dir()
    backups = sorted(backup_dir.glob("retailgpt_backup_*.db"), key=os.path.getmtime)
    if len(backups) > keep_count:
        for old_backup in backups[:-keep_count]:
            try:
                old_backup.unlink()
                print(f"[BACKUP ROTATION] Deleted old backup: {old_backup.name}")
            except Exception as e:
                print(f"[BACKUP ROTATION ERROR] Could not delete {old_backup.name}: {e}")


def create_backup() -> str:
    db_path = get_db_path()
    backup_dir = get_backup_dir()

    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found at {db_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"retailgpt_backup_{timestamp}.db"
    backup_path = backup_dir / backup_filename

    # Use SQLite's online backup API to prevent corruption if database is actively being written to
    src_conn = sqlite3.connect(str(db_path))
    dest_conn = sqlite3.connect(str(backup_path))
    try:
        src_conn.backup(dest_conn)
        print(f"[BACKUP SUCCESS] Created timestamped backup at: {backup_path}")
        prune_old_backups(keep_count=5)
    finally:
        dest_conn.close()
        src_conn.close()

    return str(backup_path)


def verify_backup(backup_file: str) -> bool:
    if not os.path.exists(backup_file):
        print(f"[VERIFICATION FAILED] Backup file does not exist: {backup_file}")
        return False

    try:
        conn = sqlite3.connect(backup_file)
        cursor = conn.cursor()
        # Run integrity check
        cursor.execute("PRAGMA integrity_check;")
        res = cursor.fetchone()
        conn.close()

        if res and res[0] == "ok":
            print(
                f"[VERIFICATION SUCCESS] Backup file integrity verified: {backup_file}"
            )
            return True
        else:
            print(f"[VERIFICATION FAILED] Integrity check returned: {res}")
            return False
    except Exception as e:
        print(f"[VERIFICATION FAILED] SQLite headers/integrity corrupt: {e}")
        return False


def restore_backup(backup_file: str) -> bool:
    db_path = get_db_path()

    if not os.path.exists(backup_file):
        raise FileNotFoundError(f"Backup file not found: {backup_file}")

    if not verify_backup(backup_file):
        raise ValueError("Cannot restore from a corrupt backup file.")

    # Online restore
    src_conn = sqlite3.connect(backup_file)
    dest_conn = sqlite3.connect(str(db_path))
    try:
        src_conn.backup(dest_conn)
        print(f"[RESTORE SUCCESS] Database restored from backup: {backup_file}")
        return True
    finally:
        dest_conn.close()
        src_conn.close()


if __name__ == "__main__":
    # Test run
    try:
        print("Running backup system test...")
        b_file = create_backup()
        verify_backup(b_file)
    except Exception as e:
        print(f"Error during backup test: {e}")
