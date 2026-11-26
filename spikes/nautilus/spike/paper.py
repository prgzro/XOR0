"""PAPER guard shared by every script that opens an execution client."""

import os
import sys
from pathlib import Path

from dotenv import dotenv_values
from ib_async import IB

HOST, PORT = "127.0.0.1", 4002  # paper Gateway only
REPO_ENV = Path(__file__).resolve().parents[3] / ".env"


def paper_account_or_exit(probe_client_id: int) -> str:
    """Return the Gateway's single DU... paper account, or exit. Never trusts code for the id."""
    for source in (dotenv_values(REPO_ENV), os.environ):
        if str(source.get("ENABLE_LIVE_TRADING", "false")).lower() == "true":
            sys.exit("refusing: ENABLE_LIVE_TRADING is true")
    ib = IB()
    ib.connect(HOST, PORT, clientId=probe_client_id, readonly=True, timeout=10)
    try:
        accounts = ib.managedAccounts()
    finally:
        ib.disconnect()
    if len(accounts) != 1 or not accounts[0].startswith("DU"):
        sys.exit(f"refusing: expected one paper DU... account, got {len(accounts)} account(s)")
    return accounts[0]
