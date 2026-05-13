"""使 ``python -m rumor_capture`` 能够执行 CLI 入口。"""

from rumor_capture.fetcher import main

if __name__ == "__main__":
    import sys

    sys.exit(main())
