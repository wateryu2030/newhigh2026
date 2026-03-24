"""
财报分析器

分析财报指标变化、10 大股东变化，生成分析报告。

功能:
- 计算单只股票指标变化
- 分析 10 大股东变化 (新进/增持/减持/退出)
- 生成 5 年股东追踪报告
- 全市场十大变化排名

使用示例:
    from core.analysis.financial_analyzer import FinancialAnalyzer

    analyzer = FinancialAnalyzer()

    # 计算指标变化
    changes = analyzer.calculate_changes("000001")

    # 分析股东变化
    holder_changes = analyzer.analyze_shareholder_changes("000001")

    # 获取 5 年股东追踪
    tracking = analyzer.get_shareholder_tracking("000001", years=5)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from lib.database import get_connection


class FinancialAnalyzer:
    """财报分析器"""

    def __init__(self):
        """初始化分析器"""

    def _get_connection(self):
        """获取数据库连接"""
        # 与 Gateway 审计/duckdb_manager 同库时不可只读，否则 DuckDB 同进程配置冲突
        return get_connection(read_only=False)

    def calculate_changes(
        self,
        stock_code: str,
        metric_names: Optional[List[str]] = None,
        periods: int = 4
    ) -> List[Dict[str, Any]]:
        """
        计算指标变化

        Args:
            stock_code: 股票代码
            metric_names: 指标列表，None 则使用默认指标
            periods: 分析期数

        Returns:
            变化数据列表
        """
        if metric_names is None:
            metric_names = [
                "total_revenue",
                "gross_profit",
                "net_profit",
                "operating_cash_flow",
                "roe",
                "gross_margin",
            ]

        conn = self._get_connection()
        changes = []

        for metric in metric_names:
            try:
                # 获取历史数据
                df = conn.execute(f"""
                    SELECT
                        report_date,
                        period_end,
                        {metric} as value
                    FROM financial_report
                    WHERE stock_code = ?
                    ORDER BY period_end DESC
                    LIMIT ?
                """, [stock_code, periods]).fetchdf()

                if len(df) < 2:
                    continue

                # 计算环比变化
                for i in range(len(df) - 1):
                    current = df.iloc[i]
                    previous = df.iloc[i + 1]

                    if current["value"] and previous["value"]:
                        change_amount = current["value"] - previous["value"]
                        change_ratio = (change_amount / abs(previous["value"])) * 100 if previous["value"] != 0 else 0

                        changes.append({
                            "stock_code": stock_code,
                            "report_date": current["report_date"],
                            "period_end": current["period_end"],
                            "metric_name": metric,
                            "current_value": current["value"],
                            "previous_value": previous["value"],
                            "change_amount": change_amount,
                            "change_ratio": change_ratio,
                        })

            except (ValueError, TypeError, KeyError, OSError) as e:
                print(f"计算 {stock_code} 的 {metric} 变化失败：{e}")

        conn.close()
        return changes

    def get_top_changes(
        self,
        stock_code: str,
        report_date: Optional[str] = None,
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取十大变化

        Args:
            stock_code: 股票代码
            report_date: 报告日期，None 则使用最新
            top_n: 返回数量

        Returns:
            十大变化列表
        """
        changes = self.calculate_changes(stock_code)

        if not changes:
            return []

        # 按变化率绝对值排序
        sorted_changes = sorted(
            changes,
            key=lambda x: abs(x.get("change_ratio", 0)),
            reverse=True
        )

        # 取前 N 个
        top_changes = sorted_changes[:top_n]

        # 添加排名和描述
        metric_names_zh = {
            "total_revenue": "营业收入",
            "gross_profit": "毛利润",
            "net_profit": "净利润",
            "operating_cash_flow": "经营现金流",
            "roe": "净资产收益率",
            "gross_margin": "毛利率",
        }

        for i, change in enumerate(top_changes, 1):
            change["rank"] = i
            metric_zh = metric_names_zh.get(change["metric_name"], change["metric_name"])
            ratio = change["change_ratio"]
            direction = "增长" if ratio > 0 else "下降"
            change["description"] = f"{metric_zh}{direction}{abs(ratio):.2f}%"

        return top_changes

    def analyze_shareholder_changes(
        self,
        stock_code: str,
        current_date: Optional[str] = None,
        previous_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析 10 大股东变化

        Args:
            stock_code: 股票代码
            current_date: 当前报告期
            previous_date: 上期报告期

        Returns:
            股东变化分析结果
        """
        conn = self._get_connection()

        # 获取当前期 10 大股东
        if current_date is None:
            current_date = conn.execute("""
                SELECT MAX(report_date) FROM top_10_shareholders
                WHERE stock_code = ?
            """, [stock_code]).fetchone()[0]

        if current_date is None:
            conn.close()
            return {"error": "无股东数据"}

        current_df = conn.execute("""
            SELECT * FROM top_10_shareholders
            WHERE stock_code = ? AND report_date = ?
            ORDER BY rank
        """, [stock_code, current_date]).fetchdf()

        # 获取上期 10 大股东
        if previous_date is None:
            previous_date = conn.execute("""
                SELECT MAX(report_date) FROM top_10_shareholders
                WHERE stock_code = ? AND report_date < ?
            """, [stock_code, current_date]).fetchone()[0]

        analysis = {
            "stock_code": stock_code,
            "current_date": current_date,
            "previous_date": previous_date,
            "current_holders": [],
            "changes": [],
            "summary": {},
        }

        if current_df.empty:
            conn.close()
            return analysis

        analysis["current_holders"] = current_df.to_dict("records")

        if previous_date:
            previous_df = conn.execute("""
                SELECT * FROM top_10_shareholders
                WHERE stock_code = ? AND report_date = ?
                ORDER BY rank
            """, [stock_code, previous_date]).fetchdf()

            if not previous_df.empty:
                # 分析变化
                current_names = set(current_df["shareholder_name"].tolist())
                previous_names = set(previous_df["shareholder_name"].tolist())

                # 新进股东
                new_holders = current_names - previous_names

                # 退出股东
                exited_holders = previous_names - current_names

                # 在榜股东，检查持股变化
                common_holders = current_names & previous_names

                changes = []

                # 新进
                for name in new_holders:
                    holder = current_df[current_df["shareholder_name"] == name].iloc[0]
                    changes.append({
                        "change_type": "新进",
                        "shareholder_name": name,
                        "current_rank": int(holder["rank"]),
                        "current_shares": int(holder["share_count"] or 0),
                        "current_ratio": float(holder["share_ratio"] or 0),
                    })

                # 退出
                for name in exited_holders:
                    holder = previous_df[previous_df["shareholder_name"] == name].iloc[0]
                    changes.append({
                        "change_type": "退出",
                        "shareholder_name": name,
                        "previous_rank": int(holder["rank"]),
                        "previous_shares": int(holder["share_count"] or 0),
                        "previous_ratio": float(holder["share_ratio"] or 0),
                    })

                # 增持/减持
                for name in common_holders:
                    current_holder = current_df[current_df["shareholder_name"] == name].iloc[0]
                    previous_holder = previous_df[previous_df["shareholder_name"] == name].iloc[0]

                    current_shares = int(current_holder["share_count"] or 0)
                    previous_shares = int(previous_holder["share_count"] or 0)

                    if current_shares != previous_shares:
                        change = current_shares - previous_shares
                        change_ratio = (change / previous_shares * 100) if previous_shares > 0 else 0

                        changes.append({
                            "change_type": "增持" if change > 0 else "减持",
                            "shareholder_name": name,
                            "current_rank": int(current_holder["rank"]),
                            "previous_rank": int(previous_holder["rank"]),
                            "current_shares": current_shares,
                            "previous_shares": previous_shares,
                            "share_change": change,
                            "change_ratio": change_ratio,
                        })

                analysis["changes"] = changes

                # 汇总统计
                analysis["summary"] = {
                    "total_holders": len(current_df),
                    "new_count": len(new_holders),
                    "exited_count": len(exited_holders),
                    "increased_count": len([c for c in changes if c["change_type"] == "增持"]),
                    "decreased_count": len([c for c in changes if c["change_type"] == "减持"]),
                }

        conn.close()
        return analysis

    def get_shareholder_tracking(
        self,
        stock_code: str,
        years: int = 5,
        shareholder_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取股东追踪报告 (5 年历史)

        Args:
            stock_code: 股票代码
            years: 追踪年数
            shareholder_name: 特定股东名称，None 则追踪所有前 10 股东

        Returns:
            股东追踪报告
        """
        conn = self._get_connection()

        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)

        # 获取时间范围内的所有股东记录
        if shareholder_name:
            df = conn.execute("""
                SELECT * FROM top_10_shareholders
                WHERE stock_code = ?
                  AND shareholder_name = ?
                  AND report_date >= ?
                ORDER BY report_date, rank
            """, [stock_code, shareholder_name, start_date.strftime("%Y-%m-%d")]).fetchdf()
        else:
            df = conn.execute("""
                SELECT * FROM top_10_shareholders
                WHERE stock_code = ? AND report_date >= ?
                ORDER BY report_date, rank
            """, [stock_code, start_date.strftime("%Y-%m-%d")]).fetchdf()

        conn.close()

        if df.empty:
            return {
                "stock_code": stock_code,
                "years": years,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "error": "无历史数据",
            }

        # 按股东分组统计
        tracking = {}
        for _, row in df.iterrows():
            name = row["shareholder_name"]
            if name not in tracking:
                tracking[name] = {
                    "appearances": [],
                    "total_appearances": 0,
                    "first_appearance": None,
                    "last_appearance": None,
                    "share_history": [],
                }

            tracking[name]["appearances"].append({
                "report_date": str(row["report_date"]),
                "rank": int(row["rank"]),
                "share_count": int(row["share_count"] or 0),
                "share_ratio": float(row["share_ratio"] or 0),
            })
            tracking[name]["total_appearances"] += 1
            tracking[name]["share_history"].append({
                "date": str(row["report_date"]),
                "shares": int(row["share_count"] or 0),
            })

        # 计算首次和末次出现
        for name, data in tracking.items():
            if data["appearances"]:
                data["first_appearance"] = data["appearances"][0]["report_date"]
                data["last_appearance"] = data["appearances"][-1]["report_date"]

        return {
            "stock_code": stock_code,
            "years": years,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "tracking": tracking,
        }

    def get_market_top_changes(
        self,
        metric_name: str = "total_revenue",
        report_date: Optional[str] = None,
        top_n: int = 50,
        change_type: str = "growth"  # "growth" or "decline"
    ) -> List[Dict[str, Any]]:
        """
        获取全市场十大变化排名

        Args:
            metric_name: 指标名称
            report_date: 报告日期
            top_n: 返回数量
            change_type: 变化类型 ("growth" 增长 / "decline" 下降)

        Returns:
            全市场变化排名列表
        """
        conn = self._get_connection()

        # 获取最新报告日期
        if report_date is None:
            report_date = conn.execute("""
                SELECT MAX(report_date) FROM financial_report
            """).fetchone()[0]

        if report_date is None:
            conn.close()
            return []

        # 计算变化率并排序
        order = "DESC" if change_type == "growth" else "ASC"

        df = conn.execute(f"""
            SELECT
                stock_code,
                report_date,
                {metric_name} as current_value,
                LAG({metric_name}) OVER (PARTITION BY stock_code ORDER BY report_date) as previous_value,
                (
                    ({metric_name} - LAG({metric_name}) OVER (PARTITION BY stock_code ORDER BY report_date))
                    / NULLIF(ABS(LAG({metric_name}) OVER (PARTITION BY stock_code ORDER BY report_date)), 0) * 100
                ) as change_ratio
            FROM financial_report
            WHERE report_date <= ?
            ORDER BY change_ratio {order}
            LIMIT ?
        """, [report_date, top_n]).fetchdf()

        conn.close()

        # 转换为字典列表
        result = df.to_dict("records")

        # 添加描述
        metric_names_zh = {
            "total_revenue": "营业收入",
            "gross_profit": "毛利润",
            "net_profit": "净利润",
            "operating_cash_flow": "经营现金流",
        }

        metric_zh = metric_names_zh.get(metric_name, metric_name)
        direction = "增长" if change_type == "growth" else "下降"

        for i, row in enumerate(result, 1):
            row["rank"] = i
            row["description"] = f"{metric_zh}{direction}{abs(row.get('change_ratio', 0)):.2f}%"

        return result


def main():
    """测试分析器"""
    analyzer = FinancialAnalyzer()

    # 测试指标变化
    print("测试指标变化分析...")
    changes = analyzer.calculate_changes("000001")
    print(f"找到 {len(changes)} 条变化记录")
    if changes:
        print(f"示例：{changes[0]}")

    # 测试股东变化
    print("\n测试股东变化分析...")
    holder_analysis = analyzer.analyze_shareholder_changes("000001")
    print(f"股东变化摘要：{holder_analysis.get('summary', {})}")

    # 测试 5 年追踪
    print("\n测试 5 年股东追踪...")
    tracking = analyzer.get_shareholder_tracking("000001", years=5)
    if "tracking" in tracking:
        print(f"追踪到 {len(tracking['tracking'])} 位股东")


if __name__ == "__main__":
    main()
