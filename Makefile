# 缩短本地迭代闭环：常用入口集中在此（需在仓库根目录执行 make <target>）
ROOT := $(abspath .)

.PHONY: help dev-check gateway-restart pipeline-editable quant-readiness data-daily-ashare scheduler-backfill-restart sync-nav openclaw-iterate-ready openclaw-status openclaw-iteration-once openclaw-cursor-iterate openclaw-benign-loop check-openclaw-cursor-loop test-python-smoke

help:
	@echo "Targets:"
	@echo "  make dev-check        - scripts/restart_and_check.sh（网关/健康等冒烟）"
	@echo "  make gateway-restart  - scripts/restart_gateway_frontend.sh"
	@echo "  make pipeline-editable - pip install -e data-pipeline（含 tushare 等依赖）"
	@echo "  make quant-readiness  - scripts/verify_quant_readiness.py（DuckDB 表与日线新鲜度）"
	@echo "  make data-daily-ashare - scripts/run_daily_ashare_kline.sh（东财日 K 增量→DuckDB）"
	@echo "  make scheduler-backfill-restart - 停调度→回补→再起 monitor（见脚本内说明）"
	@echo "  make sync-nav         - 从 config/navigation_manifest.json 生成小程序 menu.generated.js"
	@echo "  make openclaw-iterate-ready - OpenClaw 迭代前置：workspace+HEARTBEAT+skills+自检（见 tasks/openclaw_handoff.md）"
	@echo "  make openclaw-status      - 本机 Gateway/CLI/symlink 快速探活（见 docs/OPENCLAW_REALITY_CHECK_AND_IMPROVEMENTS.md）"
	@echo "  make openclaw-iteration-once - 本机跑一轮迭代提示（内联 current_task+§2，默认 --local）"
	@echo "  make openclaw-cursor-iterate - OpenClaw 规划 + Cursor agent 执行（见 docs/OPENCLAW_PLUS_CURSOR_LOOP.md §C）"
	@echo "  make openclaw-benign-loop - 同上（脚本别名 openclaw_benign_loop.sh，§四 防循环）"
	@echo "  make check-openclaw-cursor-loop - 检查 openclaw/cursor/.env 并冒烟生成规划文件"
	@echo "  make test-python-smoke - 根目录 pytest：data_pipeline + strategy_engine + execution_engine（9 项）"

dev-check:
	bash $(ROOT)/scripts/restart_and_check.sh

gateway-restart:
	bash $(ROOT)/scripts/restart_gateway_frontend.sh

pipeline-editable:
	python3 -m pip install -e "$(ROOT)/data-pipeline"

quant-readiness:
	"$(ROOT)/.venv/bin/python" "$(ROOT)/scripts/verify_quant_readiness.py"

data-daily-ashare:
	bash "$(ROOT)/scripts/run_daily_ashare_kline.sh"

scheduler-backfill-restart:
	bash "$(ROOT)/scripts/stop_scheduler_backfill_restart.sh"

sync-nav:
	python3 "$(ROOT)/scripts/gen_miniprogram_menu.py"

openclaw-iterate-ready:
	bash "$(ROOT)/scripts/openclaw_iteration_ready.sh"

openclaw-status:
	bash "$(ROOT)/scripts/openclaw_status.sh"

openclaw-iteration-once:
	bash "$(ROOT)/scripts/openclaw_iteration_prompt_once.sh"

openclaw-cursor-iterate:
	bash "$(ROOT)/scripts/openclaw_cursor_iterate.sh"

openclaw-benign-loop:
	bash "$(ROOT)/scripts/openclaw_benign_loop.sh"

check-openclaw-cursor-loop:
	bash "$(ROOT)/scripts/check_openclaw_cursor_loop.sh"

test-python-smoke:
	@if [ -x "$(ROOT)/.venv/bin/python" ]; then \
		"$(ROOT)/.venv/bin/python" -m pytest "$(ROOT)/tests/test_data_pipeline.py" "$(ROOT)/tests/test_strategy_engine.py" "$(ROOT)/tests/test_execution_engine.py" -q; \
	else \
		python3 -m pytest "$(ROOT)/tests/test_data_pipeline.py" "$(ROOT)/tests/test_strategy_engine.py" "$(ROOT)/tests/test_execution_engine.py" -q; \
	fi
