"""First-connect history import."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable

from app.mt5.gateway import MT5Gateway
from app.mt5.types import Deal
from app.observability import get_logger

logger = get_logger("mt5.history_sync")


class HistorySync:
    """Import full history in 90-day chunks."""

    def import_full_history(
        self,
        gateway: MT5Gateway,
        account_login: int,  # noqa: ARG002
        progress_cb: Callable[[float], None] | None = None,
    ) -> list[Deal]:
        # check max bars setting
        try:
            fut = gateway.terminal_info()
            tinfo = fut.result(timeout=5)
            if tinfo is not None:
                # terminal_info doesn't expose max bars directly; log warning if needed
                logger.info(f"Terminal build {tinfo.build} — checking history availability")
        except Exception:
            pass

        now = dt.datetime.now(tz=dt.UTC)
        # start from 10 years ago (or account creation)
        start = now - dt.timedelta(days=365 * 10)
        chunk = dt.timedelta(days=90)
        all_deals: list[Deal] = []
        total_chunks = max(1, int((now - start) / chunk) + 1)
        current = start
        idx = 0
        while current < now:
            chunk_end = min(current + chunk, now)
            try:
                deals_fut = gateway.history_deals_get(current, chunk_end)
                deals = deals_fut.result(timeout=65)
                if deals:
                    all_deals.extend(deals)
            except Exception as exc:
                logger.warning(f"history_deals_get failed for {current}..{chunk_end}: {exc}")
            idx += 1
            if progress_cb:
                progress_cb(idx / total_chunks)
            current = chunk_end

        # warn if history too short
        if len(all_deals) < 100:
            logger.warning(
                f"History too short for training/backtesting: only {len(all_deals)} deals (max bars setting may be low)"
            )

        logger.info(f"Imported {len(all_deals)} deals")
        return all_deals
