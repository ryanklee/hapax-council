"""Test consent gating in sync agents."""


def test_gcalendar_sync_checks_consent():
    """gcalendar_sync must call contract_check before writing attendee data."""
    source = open("agents/gcalendar_sync.py").read()
    assert "contract_check" in source or "ConsentRegistry" in source, (
        "gcalendar_sync.py must check consent before writing attendee data"
    )


def test_gmail_sync_checks_consent():
    """gmail_sync must call contract_check before writing sender/recipient data."""
    source = open("agents/gmail_sync.py").read()
    assert "contract_check" in source or "ConsentRegistry" in source, (
        "gmail_sync.py must check consent before writing sender/recipient data"
    )
