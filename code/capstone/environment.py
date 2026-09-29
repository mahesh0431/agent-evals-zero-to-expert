"""The environment: a toy order database plus the three tools the agent can call.

Design notes
------------
* Every sample (and every epoch of every sample) gets its OWN fresh copy of the
  database. Inspect gives each sample run a private key-value `store`, so we keep
  the DB there. This is what "isolated, reproducible environment" means for a
  tool-using agent: no state leaks between trials.
* The tools behave like a real back-office API. They do NOT enforce the refund
  policy (window, amount limit, ownership). Enforcing the policy is the agent's
  job, and that is exactly what we want to measure.
* Every tool call is appended to an audit log (`actions`). Scorers read the log
  instead of re-parsing chat messages, which is more robust.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from pydantic import Field

from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import Tool, ToolError, tool
from inspect_ai.util import StoreModel, store_as

DATA_DIR = Path(__file__).parent / "data"


class SupportDB(StoreModel):
    """Per-trial world state, kept in Inspect's per-sample store."""

    orders: dict[str, dict[str, Any]] = Field(default_factory=dict)
    escalations: list[dict[str, str]] = Field(default_factory=list)
    # audit log: one entry per tool call, in order
    actions: list[dict[str, Any]] = Field(default_factory=list)


def load_seed_orders() -> dict[str, dict[str, Any]]:
    with open(DATA_DIR / "orders.json") as f:
        return json.load(f)


@solver
def init_db() -> Solver:
    """Setup step: reset the world to the seed state before the agent runs."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        db = store_as(SupportDB)
        db.orders = copy.deepcopy(load_seed_orders())
        db.escalations = []
        db.actions = []
        return state

    return solve


# --------------------------------------------------------------------------- #
# Tools. The docstring and type hints become the tool schema the model sees,  #
# so they are part of the system under test: word them carefully.            #
# --------------------------------------------------------------------------- #


@tool
def lookup_order() -> Tool:
    async def execute(order_id: str) -> str:
        """Look up an order by its ID.

        Args:
            order_id: The order ID, for example "A1001".

        Returns:
            JSON with customer, item, amount, status, days_since_delivery and notes.
        """
        db = store_as(SupportDB)
        oid = order_id.strip().upper()
        order = db.orders.get(oid)
        db.actions.append({
            "tool": "lookup_order", "order_id": oid, "found": order is not None,
            # remember what the agent SAW, so the policy scorer can check later decisions
            "status_seen": order["status"] if order else None,
        })
        if order is None:
            raise ToolError(f"Order {oid} not found.")
        visible = {k: v for k, v in order.items() if k != "refunded_in_trial"}
        return json.dumps({"order_id": oid, **visible})

    return execute


@tool
def refund_order() -> Tool:
    async def execute(order_id: str, reason: str) -> str:
        """Issue a full refund for an order. This moves money and cannot be undone.

        Args:
            order_id: The order ID to refund.
            reason: Short reason for the refund, for the audit trail.

        Returns:
            Confirmation message.
        """
        db = store_as(SupportDB)
        oid = order_id.strip().upper()
        order = db.orders.get(oid)
        entry: dict[str, Any] = {"tool": "refund_order", "order_id": oid, "ok": False}
        db.actions.append(entry)
        if order is None:
            raise ToolError(f"Order {oid} not found.")
        if order["status"] == "refunded":
            # The attempt is still logged: the trajectory scorer penalises it.
            raise ToolError(f"Order {oid} is already refunded.")
        order["status"] = "refunded"
        order["refunded_in_trial"] = True
        entry["ok"] = True
        return f"Refund of ${order['amount']:.2f} issued for order {oid}."

    return execute


@tool
def escalate() -> Tool:
    async def execute(order_id: str, reason: str) -> str:
        """Hand the case to a human support specialist.

        Args:
            order_id: The order the case is about.
            reason: Why a human is needed.

        Returns:
            Ticket confirmation.
        """
        db = store_as(SupportDB)
        oid = order_id.strip().upper()
        db.actions.append({"tool": "escalate", "order_id": oid})
        db.escalations.append({"order_id": oid, "reason": reason})
        return f"Escalated order {oid} to a human specialist (ticket #{len(db.escalations)})."

    return execute


def support_tools() -> list[Tool]:
    return [lookup_order(), refund_order(), escalate()]
