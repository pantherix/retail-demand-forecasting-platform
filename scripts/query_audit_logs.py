import json
import sys
from pathlib import Path

WORKSPACE_BACKEND = Path(
    r"c:\Users\statu\Downloads\my projects\retail-demand-forecasting-platform\backend"
)
sys.path.insert(0, str(WORKSPACE_BACKEND))

from database.models import AuditLog
from database.session import SessionLocal


def query_audit_logs():
    db = SessionLocal()
    print("=== CRITICAL ACTIONS AUDIT LOG TRAIL ===")

    # Query distinct actions in audit logs to see coverage
    actions = db.query(AuditLog.action).distinct().all()
    print("\nDistinct Audit Actions Recorded:")
    for act in actions:
        print(f" - {act[0]}")

    # Retrieve logs for critical events
    critical_actions = [
        "login",
        "register",
        "user_create",
        "import_dataset",
        "add_note",
        "change_status",
        "assign_decision",
        "create_po",
        "approve_po",
        "submit_po",
        "create_transfer",
        "receive_transfer",
        "resolve_alert",
        "shopify_sync_po",
        "zoho_sync_po",
    ]

    print("\nRecent Critical Audit Records:")
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(15).all()
    logs_list = []
    for l in logs:
        logs_list.append(
            {
                "id": l.id,
                "user": l.user,
                "action": l.action,
                "resource": l.resource,
                "detail": l.detail,
                "timestamp": l.created_at.isoformat() if l.created_at else None,
            }
        )
    print(json.dumps(logs_list, indent=2))

    db.close()


if __name__ == "__main__":
    query_audit_logs()
