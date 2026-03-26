#!/usr/bin/env python3
"""
清理旧数据库文件 - 在确认迁移成功后，可以清理旧的数据库文件
注意: 这是一个破坏性操作，需要谨慎执行
"""

import os
import shutil
from datetime import datetime

def check_migration_success():
    """检查迁移是否成功"""
    print("🔍 检查数据库迁移状态...")

    target_db = "data/quant_system.duckdb"
    old_dbs = ["data/market.duckdb", "data/quant.duckdb"]

    # 检查目标数据库是否存在
    if not os.path.exists(target_db):
        print(f"❌ 目标数据库不存在: {target_db}")
        return False

    # 检查目标数据库的关键表
    try:
        import duckdb
        conn = duckdb.connect(target_db)

        # 检查关键表
        key_tables = ['daily_bars', 'stocks', 'news_items', 'market_emotion_state']
        all_exist = True

        for table in key_tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"  {table}: {count:,} 行")
                if count == 0 and table in ['daily_bars', 'stocks']:
                    print(f"  ⚠️  {table} 表为空，但应该是关键表")
            except:
                print(f"  ❌ {table}: 表不存在或读取错误")
                all_exist = False

        conn.close()

        if not all_exist:
            print("⚠️  部分关键表不存在，迁移可能不完整")
            return False

    except Exception as e:
        print(f"❌ 检查目标数据库失败: {e}")
        return False

    return True

def backup_old_databases():
    """备份旧数据库"""
    print("\n📦 备份旧数据库...")

    backup_dir = "backups/old_databases"
    os.makedirs(backup_dir, exist_ok=True)

    old_dbs = ["data/market.duckdb", "data/quant.duckdb"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backed_up = []

    for db_path in old_dbs:
        if os.path.exists(db_path):
            backup_path = os.path.join(backup_dir, f"{os.path.basename(db_path)}.backup_{timestamp}")
            try:
                shutil.copy2(db_path, backup_path)
                print(f"  ✅ {db_path} -> {backup_path}")
                backed_up.append(db_path)
            except Exception as e:
                print(f"  ❌ 备份失败 {db_path}: {e}")
                return False
        else:
            print(f"  ⚠️  {db_path} 不存在")

    return len(backed_up) > 0

def cleanup_old_databases():
    """清理旧数据库"""
    print("\n🗑️  清理旧数据库...")

    old_dbs = ["data/market.duckdb", "data/quant.duckdb"]

    for db_path in old_dbs:
        if os.path.exists(db_path):
            try:
                # 移动到回收站而不是直接删除
                trash_dir = "trash"
                os.makedirs(trash_dir, exist_ok=True)
                trash_path = os.path.join(trash_dir, os.path.basename(db_path))

                shutil.move(db_path, trash_path)
                print(f"  ✅ 已移动到回收站: {db_path} -> {trash_path}")
            except Exception as e:
                print(f"  ❌ 清理失败 {db_path}: {e}")
                return False
        else:
            print(f"  ⚠️  {db_path} 不存在")

    return True

def verify_cleanup():
    """验证清理结果"""
    print("\n🔍 验证清理结果...")

    old_dbs = ["data/market.duckdb", "data/quant.duckdb"]
    target_db = "data/quant_system.duckdb"

    all_cleaned = True
    for db_path in old_dbs:
        if os.path.exists(db_path):
            print(f"  ❌ {db_path} 仍然存在")
            all_cleaned = False
        else:
            print(f"  ✅ {db_path} 已清理")

    if os.path.exists(target_db):
        size_mb = os.path.getsize(target_db) / (1024 * 1024)
        print(f"  ✅ {target_db} 存在 ({size_mb:.2f} MB)")
    else:
        print(f"  ❌ {target_db} 不存在")
        all_cleaned = False

    return all_cleaned

def main():
    """主函数"""
    print("=== 清理旧数据库工具 ===")
    print("注意: 这是一个破坏性操作，请确保数据库迁移已成功完成")
    print()

    # 检查迁移状态
    if not check_migration_success():
        print("\n❌ 数据库迁移可能未完成，不建议清理旧数据库")
        print("请先完成数据库迁移，或手动检查迁移状态")
        return

    # 确认用户意图
    print("\n⚠️  警告: 这将清理旧的数据库文件 (market.duckdb, quant.duckdb)")
    print("这些文件将被移动到回收站目录")
    print()

    confirm = input("是否继续? (输入 'YES' 确认): ")
    if confirm != "YES":
        print("操作已取消")
        return

    # 备份旧数据库
    if not backup_old_databases():
        print("❌ 备份失败，操作已取消")
        return

    # 清理旧数据库
    if not cleanup_old_databases():
        print("❌ 清理失败")
        return

    # 验证清理结果
    if verify_cleanup():
        print("\n✅ 清理完成!")
        print("旧数据库已移动到 trash/ 目录")
        print("所有功能现在使用 quant_system.duckdb")
    else:
        print("\n⚠️  清理可能不完整，请手动检查")

if __name__ == "__main__":
    main()