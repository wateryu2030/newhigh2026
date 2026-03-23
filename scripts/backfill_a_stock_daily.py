#!/usr/bin/env python3
"""
将 a_stock_daily 从「少数测试股」扩到全市场（或前 N 只），写入 quant_system.duckdb。

数据源（--source）：
- ashare_daily_kline：akshare → 东方财富。若 VPN/系统代理导致 ProxyError，可试 --no-proxy 或换 Tushare。
- tushare_daily：需 Tushare Token（项目根 `.env` 中 `TUSHARE_TOKEN`，或别名 `TUSHARE_API_KEY` / `TS_TOKEN`）。

逻辑：
- 代码列表来自 a_stock_basic（不再只认已有日线的少数股票）。
- 尚无日线：约一年历史；已有数据：从库内全局最新交易日续拉。

用法（仓库根目录，建议已激活 .venv）：

  # 东财（默认）
  python scripts/backfill_a_stock_daily.py --codes-limit 300
  python scripts/backfill_a_stock_daily.py --no-proxy --codes-limit 50

  # Tushare 渠道（VPN 下东财失败时推荐）：项目根 .env 里配置 TUSHARE_TOKEN 即可，脚本会自动加载
  python scripts/backfill_a_stock_daily.py --source tushare_daily --codes-limit 300

  # 补全「其余全部」股票（不要带 --codes-limit；已写过日 K 的只会增量续拉，不会整年重下）
  python scripts/backfill_a_stock_daily.py --source tushare_daily --all-market
  # 与上一行等价：python scripts/backfill_a_stock_daily.py --source tushare_daily

也可调用 Gateway（全市场不传 codes_limit）：
  curl -X POST 'http://127.0.0.1:8000/api/data/incremental?source_id=tushare_daily'
  curl -X POST 'http://127.0.0.1:8000/api/data/incremental?source_id=tushare_daily&codes_limit=500'

另有 collectors/tushare_daily.update_tushare_daily 可按批拉取，与 ensure_market_data 可配合使用。

若东财仍 +0 行：多为代理；除 --no-proxy 外可在 macOS 系统设置里关闭「网络代理」或对东财域名直连。
"""

from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ("data-pipeline/src",):
    p = os.path.join(ROOT, d)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)


def _strip_env_value(raw: object) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1].strip()
    return s


def _load_repo_dotenv() -> None:
    """
    加载项目根 .env。
    注意：若 shell 里曾 `export TUSHARE_TOKEN=占位符`，load_dotenv(override=False) 不会覆盖。
    因此对 Tushare 相关键会再从 .env 原文读取并 **强制写入** os.environ，以 .env 为准。
    """
    path = os.path.join(ROOT, ".env")
    if not os.path.isfile(path):
        return
    try:
        from dotenv import dotenv_values, load_dotenv

        load_dotenv(path, override=False)
        vals = dotenv_values(path) or {}
        tok = _strip_env_value(vals.get("TUSHARE_TOKEN"))
        if not tok:
            tok = _strip_env_value(vals.get("TUSHARE_API_KEY"))
        if not tok:
            tok = _strip_env_value(vals.get("TS_TOKEN"))
        if tok:
            os.environ["TUSHARE_TOKEN"] = tok
    except ImportError:
        pass


def _sync_tushare_token_alias() -> None:
    """若未从 .env 写入 TUSHARE_TOKEN，则用环境中别名补齐。"""
    if os.environ.get("TUSHARE_TOKEN", "").strip():
        return
    for alt in ("TUSHARE_API_KEY", "TS_TOKEN"):
        v = os.environ.get(alt, "").strip()
        if v:
            os.environ["TUSHARE_TOKEN"] = v
            return


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill a_stock_daily via ashare_daily_kline or tushare_daily.",
        epilog=(
            "补全全市场（约 5k+ 只，耗时可数小时）：\n"
            "  python scripts/backfill_a_stock_daily.py --source tushare_daily --all-market\n"
            "已有一部分日 K 的标的会自动走增量，不会重复拉满一年。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source",
        default="ashare_daily_kline",
        choices=["ashare_daily_kline", "tushare_daily"],
        help="ashare=东财(akshare)；tushare=api.tushare.pro，需 TUSHARE_TOKEN",
    )
    lim_group = parser.add_mutually_exclusive_group()
    lim_group.add_argument(
        "--codes-limit",
        type=int,
        default=None,
        metavar="N",
        help="只处理 a_stock_basic 按 code 排序后的前 N 只（用于试跑）",
    )
    lim_group.add_argument(
        "--all-market",
        action="store_true",
        help="处理最多 8000 只（全市场常用；与「不传 --codes-limit」等价）",
    )
    parser.add_argument(
        "--force-full",
        action="store_true",
        help="Re-fetch ~1y window for all selected symbols (slow)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable per-batch progress on stderr (default: show progress)",
    )
    parser.add_argument(
        "--request-sleep",
        type=float,
        default=0.0,
        metavar="SEC",
        help="ashare: sleep after each symbol; tushare: also used as batch pause if >0 (else 0.25s)",
    )
    parser.add_argument(
        "--no-proxy",
        action="store_true",
        help="Strip env *proxy* vars during HTTP (helps broken ProxyError on East Money / Tushare)",
    )
    parser.add_argument(
        "--tushare-chunk-size",
        type=int,
        default=None,
        metavar="N",
        help="仅 tushare_daily：每批 ts_code 数量（默认 22；接口单次约 6000 行，过大会丢历史）",
    )
    args = parser.parse_args()
    _load_repo_dotenv()
    _sync_tushare_token_alias()

    from data_pipeline import list_sources, run_incremental
    from data_pipeline.data_sources.tushare_source import _tushare_token_from_env

    if args.source not in list_sources():
        print(f"unknown source: {args.source}", file=sys.stderr)
        return 2

    kw: dict = {"verbose": not args.quiet}
    if args.codes_limit is not None:
        kw["codes_limit"] = args.codes_limit
    # --all-market：不传 codes_limit，由数据源内默认 LIMIT 8000 覆盖全表常用规模
    if args.all_market and not args.quiet:
        print(
            "全市场模式：最多约 8000 只 code；库内已有日 K 的仅续拉增量。",
            file=sys.stderr,
        )
    if args.request_sleep and args.request_sleep > 0:
        kw["request_sleep_sec"] = args.request_sleep
    if args.no_proxy:
        kw["strip_proxy_env"] = True
    if args.source == "tushare_daily" and args.tushare_chunk_size is not None:
        kw["tushare_chunk_size"] = args.tushare_chunk_size

    if args.source == "tushare_daily":
        try:
            import tushare  # noqa: F401
        except ImportError:
            print(
                "错误：当前虚拟环境未安装 tushare。请执行: pip install tushare\n"
                "或: pip install -r requirements.txt",
                file=sys.stderr,
            )
            return 1
        tok = _tushare_token_from_env()
        if not tok:
            print(
                "错误：未找到 Tushare Token。请在项目根 `.env` 中设置 TUSHARE_TOKEN=（或 TUSHARE_API_KEY / TS_TOKEN），"
                "见 https://tushare.pro/user/token",
                file=sys.stderr,
            )
            return 1
        low = tok.lower()
        if "你的tushare_token" in low or "你的token" in tok or len(tok) < 24:
            print(
                "错误：当前 TUSHARE_TOKEN 仍是占位符或过短。"
                "请检查项目根 `.env`，并执行 `unset TUSHARE_TOKEN` 清除 shell 里旧的 export 后再运行。",
                file=sys.stderr,
            )
            return 1

    n = run_incremental(args.source, force_full=args.force_full, **kw)
    print(f"rows_written: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
