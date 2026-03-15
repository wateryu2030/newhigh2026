#!/usr/bin/env python3
"""
智能数据库迁移 - 处理主键冲突
"""

import os
import duckdb
from datetime import datetime

def get_table_primary_key(conn, table_name):
    """获取表的主键信息"""
    try:
        # 尝试从PRAGMA获取主键
        pk_info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        pk_columns = []
        for col in pk_info:
            col_name, col_type, not_null, default_val, pk = col[1], col[2], col[3], col[4], col[5]
            if pk > 0:
                pk_columns.append(col_name)
        
        if pk_columns:
            return pk_columns
        
        # 如果没有明确的主键，尝试猜测
        # 常见的主键列名
        common_pk_names = ['id', 'code', 'symbol', 'order_book_id', 'date', 'trade_date']
        for col in pk_info:
            if col[1].lower() in common_pk_names:
                return [col[1]]
        
        return None
        
    except Exception as e:
        print(f"    获取主键失败: {e}")
        return None

def migrate_table_with_conflict(source_conn, target_conn, table_name):
    """迁移表，处理主键冲突"""
    print(f"   迁移 {table_name}...", end="")
    
    try:
        # 获取源表数据量
        source_count = source_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        if source_count == 0:
            print(f" ⚠️ 空表，跳过")
            return {"status": "skipped", "rows": 0}
        
        print(f" ({source_count:,} 行)")
        
        # 获取主键
        pk_columns = get_table_primary_key(source_conn, table_name)
        if pk_columns:
            print(f"     主键: {pk_columns}")
        
        # 检查目标表是否存在
        target_exists = target_conn.execute(
            f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table_name}'"
        ).fetchone()[0] > 0
        
        if not target_exists:
            print(f"     目标表不存在，将创建...")
            # 这里应该创建表，但为了简单，我们假设表已存在
            # 实际上，quant_system.duckdb应该已经有所有表结构
        
        # 获取目标表现有数据量
        target_count = 0
        if target_exists:
            target_count = target_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            print(f"     目标表已有 {target_count:,} 行")
        
        # 迁移策略
        if target_count == 0:
            # 目标表为空，直接插入
            print(f"     直接插入所有数据...")
            data = source_conn.execute(f"SELECT * FROM {table_name}").fetchall()
            if data:
                cols = source_conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                col_names = [col[1] for col in cols]
                placeholders = ", ".join(["?" for _ in col_names])
                insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
                target_conn.executemany(insert_sql, data)
        
        elif pk_columns:
            # 有主键，使用INSERT OR REPLACE
            print(f"     使用INSERT OR REPLACE处理冲突...")
            
            # 获取所有列
            cols = source_conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            col_names = [col[1] for col in cols]
            
            # 构建INSERT OR REPLACE语句
            placeholders = ", ".join(["?" for _ in col_names])
            insert_sql = f"INSERT OR REPLACE INTO {table_name} VALUES ({placeholders})"
            
            # 分批处理
            batch_size = 50000
            migrated = 0
            
            for offset in range(0, source_count, batch_size):
                data = source_conn.execute(
                    f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}"
                ).fetchall()
                
                if data:
                    target_conn.executemany(insert_sql, data)
                    migrated += len(data)
                
                print(f"     进度: {min(offset + batch_size, source_count):,}/{source_count:,} 行")
        
        else:
            # 没有主键，直接追加
            print(f"     没有主键，直接追加数据...")
            data = source_conn.execute(f"SELECT * FROM {table_name}").fetchall()
            if data:
                cols = source_conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                col_names = [col[1] for col in cols]
                placeholders = ", ".join(["?" for _ in col_names])
                insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
                target_conn.executemany(insert_sql, data)
        
        # 验证
        final_count = target_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"     ✅ 完成，目标表现有 {final_count:,} 行")
        
        return {"status": "success", "rows": final_count}
        
    except Exception as e:
        print(f"     ❌ 失败: {e}")
        return {"status": "failed", "error": str(e)}

def main():
    """主函数"""
    print("=== 智能数据库迁移 ===")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 目标数据库
    target_db = "data/quant_system.duckdb"
    
    if not os.path.exists(target_db):
        print(f"❌ 目标数据库不存在: {target_db}")
        return
    
    # 连接目标数据库
    target_conn = duckdb.connect(target_db)
    
    # 1. 迁移market.duckdb
    print("1. 迁移 quant_system.duckdb")
    print("=" * 40)
    
    market_db = "data/quant_system.duckdb"
    if os.path.exists(market_db):
        market_conn = duckdb.connect(market_db)
        market_tables = market_conn.execute("SHOW TABLES").fetchall()
        
        for table in market_tables:
            table_name = table[0]
            count = market_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            if count > 0:
                migrate_table_with_conflict(market_conn, target_conn, table_name)
        
        market_conn.close()
    else:
        print("⚠️  quant_system.duckdb 不存在")
    
    print()
    
    # 2. 迁移quant.duckdb
    print("2. 迁移 quant_system.duckdb")
    print("=" * 40)
    
    quant_db = "data/quant_system.duckdb"
    if os.path.exists(quant_db):
        quant_conn = duckdb.connect(quant_db)
        quant_tables = quant_conn.execute("SHOW TABLES").fetchall()
        
        # 按重要性排序迁移
        priority_tables = ['stocks', 'daily_bars', 'news_items', 'features_daily', 'backtest_runs']
        
        for table_name in priority_tables:
            # 检查表是否存在
            table_exists = any(t[0] == table_name for t in quant_tables)
            if table_exists:
                count = quant_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                if count > 0:
                    migrate_table_with_conflict(quant_conn, target_conn, table_name)
                else:
                    print(f"   {table_name}: ⚠️ 空表，跳过")
            else:
                print(f"   {table_name}: ⚠️ 表不存在")
        
        quant_conn.close()
    else:
        print("⚠️  quant_system.duckdb 不存在")
    
    # 关闭连接
    target_conn.close()
    
    # 最终验证
    print()
    print("3. 迁移结果验证")
    print("=" * 40)
    
    final_conn = duckdb.connect(target_db)
    tables = final_conn.execute("SHOW TABLES").fetchall()
    
    print(f"quant_system.duckdb 现有 {len(tables)} 个表:")
    
    total_rows = 0
    for table in tables:
        table_name = table[0]
        try:
            count = final_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            total_rows += count
            if count > 0:
                print(f"  ✅ {table_name}: {count:,} 行")
        except:
            print(f"  ❌ {table_name}: 读取错误")
    
    final_conn.close()
    
    print(f"\n总计: {total_rows:,} 行数据")
    print(f"\n✅ 迁移完成!")
    print(f"⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()