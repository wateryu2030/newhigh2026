#!/usr/bin/env python3
"""
简化版数据库迁移脚本
策略: 只迁移quant数据库的数据，market数据库基本为空，可以忽略
"""

import duckdb
import os
import time
from datetime import datetime

def log(message):
    """记录日志"""
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] {message}")
    return f"[{timestamp}] {message}"

def main():
    """主函数"""
    print("=== 简化版数据库迁移 ===")
    print("策略: 只迁移quant数据库的重要数据")
    print()

    # 检查备份
    backup_dir = "data/backup_20260314"
    if not os.path.exists(backup_dir):
        print("错误: 备份目录不存在")
        return False

    print("✅ 备份检查通过")

    # 分析quant数据库
    quant_db = "data/quant_system.duckdb"
    target_db = "data/quant_system.duckdb"

    if not os.path.exists(quant_db):
        print(f"错误: quant数据库不存在: {quant_db}")
        return False

    if not os.path.exists(target_db):
        print(f"错误: 目标数据库不存在: {target_db}")
        return False

    print(f"源数据库: {quant_db}")
    print(f"目标数据库: {target_db}")
    print()

    migration_log = []

    try:
        # 连接到quant数据库
        quant_conn = duckdb.connect(quant_db)

        # 获取quant数据库的表
        quant_tables_result = quant_conn.execute('SHOW TABLES').fetchall()
        quant_tables = [table[0] for table in quant_tables_result]

        print(f"quant数据库有 {len(quant_tables)} 个表:")
        for table in quant_tables:
            count_result = quant_conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()
            row_count = count_result[0] if count_result else 0
            print(f"  - {table}: {row_count} 行")

        print()

        # 连接到目标数据库
        target_conn = duckdb.connect(target_db)

        # 获取目标数据库的表
        target_tables_result = target_conn.execute('SHOW TABLES').fetchall()
        target_tables = [table[0] for table in target_tables_result]

        print(f"目标数据库有 {len(target_tables)} 个表")
        print()

        # 迁移策略: 只迁移daily_bars表（最重要的历史数据）
        tables_to_migrate = ["daily_bars", "news_items", "stocks"]

        for table in tables_to_migrate:
            if table not in quant_tables:
                print(f"跳过: {table} 不在quant数据库中")
                continue

            # 检查表数据量
            count_result = quant_conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()
            row_count = count_result[0] if count_result else 0

            if row_count == 0:
                print(f"跳过: {table} 是空表")
                continue

            print(f"处理表: {table} ({row_count}行)")

            if table in target_tables:
                print(f"  表已存在，检查是否需要更新...")

                # 检查目标表的数据量
                target_count_result = target_conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()
                target_row_count = target_count_result[0] if target_count_result else 0

                if target_row_count > 0:
                    print(f"  目标表已有 {target_row_count} 行数据")

                    # 简单策略: 如果目标表数据量少，则补充数据
                    if target_row_count < row_count:
                        print(f"  目标表数据较少，补充数据...")

                        # 使用临时表避免重复
                        temp_table = f"temp_{table}"

                        # 创建临时表并导入quant数据
                        quant_conn.execute(f'CREATE TEMPORARY TABLE {temp_table} AS SELECT * FROM {table}')

                        # 找出目标表中没有的数据
                        # 这里简化处理: 假设有date和symbol列
                        try:
                            # 尝试找出最新的日期
                            latest_date_result = target_conn.execute(f'SELECT MAX(date) FROM {table}').fetchone()
                            latest_date = latest_date_result[0] if latest_date_result else None

                            if latest_date:
                                print(f"  目标表最新日期: {latest_date}")

                                # 导入最新日期之后的数据
                                quant_conn.execute(f'''
                                    CREATE TEMPORARY TABLE new_data AS
                                    SELECT * FROM {temp_table}
                                    WHERE date > '{latest_date}'
                                ''')

                                new_count_result = quant_conn.execute('SELECT COUNT(*) FROM new_data').fetchone()
                                new_count = new_count_result[0] if new_count_result else 0

                                if new_count > 0:
                                    print(f"  找到 {new_count} 条新数据")

                                    # 导出到临时文件
                                    temp_file = f'temp_new_{table}.parquet'
                                    quant_conn.execute(f'COPY new_data TO \'{temp_file}\' (FORMAT PARQUET)')

                                    # 导入到目标表
                                    target_conn.execute(f'COPY {table} FROM \'{temp_file}\' (FORMAT PARQUET)')

                                    # 清理临时文件
                                    if os.path.exists(temp_file):
                                        os.remove(temp_file)

                                    print(f"  成功导入 {new_count} 条新数据")
                                else:
                                    print(f"  没有找到新数据")
                            else:
                                print(f"  无法确定最新日期，跳过此表")

                        except Exception as e:
                            print(f"  处理失败: {e}")
                            print(f"  使用简单追加策略...")

                            # 简单追加策略
                            temp_file = f'temp_{table}.parquet'
                            quant_conn.execute(f'COPY {temp_table} TO \'{temp_file}\' (FORMAT PARQUET)')
                            target_conn.execute(f'COPY {table} FROM \'{temp_file}\' (FORMAT PARQUET)')

                            if os.path.exists(temp_file):
                                os.remove(temp_file)

                            print(f"  追加了 {row_count} 行数据")

                    else:
                        print(f"  目标表数据量足够，跳过")
                else:
                    print(f"  目标表是空的，直接导入数据...")

                    # 直接导入数据
                    temp_file = f'temp_{table}.parquet'
                    quant_conn.execute(f'COPY {table} TO \'{temp_file}\' (FORMAT PARQUET)')
                    target_conn.execute(f'COPY {table} FROM \'{temp_file}\' (FORMAT PARQUET)')

                    if os.path.exists(temp_file):
                        os.remove(temp_file)

                    print(f"  成功导入 {row_count} 行数据")

            else:
                print(f"  表不存在，创建并导入数据...")

                # 获取表结构
                create_table_sql = quant_conn.execute(f'SELECT sql FROM sqlite_master WHERE type="table" AND name="{table}"').fetchone()

                if create_table_sql:
                    # 在目标数据库创建表
                    target_conn.execute(create_table_sql[0])

                    # 复制数据
                    temp_file = f'temp_{table}.parquet'
                    quant_conn.execute(f'COPY {table} TO \'{temp_file}\' (FORMAT PARQUET)')
                    target_conn.execute(f'COPY {table} FROM \'{temp_file}\' (FORMAT PARQUET)')

                    if os.path.exists(temp_file):
                        os.remove(temp_file)

                    print(f"  成功创建表并导入 {row_count} 行数据")

        quant_conn.close()
        target_conn.close()

        print()
        print("✅ 数据库迁移完成")

        # 验证迁移结果
        print()
        print("=== 迁移结果验证 ===")

        target_conn = duckdb.connect(target_db)
        for table in tables_to_migrate:
            try:
                count_result = target_conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()
                row_count = count_result[0] if count_result else 0
                print(f"{table}: {row_count} 行")
            except:
                print(f"{table}: 表不存在或查询失败")

        target_conn.close()

        return True

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        return False

if __name__ == "__main__":
    success = main()

    if success:
        print("\n🎉 数据库统一完成!")
        print("下一步: 更新代码中的数据库引用")
    else:
        print("\n💥 数据库统一失败!")
        print("请检查错误信息")