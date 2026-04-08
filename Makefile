# 缩短本地迭代闭环：常用入口集中在此（需在仓库根目录执行 make <target>）
ROOT := $(abspath .)

.PHONY: help dev-check gateway-restart pipeline-editable quant-readiness

help:
	@echo "Targets:"
	@echo "  make dev-check        - scripts/restart_and_check.sh（网关/健康等冒烟）"
	@echo "  make gateway-restart  - scripts/restart_gateway_frontend.sh"
	@echo "  make pipeline-editable - pip install -e data-pipeline（含 tushare 等依赖）"
	@echo "  make quant-readiness  - scripts/verify_quant_readiness.py（DuckDB 表与日线新鲜度）"

dev-check:
	bash $(ROOT)/scripts/restart_and_check.sh

gateway-restart:
	bash $(ROOT)/scripts/restart_gateway_frontend.sh

pipeline-editable:
	python3 -m pip install -e "$(ROOT)/data-pipeline"

quant-readiness:
	"$(ROOT)/.venv/bin/python" "$(ROOT)/scripts/verify_quant_readiness.py"
