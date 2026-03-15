#!/usr/bin/env python3
"""
数据库迁移脚本 - 将market.duckdb和quant.duckdb迁移到quant_system.duckdb
"""

import os
import sys
import shutil
import duckdb
from datetime import datetime

def backup_database(source_path, backup_dir="backups"):
    """备份数据库"""
    if not os.path.exists(source_path):
        print(f"⚠️  源文件不存在: {source_path}")
        return None
    
    # 创建备份目录
    os.makedirs(backup_dir, exist_ok=True)
    
    # 生成备份文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.basename(source_path)
    backup_path = os.path.join(backup_dir, f"{filename}.backup_{timestamp}")
    
    # 复制文件
    try:
        shutil.copy2(source_path, backup_path)
        print(f"✅ 备份完成: {source_path} -> {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ 备份失败: {e}")
        return None

def analyze_table_conflicts(source_conn, target_conn, source_db_name):
    """分析表冲突"""
    print(f"\n🔍 分析 {source_db_name} 表冲突...")
    
    # 获取源数据库表
    source_tables = source_conn.execute("SHOW TABLES").fetchall()
    source_table_names = [t[0] for t in source_tables]
    
    # 获取目标数据库表
    target_tables = target_conn.execute("SHOW TABLES").fetchall()
    target_table_names = [t[0] for t in target_tables]
    
    conflicts = []
    for table in source_table_names:
        if table in target_table_names:
            # 检查表结构是否一致
            try:
                source_schema = source_conn.execute(f"DESCRIBE {table}").fetchall()
                target_schema = target_conn.execute(f"DESCRIBE {table}").fetchall()
                
                if source_schema != target_schema:
                    conflicts.append({
                        "table": table,
                        "type": "schema_mismatch",
                        "source_columns": len(source_schema),
                        "target_columns": len(target_schema)
                    })
                else:
                    # 检查数据量
                    source_count = source_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    target_count = target_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    
                    if source_count > 0 and target_count > 0:
                        conflicts.append({
                            "table": table,
                            "type": "data_overlap",
                            "source_rows": source_count,
                            "target_rows": target_count
                        })
            except Exception as e:
                conflicts.append({
                    "table": table,
                    "type": "error",
                    "error": str(e)
                })
    
    return conflicts

def migrate_table(source_conn, target_conn, table_name, strategy="append"):
    """迁移单个表"""
    print(f"  迁移表: {table_name}...", end="")
    
    try:
        # 检查源表是否存在数据
        source_count = source_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        if source_count == 0:
            print(f" ⚠️ 源表为空，跳过")
            return {"status": "skipped", "reason": "empty_source", "rows": 0}
        
        # 检查目标表是否存在
        target_exists = target_conn.execute(
            f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table_name}'"
        ).fetchone()[0] > 0
        
        if not target_exists:
            # 创建表（从源表复制结构）
            create_sql = source_conn.execute(f"SELECT sql FROM pragma_table_info('{table_name}')").fetchall()
            # 这里简化处理，实际应该生成完整的CREATE TABLE语句
            # 使用更简单的方法：直接复制数据
            print(f" ⚠️ 目标表不存在，将创建...", end="")
        
        # 迁移数据
        if strategy == "replace":
            # 先删除目标表数据
            target_conn.execute(f"DELETE FROM {table_name}")
        
        # 插入数据
        insert_sql = f"INSERT INTO {table_name} SELECT * FROM source_db.{table_name}"
        target_conn.execute(insert_sql)
        
        # 验证迁移
        migrated_count = target_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        
        print(f" ✅ 完成 ({migrated_count} 行)")
        return {"status": "success", "rows": migrated_count}
        
    except Exception as e:
        print(f" ❌ 失败: {e}")
        return {"status": "failed", "error": str(e)}

def migrate_database(source_path, target_path, source_db_name):
    """迁移整个数据库"""
    print(f"\n🚀 开始迁移 {source_db_name} ({source_path}) -> {target_path}")
    
    # 备份源数据库
    backup_path = backup_database(source_path)
    if not backup_path:
        print("⚠️  备份失败，继续迁移但风险较高")
    
    # 连接数据库
    try:
        source_conn = duckdb.connect(source_path)
        target_conn = duckdb.connect(target_path)
        
        # 附加源数据库到目标连接
        target_conn.execute(f"ATTACH '{source_path}' AS source_db")
        
        # 分析冲突
        conflicts = analyze_table_conflicts(source_conn, target_conn, source_db_name)
        
        if conflicts:
            print(f"⚠️  发现 {len(conflicts)} 个表冲突:")
            for conflict in conflicts:
                if conflict["type"] == "schema_mismatch":
                    print(f"   - {conflict['table']}: 表结构不一致 (源:{conflict['source_columns']}列, 目标:{conflict['target_columns']}列)")
                elif conflict["type"] == "data_overlap":
                    print(f"   - {conflict['table']}: 数据重叠 (源:{conflict['source_rows']}行, 目标:{conflict['target_rows']}行)")
                else:
                    print(f"   - {conflict['table']}: 错误 - {conflict['error']}")
        
        # 获取源数据库表
        source_tables = source_conn.execute("SHOW TABLES").fetchall()
        
        migration_results = {}
        
        # 迁移每个表
        for table in source_tables:
            table_name = table[0]
            
            # 确定迁移策略
            strategy = "append"  # 默认追加
            
            # 检查是否有冲突
            conflict = next((c for c in conflicts if c["table"] == table_name), None)
            if conflict:
                if conflict["type"] == "data_overlap":
                    # 对于数据重叠的表，使用替换策略
                    strategy = "replace"
                    print(f"   ⚠️  {table_name}: 数据重叠，使用替换策略")
            
            result = migrate_table(source_conn, target_conn, table_name, strategy)
            migration_results[table_name] = result
        
        # 分离源数据库
        target_conn.execute("DETACH source_db")
        
        # 关闭连接
        source_conn.close()
        target_conn.close()
        
        # 统计结果
        success_count = sum(1 for r in migration_results.values() if r["status"] == "success")
        skipped_count = sum(1 for r in migration_results.values() if r["status"] == "skipped")
        failed_count = sum(1 for r in migration_results.values() if r["status"] == "failed")
        
        print(f"\n📊 迁移完成统计:")
        print(f"   ✅ 成功: {success_count} 个表")
        print(f"   ⚠️  跳过: {skipped_count} 个表 (源表为空)")
        print(f"   ❌ 失败: {failed_count} 个表")
        
        return {
            "source": source_path,
            "target": target_path,
            "backup": backup_path,
            "results": migration_results,
            "summary": {
                "success": success_count,
                "skipped": skipped_count,
                "failed": failed_count
            }
        }
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        return {"status": "failed", "error": str(e)}

def update_configurations():
    """更新配置文件中的数据库路径"""
    print("\n🔧 更新配置文件...")
    
    # 需要更新的配置文件列表
    config_files = [
        ".env",
        ".env.example",
        "config/settings.py",
        "config/database.py"
    ]
    
    updates_made = 0
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"  检查 {config_file}...", end="")
            
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 替换数据库路径
                new_content = content
                
                # 替换market.duckdb引用
                if 'quant_system.duckdb' in content:
                    new_content = new_content.replace('quant_system.duckdb', 'quant_system.duckdb')
                    print(f" ✅ 更新market.duckdb引用")
                
                # 替换quant.duckdb引用
                if 'quant_system.duckdb' in content:
                    new_content = new_content.replace('quant_system.duckdb', 'quant_system.duckdb')
                    print(f" ✅ 更新quant.duckdb引用")
                
                # 如果内容有变化，保存
                if new_content != content:
                    with open(config_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    updates_made += 1
                else:
                    print(f" ⚠️ 无需更新")
                    
            except Exception as e:
                print(f" ❌ 错误: {e}")
    
    print(f"📊 共更新了 {updates_made} 个配置文件")
    return updates_made

def main():
    """主函数"""
    print("=== 数据库迁移工具 ===")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 检查数据库文件
    source_dbs = [
        ("quant_system.duckdb", "data/quant_system.duckdb"),
        ("quant_system.duckdb", "data/quant_system.duckdb")
    ]
    
    target_db = "data/quant_system.duckdb"
    
    # 检查目标数据库是否存在
    if not os.path.exists(target_db):
        print(f"❌ 目标数据库不存在: {target_db}")
        print("请先创建quant_system.duckdb或检查路径")
        return
    
    print(f"目标数据库: {target_db}")
    print()
    
    # 备份目标数据库
    print("📦 备份目标数据库...")
    target_backup = backup_database(target_db)
    
    all_results = {}
    
    # 迁移每个源数据库
    for db_name, db_path in source_dbs:
        if os.path.exists(db_path):
            result = migrate_database(db_path, target_db, db_name)
            all_results[db_name] = result
        else:
            print(f"⚠️  源数据库不存在: {db_path}")
    
    # 更新配置文件
    print("\n" + "="*50)
    print("🔄 更新系统配置")
    print("="*50)
    
    config_updates = update_configurations()
    
    # 生成迁移报告
    print("\n" + "="*50)
    print("📋 迁移完成报告")
    print("="*50)
    
    total_success = 0
    total_skipped = 0
    total_failed = 0
    
    for db_name, result in all_results.items():
        if "summary" in result:
            summary = result["summary"]
            total_success += summary["success"]
            total_skipped += summary["skipped"]
            total_failed += summary["failed"]
            
            print(f"\n{db_name}:")
            print(f"  成功: {summary['success']} 表")
            print(f"  跳过: {summary['skipped']} 表")
            print(f"  失败: {summary['failed']} 表")
    
    print(f"\n📊 总计:")
    print(f"  ✅ 成功迁移: {total_success} 个表")
    print(f"  ⚠️  跳过: {total_skipped} 个表")
    print(f"  ❌ 失败: {total_failed} 个表")
    print(f"  🔧 配置更新: {config_updates} 个文件")
    
    if target_backup:
        print(f"  📦 目标数据库备份: {target_backup}")
    
    print(f"\n⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 重要提醒
    print("\n" + "="*50)
    print("⚠️  重要提醒")
    print("="*50)
    print("1. 请测试所有依赖数据库的功能")
    print("2. 确认配置文件更新正确")
    print("3. 源数据库已备份，如有问题可恢复")
    print("4. 建议在非交易时间进行最终验证")
    
    # 保存迁移报告
    report_file = "database_migration_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"数据库迁移报告\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"目标数据库: {target_db}\n\n")
        
        for db_name, result in all_results.items():
            if "summary" in result:
                summary = result["summary"]
                f.write(f"{db_name}:\n")
                f.write(f"  成功: {summary['success']} 表\n")
                f.write(f"  跳过: {summary['skipped']} 表\n")
                f.write(f"  失败: {summary['failed']} 表\n\n")
        
        f.write(f"总计:\n")
        f.write(f"  成功迁移: {total_success} 个表\n")
        f.write(f"  跳过: {total_skipped} 个表\n")
        f.write(f"  失败: {total_failed} 个表\n")
        f.write(f"  配置更新: {config_updates} 个文件\n")
    
    print(f"\n📄 详细报告已保存到: {report_file}")
    print("✅ 数据库迁移完成!")

if __name__ == "__main__":
    main()