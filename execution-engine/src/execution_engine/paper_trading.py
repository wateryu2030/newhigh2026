# Auto-fixed by Cursor on 2026-04-02: paper trading shim with latency + partial fill simulation.
"""模拟盘增强：延迟、部分成交；底层仍复用 DuckDB simulated 步进。"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

_log = logging.getLogger(__name__)


@dataclass
class PaperTradingConfig:
    latency_ms: int = 50
    partial_fill_prob: float = 0.0
    partial_fill_ratio: float = 1.0


def paper_step(
    cfg: Optional[PaperTradingConfig] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    调用 step_simulated 前模拟网络延迟；partial_fill_prob>0 时随机降低有效手数。
    """
    cfg = cfg or PaperTradingConfig()
    if cfg.latency_ms > 0:
        time.sleep(min(cfg.latency_ms, 2000) / 1000.0)
    lot = int(kwargs.get("lot_size", 100) or 100)
    if cfg.partial_fill_prob > 0 and random.random() < cfg.partial_fill_prob:
        lot = max(1, int(lot * cfg.partial_fill_ratio))
        kwargs["lot_size"] = lot
    try:
        from .simulated import step_simulated

        out = step_simulated(**kwargs)
        out["paper_latency_ms"] = cfg.latency_ms
        out["paper_partial_used"] = lot
        return out
    except Exception as e:
        _log.exception("paper_step failed")
        return {"ok": False, "error": str(e)}
