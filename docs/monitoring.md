# 监控与告警

## Prometheus

- 配置：`monitoring/prometheus.yml` 抓取 Gateway `http://api:8000/metrics`。
- 启动（与 docker-compose 一起）：`docker compose --profile monitor up -d`，Prometheus 监听 9090。

## Grafana

1. 启动 Grafana：`docker run -d -p 3001:3000 grafana/grafana:10.2.0`
2. 登录 http://localhost:3001（默认 admin/admin），添加 Data Source → Prometheus，URL 填 `http://host.docker.internal:9090`（或宿主机 IP:9090）。
3. 导入 Dashboard：可新建 Panel，查询 `http_requests_total` 等（需 Gateway 使用 prometheus_client 暴露指标）。

## 告警（可选）

在 `monitoring/prometheus.yml` 中配置 `alerting` 与 `rule_files`，或使用 Alertmanager。示例规则见 `monitoring/alert_rules.example.yml`。

## 本地开发

非 Docker 时，Prometheus 可抓取本机：将 `api:8000` 改为 `127.0.0.1:8000`，并确保 Gateway 已启动且 `/metrics` 可访问。
