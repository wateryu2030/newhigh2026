#!/usr/bin/env python3
"""
完成数据库迁移 - 处理剩余的表迁移
"""

import os
import duckdb
from datetime import datetime

def check_database_connection(db_path):
    """检查数据库连接"""
    try:
        conn = duckdb.connect(db_path)
        tables = conn.execute("SHOW TABLES").fetchall()
        conn.close()
        return True, len(tables)
    except Exception as e:
        return False, str(e)

def migrate_remaining_tables():
    """迁移剩余的表"""
    print("=== 迁移剩余表 ===")
    
    source_db = "data/quant.duckdb"
    target_db = "data/quant_system.duckdb"
    
    if not os.path.exists(source_db):
        print(f"❌ 源数据库不存在: {source_db}")
        return False
    
    if not os.path.exists(target_db):
        print(f"❌ 目标数据库不存在: {target_db}")
        return False
    
    try:
        # 连接数据库
        source_conn = duckdb.connect(source_db)
        target_conn = duckdb.connect(target_db)
        
        # 获取源表
        source_tables = source_conn.execute("SHOW TABLES").fetchall()
        print(f"源数据库有 {len(source_tables)} 个表")
        
        # 获取目标表
        target_tables = target_conn.execute("SHOW TABLES").fetchall()
        target_table_names = [t[0] for t in target_tables]
        print(f"目标数据库有 {len(target_tables)} 个表")
        
        # 检查哪些表需要迁移
        tables_to_migrate = []
        for table in source_tables:
            table_name = table[0]
            if table_name not in target_table_names:
                tables_to_migrate.append(table_name)
            else:
                # 检查表是否有数据
                source_count = source_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                if source_count > 0:
                    print(f"  ⚠️  {table_name}: 表已存在，但有 {source_count} 行数据可能需要处理")
        
        print(f"\n需要迁移的表: {tables_to_migrate}")
        
        # 迁移剩余的表
        for table_name in tables_to_migrate:
            print(f"\n迁移 {table_name}...")
            
            try:
                # 获取表结构
                schema = source_conn.execute(f"DESCRIBE {table_name}").fetchall()
                
                # 创建表
                create_sql = f"CREATE TABLE {table_name} ("
                for col in schema:
                    col_name = col[0]
                    col_type = col[1]
                    create_sql += f"{col_name} {col_type}, "
                create_sql = create_sql.rstrip(", ") + ")"
                
                target_conn.execute(create_sql)
                print("  创建表结构完成")
                
                # 迁移数据
                source_count = source_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                if source_count > 0:
                    print(f"  迁移 {source_count} 行数据...")
                    
                    # 分批迁移
                    batch_size = 50000
                    migrated = 0
                    
                    for offset in range(0, source_count, batch_size):
                        data = source_conn.execute(
                            f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}"
                        ).fetchall()
                        
                        if data:
                            # 获取列名
                            col_names = [col[0] for col in schema]
                            placeholders = ", ".join(["?" for _ in col_names])
                            insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
                            
                            target_conn.executemany(insert_sql, data)
                            migrated += len(data)
                        
                        print(f"    进度: {min(offset + batch_size, source_count):,}/{source_count:,}")
                    
                    print(f"  ✅ 完成: {migrated:,} 行已迁移")
                else:
                    print("  ⚠️ 空表，跳过数据迁移")
                    
            except Exception as e:
                print(f"  ❌ 迁移失败: {e}")
        
        # 关闭连接
        source_conn.close()
        target_conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 迁移过程出错: {e}")
        return False

def verify_migration():
    """验证迁移结果"""
    print("\n=== 验证迁移结果 ===")
    
    target_db = "data/quant_system.duckdb"
    
    try:
        conn = duckdb.connect(target_db)
        tables = conn.execute("SHOW TABLES").fetchall()
        
        print(f"quant_system.duckdb 现有 {len(tables)} 个表:")
        
        total_rows = 0
        key_tables = ['daily_bars', 'stocks', 'news_items', 'market_emotion_state', 'sector_strength']
        
        for table in tables:
            table_name = table[0]
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                total_rows += count
                
                if table_name in key_tables:
                    if count > 0:
                        print(f"  ✅ {table_name}: {count:,} 行")
                    else:
                        print(f"  ⚠️  {table_name}: {count:,} 行 (关键表为空)")
                elif count > 1000:
                    print(f"  📊 {table_name}: {count:,} 行")
                    
            except Exception as e:
                print(f"  ❌ {table_name}: 读取错误 - {e}")
        
        conn.close()
        
        print(f"\n总计: {total_rows:,} 行数据")
        print(f"数据库大小: {os.path.getsize(target_db) / (1024*1024):.2f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

def main():
    """主函数"""
    print("=== 完成数据库迁移 ===")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 检查数据库连接
    print("检查数据库连接...")
    
    dbs = {
        "market.duckdb": "data/market.duckdb",
        "quant.duckdb": "data/quant.duckdb",
        "quant_system.duckdb": "data/quant_system.duckdb"
    }
    
    for name, path in dbs.items():
        if os.path.exists(path):
            success, result = check_database_connection(path)
            if success:
                print(f"  ✅ {name}: 连接正常 ({result} 个表)")
            else:
                print(f"  ❌ {name}: 连接失败 - {result}")
        else:
            print(f"  ⚠️  {name}: 文件不存在")
    
    print()
    
    # 迁移剩余的表
    if not migrate_remaining_tables():
        print("❌ 迁移失败")
        return
    
    # 验证迁移结果
    if not verify_migration():
        print("❌ 验证失败")
        return
    
    print()
    print("=== 迁移完成建议 ===")
    print("1. 运行系统功能测试，确保所有功能正常")
    print("2. 备份旧数据库文件 (market.duckdb, quant.duckdb)")
    print("3. 更新相关文档和配置")
    print("4. 监控系统运行情况，确保稳定性")
    print()
    print("✅ 数据库迁移完成!")
    print(f"⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()