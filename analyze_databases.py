#!/usr/bin/env python3
"""
数据库分析脚本 - 分析三个DuckDB数据库的结构和数据
"""

import os
import sys
import subprocess
import json
from datetime import datetime

def check_duckdb_installed():
    """检查duckdb是否安装"""
    try:
        import duckdb
        return True
    except ImportError:
        return False

def install_duckdb():
    """安装duckdb模块"""
    print("正在安装duckdb模块...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "duckdb", "--break-system-packages"])
        return True
    except Exception as e:
        print(f"安装失败: {e}")
        return False

def analyze_database(db_path, db_name):
    """分析单个数据库"""
    import duckdb
    
    if not os.path.exists(db_path):
        return {"error": f"文件不存在: {db_path}"}
    
    try:
        conn = duckdb.connect(db_path)
        
        # 获取表列表
        tables_result = conn.execute("SHOW TABLES").fetchall()
        tables = [t[0] for t in tables_result]
        
        analysis = {
            "path": db_path,
            "size_mb": os.path.getsize(db_path) / (1024 * 1024),
            "table_count": len(tables),
            "tables": {}
        }
        
        # 分析每个表
        for table in tables:
            try:
                # 获取行数
                count_result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                row_count = count_result[0] if count_result else 0
                
                # 获取表结构
                schema_result = conn.execute(f"DESCRIBE {table}").fetchall()
                columns = [{"name": col[0], "type": col[1]} for col in schema_result]
                
                # 获取示例数据
                sample_result = conn.execute(f"SELECT * FROM {table} LIMIT 3").fetchall()
                sample = [list(row) for row in sample_result]
                
                analysis["tables"][table] = {
                    "row_count": row_count,
                    "column_count": len(columns),
                    "columns": columns,
                    "sample": sample
                }
                
            except Exception as e:
                analysis["tables"][table] = {"error": str(e)}
        
        conn.close()
        return analysis
        
    except Exception as e:
        return {"error": str(e)}

def main():
    """主函数"""
    print("=== 数据库分析工具 ===")
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 检查duckdb
    if not check_duckdb_installed():
        print("duckdb模块未安装，正在自动安装...")
        if not install_duckdb():
            print("无法继续，请手动安装duckdb: pip install duckdb")
            return
    
    import duckdb
    
    # 数据库路径
    databases = {
        "quant_system.duckdb": "data/quant_system.duckdb",
        "quant_system.duckdb": "data/quant_system.duckdb",
        "quant_system.duckdb": "data/quant_system.duckdb"
    }
    
    results = {}
    
    # 分析每个数据库
    for name, path in databases.items():
        print(f"\n分析 {name}...")
        analysis = analyze_database(path, name)
        results[name] = analysis
        
        if "error" in analysis:
            print(f"  ❌ 错误: {analysis['error']}")
        else:
            print(f"  ✅ 大小: {analysis['size_mb']:.2f} MB")
            print(f"  ✅ 表数量: {analysis['table_count']}")
            
            # 显示表统计
            for table_name, table_info in analysis["tables"].items():
                if "error" in table_info:
                    print(f"    - {table_name}: 错误 - {table_info['error']}")
                else:
                    print(f"    - {table_name}: {table_info['row_count']:,} 行, {table_info['column_count']} 列")
    
    # 保存分析结果
    output_file = "database_analysis.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n分析结果已保存到: {output_file}")
    
    # 生成汇总报告
    print("\n=== 数据库统一建议 ===")
    
    # 检查表冲突
    all_tables = {}
    for db_name, analysis in results.items():
        if "error" in analysis:
            continue
        for table_name in analysis["tables"].keys():
            if table_name not in all_tables:
                all_tables[table_name] = []
            all_tables[table_name].append(db_name)
    
    # 找出重复的表
    duplicate_tables = {table: dbs for table, dbs in all_tables.items() if len(dbs) > 1}
    
    if duplicate_tables:
        print("⚠️ 发现重复的表名:")
        for table, dbs in duplicate_tables.items():
            print(f"  - {table}: 存在于 {', '.join(dbs)}")
    else:
        print("✅ 没有表名冲突")
    
    # 建议主数据库
    print("\n📊 数据库选择建议:")
    
    # 检查quant_system.duckdb是否是最全面的
    if "quant_system.duckdb" in results and "error" not in results["quant_system.duckdb"]:
        system_tables = len(results["quant_system.duckdb"]["tables"])
        print(f"  - quant_system.duckdb: {system_tables} 个表，建议作为主数据库")
    
    # 检查数据量
    print("\n📈 数据量统计:")
    for db_name, analysis in results.items():
        if "error" in analysis:
            continue
        total_rows = sum(table_info.get("row_count", 0) for table_info in analysis["tables"].values() if "error" not in table_info)
        print(f"  - {db_name}: {total_rows:,} 总行数")
    
    print("\n✅ 分析完成!")

if __name__ == "__main__":
    main()