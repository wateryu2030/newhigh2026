"""使 ``python -m financial_report`` 能够执行 CLI 入口。"""

from financial_report.fetcher import main

if __name__ == "__main__":
    import sys

    sys.exit(main())
