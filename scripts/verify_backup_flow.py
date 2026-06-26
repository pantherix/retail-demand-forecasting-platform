import sys
from pathlib import Path

WORKSPACE_BACKEND = Path(
    r"c:\Users\statu\Downloads\my projects\retail-demand-forecasting-platform\backend"
)
sys.path.insert(0, str(WORKSPACE_BACKEND))

from database.backup import create_backup, restore_backup
from database.models import Product
from database.session import SessionLocal


def verify_backup_restore_cycle():
    print("=== STARTING BACKUP & RESTORE LIFECYCLE TEST ===")

    # 1. Create backup of current database state
    try:
        backup_file = create_backup()
    except Exception as e:
        print(f"Failed to create backup: {e}")
        sys.exit(1)

    # 2. Insert test record in database
    db = SessionLocal()
    temp_sku = "SKU-BACKUP-TEST"

    # Ensure it doesn't exist already
    old_prod = db.query(Product).filter(Product.sku == temp_sku).first()
    if old_prod:
        db.delete(old_prod)
        db.commit()

    print(f"\nInserting temporary record: {temp_sku}...")
    new_prod = Product(
        sku=temp_sku,
        name="Backup Verification Item",
        category="Testing",
        base_price=10.0,
        unit_cost=5.0,
    )
    db.add(new_prod)
    db.commit()

    inserted_prod = db.query(Product).filter(Product.sku == temp_sku).first()
    if inserted_prod:
        print(
            f"Record successfully created: {inserted_prod.sku} (ID: {inserted_prod.id})"
        )
    else:
        print("Failed to insert record.")
        db.close()
        sys.exit(1)
    db.close()

    # 3. Restore backup
    print(f"\nRestoring database from backup: {backup_file}...")
    try:
        restore_backup(backup_file)
    except Exception as e:
        print(f"Restore failed: {e}")
        sys.exit(1)

    # 4. Verify database state is recovered (temp record should not exist)
    db_after = SessionLocal()
    check_prod = db_after.query(Product).filter(Product.sku == temp_sku).first()
    db_after.close()

    if check_prod is None:
        print(
            "\nVerification: Temporary test record is GONE. Reversion verified successfully."
        )
        print("[RESULT] PASS")
    else:
        print(
            f"\nVerification: Temporary test record STILL EXISTS: {check_prod.sku}. Reversion failed."
        )
        print("[RESULT] FAIL")
        sys.exit(1)


if __name__ == "__main__":
    verify_backup_restore_cycle()
