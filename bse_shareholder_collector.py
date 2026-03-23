#!/usr/bin/env python3
"""
北交所股东数据采集器
使用东方财富 API 作为数据源，补充北交所股票股东数据
"""

import sys
import datetime as dt
from pathlib import Path
from typing import List, Dict, Any

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import requests
    import pandas as pd
    REQUESTS_AVAILABLE = True
except ImportError as e:
    REQUESTS_AVAILABLE = False
    print(f"❌ 缺少依赖：{e}")

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    print("❌ duckdb 未安装")


class BSEShareholderCollector:
    """北交所股东数据采集器"""
    
    def __init__(self):
        self.session = requests.Session() if REQUESTS_AVAILABLE else None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'http://quote.eastmoney.com/'
        }
        
    def get_bse_stock_list(self) -> List[str]:
        """获取北交所股票列表（基于代码范围生成）"""
        print("\n📋 生成北交所股票代码列表...")
        
        # 北交所股票代码范围：920000-920999
        stock_codes = []
        
        # 获取数据库中已存在的股票代码，避免重复采集
        db_path = project_root / "data" / "quant_system.duckdb"
        if DUCKDB_AVAILABLE:
            try:
                conn = duckdb.connect(str(db_path))
                existing = conn.execute("""
                    SELECT DISTINCT stock_code FROM top_10_shareholders 
                    WHERE stock_code LIKE '920%' OR stock_code LIKE '8%' 
                    OR stock_code LIKE '43%' OR stock_code LIKE '87%'
                """).fetchall()
                existing_codes = set([row[0] for row in existing])
                conn.close()
                print(f"  📊 数据库中已有 {len(existing_codes)} 只北交所股票")
            except:
                existing_codes = set()
        else:
            existing_codes = set()
        
        # 生成 920 开头的股票代码 (920000-920999)
        for i in range(1000):
            code = f"920{i:03d}"
            if code not in existing_codes:
                stock_codes.append(code)
        
        print(f"  ✅ 待采集：{len(stock_codes)} 只新股票")
        return stock_codes
    
    def fetch_shareholder_data(self, stock_code: str) -> List[Dict[str, Any]]:
        """
        从东方财富 API 获取股东数据
        
        API: https://datacenter-web.eastmoney.com/api/data/v1/get
        """
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "reportName": "RPT_F10_EH_EQUITY",
            "columns": "ALL",
            "quoteColumns": "",
            "filter": f"""(SECUCODE="{stock_code}.BJ")""",
            "pageNumber": "1",
            "pageSize": "20",
            "sortTypes": "-1",
            "sortColumns": "END_DATE",
            "source": "HSF10",
            "client": "PC",
            "v": "0123456789"
        }
        
        try:
            response = self.session.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            result = data.get("result", {})
            items = result.get("data", [])
            
            shareholders = []
            for item in items:
                # 解析十大股东
                holder_items = item.get("HOLDER_ITEMS", [])
                if not holder_items:
                    continue
                
                report_date = item.get("END_DATE", "")
                if report_date:
                    try:
                        report_date = dt.datetime.strptime(report_date, "%Y-%m-%d").date()
                    except:
                        report_date = dt.datetime.now().date()
                
                for idx, holder in enumerate(holder_items[:10], 1):
                    shareholder = {
                        "stock_code": stock_code,
                        "report_date": report_date,
                        "report_type": "定期报告",
                        "rank": idx,
                        "shareholder_name": holder.get("HOLDER_NAME", ""),
                        "shareholder_type": holder.get("HOLDER_TYPE", "流通 A 股"),
                        "share_count": holder.get("HOLD_NUM", 0),
                        "share_ratio": holder.get("HOLD_RATIO", 0),
                        "share_change": holder.get("FREE_NUM", 0),
                        "change_ratio": holder.get("HOLD_RATIO_CHANGE", 0),
                        "pledge_count": 0,
                        "freeze_count": 0,
                        "created_at": dt.datetime.now(),
                        "updated_at": dt.datetime.now()
                    }
                    shareholders.append(shareholder)
            
            return shareholders
            
        except Exception as e:
            print(f"  ⚠️  获取 {stock_code} 股东数据失败：{e}")
            return []
    
    def save_to_duckdb(self, shareholders: List[Dict[str, Any]]) -> int:
        """保存到 DuckDB 数据库"""
        if not DUCKDB_AVAILABLE or not shareholders:
            return 0
        
        db_path = project_root / "data" / "quant_system.duckdb"
        conn = duckdb.connect(str(db_path))
        
        saved = 0
        for sh in shareholders:
            try:
                # 检查是否已存在
                existing = conn.execute("""
                    SELECT id FROM top_10_shareholders 
                    WHERE stock_code = ? AND report_date = ? AND rank = ?
                """, [sh["stock_code"], sh["report_date"], sh["rank"]]).fetchone()
                
                if existing:
                    # 更新现有记录
                    conn.execute("""
                        UPDATE top_10_shareholders 
                        SET shareholder_name = ?, shareholder_type = ?, share_count = ?,
                            share_ratio = ?, share_change = ?, change_ratio = ?,
                            pledge_count = ?, freeze_count = ?, updated_at = ?
                        WHERE stock_code = ? AND report_date = ? AND rank = ?
                    """, [
                        sh["shareholder_name"], sh["shareholder_type"], sh["share_count"],
                        sh["share_ratio"], sh["share_change"], sh["change_ratio"],
                        sh["pledge_count"], sh["freeze_count"], sh["updated_at"],
                        sh["stock_code"], sh["report_date"], sh["rank"]
                    ])
                    saved += 1
                else:
                    # 插入新记录
                    conn.execute("""
                        INSERT INTO top_10_shareholders (
                            stock_code, report_date, report_type, rank,
                            shareholder_name, shareholder_type, share_count,
                            share_ratio, share_change, change_ratio,
                            pledge_count, freeze_count, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        sh["stock_code"], sh["report_date"], sh["report_type"], sh["rank"],
                        sh["shareholder_name"], sh["shareholder_type"], sh["share_count"],
                        sh["share_ratio"], sh["share_change"], sh["change_ratio"],
                        sh["pledge_count"], sh["freeze_count"], sh["created_at"], sh["updated_at"]
                    ])
                    saved += 1
                    
            except Exception as e:
                print(f"  ⚠️  保存失败：{e}")
        
        conn.close()
        return saved
    
    def collect_all(self, limit: int = None) -> Dict[str, Any]:
        """采集所有北交所股票股东数据"""
        print("=" * 70)
        print("🏢 北交所股东数据采集器")
        print(f"执行时间：{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        if not REQUESTS_AVAILABLE:
            print("❌ 缺少依赖包")
            return {"error": "missing_dependencies"}
        
        # 获取股票列表
        stock_codes = self.get_bse_stock_list()
        
        if limit:
            stock_codes = stock_codes[:limit]
            print(f"\n📌 限制采集前 {limit} 只股票")
        
        # 获取已存在的股票代码
        db_path = project_root / "data" / "quant_system.duckdb"
        if DUCKDB_AVAILABLE:
            conn = duckdb.connect(str(db_path))
            existing = conn.execute("""
                SELECT DISTINCT stock_code FROM top_10_shareholders 
                WHERE stock_code LIKE '920%' OR stock_code LIKE '8%' OR stock_code LIKE '43%' OR stock_code LIKE '87%'
            """).fetchall()
            existing_codes = [row[0] for row in existing]
            conn.close()
            
            # 过滤掉已存在的股票
            new_codes = [code for code in stock_codes if code not in existing_codes]
            print(f"\n📊 数据库已有：{len(existing_codes)} 只北交所股票")
            print(f"📊 待采集：{len(new_codes)} 只新股票")
            stock_codes = new_codes
        
        if not stock_codes:
            print("\n✅ 所有北交所股票数据已存在")
            return {"total": 0, "success": 0, "saved": 0}
        
        # 采集数据
        all_shareholders = []
        stats = {
            "total": len(stock_codes),
            "success": 0,
            "failed": 0,
            "saved": 0
        }
        
        print(f"\n🚀 开始采集 {len(stock_codes)} 只股票...")
        
        for i, code in enumerate(stock_codes, 1):
            if i % 50 == 0:
                print(f"  进度：{i}/{len(stock_codes)}")
            
            shareholders = self.fetch_shareholder_data(code)
            
            if shareholders:
                all_shareholders.extend(shareholders)
                stats["success"] += 1
            else:
                stats["failed"] += 1
        
        # 保存到数据库
        print(f"\n💾 保存到数据库...")
        saved = self.save_to_duckdb(all_shareholders)
        stats["saved"] = saved
        
        # 统计
        print("\n" + "=" * 70)
        print("✅ 采集完成!")
        print("=" * 70)
        print(f"总股票数：{stats['total']}")
        print(f"成功：{stats['success']}")
        print(f"失败：{stats['failed']}")
        print(f"保存记录：{stats['saved']} 条")
        
        return stats


def main():
    """主函数"""
    collector = BSEShareholderCollector()
    
    # 采集所有北交所股票
    stats = collector.collect_all(limit=None)
    
    return stats


if __name__ == "__main__":
    stats = main()
    
    # 保存执行日志
    log_dir = project_root / "logs" / "bse_collector"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"run_{timestamp}.json"
    
    import json
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n📝 日志已保存：{log_file}")
    
    sys.exit(0 if stats.get("success", 0) > 0 else 1)
