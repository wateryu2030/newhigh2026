#!/usr/bin/env python3
"""
简单数据库迁移脚本 - 直接复制数据
"""

import duckdb
from datetime import datetime

def migrate_table_simple(source_conn, target_conn, table_name):
    """简单迁移表"""
    print(f"  迁移 {table_name}...", end="")
    
    try:
        # 检查源表数据
        source_count = source_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        if source_count == 0:
            print(" ⚠️ 空表，跳过")
            return {"status": "skipped", "rows": 0}
        
        print(f" ({source_count} 行)...", end="")
        
        # 获取数据
        data = source_conn.execute(f"SELECT * FROM {table_name}").fetchall()
        
        # 获取列名
        columns = source_conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        column_names = [col[1] for col in columns]
        
        # 检查目标表是否存在
        target_exists = target_conn.execute(
            f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table_name}'"
        ).fetchone()[0] > 0
        
        if not target_exists:
            # 创建表
            create_sql = f"CREATE TABLE {table_name} ("
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                create_sql += f"{col_name} {col_type}, "
            create_sql = create_sql.rstrip(", ") + ")"
            target_conn.execute(create_sql)
        
        # 插入数据（使用批量插入）
        if data:
            # 构建INSERT语句
            placeholders = ", ".join(["?" for _ in column_names])
            insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
            
            # 批量插入
            target_conn.executemany(insert_sql, data)
        
        # 验证
        target_count = target_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        
        print(" ✅ 完成")
        return {"status": "success", "rows": target_count}
        
    except Exception as e:
        print(f" ❌ 失败: {e}")
        return {"status": "failed", "error": str(e)}

def migrate_database_simple(source_path, target_path, db_name):
    """简单迁移数据库"""
    print(f"\n🚀 迁移 {db_name} -> quant_system.duckdb")
    
    try:
        # 分别连接数据库
        source_conn = duckdb.connect(source_path)
        target_conn = duckdb.connect(target_path)
        
        # 获取源表
        source_tables = source_conn.execute("SHOW TABLES").fetchall()
        
        results = {}
        for table in source_tables:
            table_name = table[0]
            result = migrate_table_simple(source_conn, target_conn, table_name)
            results[table_name] = result
        
        # 关闭连接
        source_conn.close()
        target_conn.close()
        
        # 统计
        success = sum(1 for r in results.values() if r["status"] == "success")
        skipped = sum(1 for r in results.values() if r["status"] == "skipped")
        failed = sum(1 for r in results.values() if r["status"] == "failed")
        
        print(f"📊 {db_name} 迁移结果: 成功={success}, 跳过={skipped}, 失败={failed}")
        
        return {
            "success": success,
            "skipped": skipped,
            "failed": failed,
            "results": results
        }
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        return {"error": str(e)}

def main():
    """主函数"""
    print("=== 简单数据库迁移 ===")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 源数据库
    sources = [
        ("market", "data/quant_system.duckdb"),
        ("quant", "data/quant_system.duckdb")
    ]
    
    target = "data/quant_system.duckdb"
    
    if not os.path.exists(target):
        print(f"❌ 目标数据库不存在: {target}")
        return
    
    all_results = {}
    
    # 迁移每个数据库
    for db_name, db_path in sources:
        if os.path.exists(db_path):
            result = migrate_database_simple(db_path, target, db_name)
            all_results[db_name] = result
        else:
            print(f"⚠️  数据库不存在: {db_path}")
    
    # 汇总
    print("\n" + "="*50)
    print("📋 迁移汇总")
    print("="*50)
    
    total_success = 0
    total_skipped = 0
    total_failed = 0
    
    for db_name, result in all_results.items():
        if "error" not in result:
            total_success += result["success"]
            total_skipped += result["skipped"]
            total_failed += result["failed"]
            
            print(f"{db_name}: 成功={result['success']}, 跳过={result['skipped']}, 失败={result['failed']}")
    
    print(f"\n总计: 成功={total_success}, 跳过={total_skipped}, 失败={total_failed}")
    
    # 验证目标数据库
    print("\n🔍 验证目标数据库...")
    try:
        conn = duckdb.connect(target)
        tables = conn.execute("SHOW TABLES").fetchall()
        print(f"quant_system.duckdb 现有 {len(tables)} 个表")
        
        for table in tables:
            table_name = table[0]
            count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            if count > 0:
                print(f"  ✅ {table_name}: {count:,} 行")
        
        conn.close()
    except Exception as e:
        print(f"❌ 验证失败: {e}")
    
    print("\n✅ 迁移完成!")
    print(f"⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()