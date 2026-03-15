#!/usr/bin/env python3
"""
代码质量检查脚本
运行基本的代码质量检查：pylint、flake8、black检查
"""

import os
import subprocess
import sys
from pathlib import Path


def run_pylint():
    """运行pylint检查"""
    print("=" * 60)
    print("运行 pylint 检查...")
    print("=" * 60)

    # 检查pylint是否安装
    try:
        subprocess.run(
            [sys.executable, "-m", "pylint", "--version"], check=True, capture_output=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠ pylint 未安装，跳过检查")
        print("  安装命令: pip install pylint")
        return False

    # 运行pylint检查关键模块
    modules_to_check = [
        "openclaw_engine",
        "data_engine",
        "data_pipeline",
        "strategy_engine/src/strategies",
    ]

    all_passed = True
    for module in modules_to_check:
        module_path = Path(module)
        if module_path.exists():
            print(f"\n检查模块: {module}")
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pylint",
                        module,
                        "--rcfile=.pylintrc" if Path(".pylintrc").exists() else "",
                    ],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    print(f"  ✅ {module}: 通过")
                else:
                    print(f"  ⚠ {module}: 发现问题")
                    # 只显示前10行错误信息，避免输出过多
                    errors = result.stderr if result.stderr else result.stdout
                    error_lines = errors.split("\n")[:10]
                    for line in error_lines:
                        if line.strip():
                            print(f"    {line}")
                    all_passed = False
            except Exception as e:
                print(f"  ✗ {module}: 检查失败 - {e}")
                all_passed = False
        else:
            print(f"  ℹ️ {module}: 模块不存在，跳过")

    return all_passed


def run_flake8():
    """运行flake8检查"""
    print("\n" + "=" * 60)
    print("运行 flake8 检查...")
    print("=" * 60)

    # 检查flake8是否安装
    try:
        subprocess.run(
            [sys.executable, "-m", "flake8", "--version"], check=True, capture_output=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠ flake8 未安装，跳过检查")
        print("  安装命令: pip install flake8")
        return False

    # 运行flake8检查
    try:
        result = subprocess.run(
            [sys.executable, "-m", "flake8", "."], capture_output=True, text=True
        )

        if result.returncode == 0:
            print("✅ flake8: 通过")
            return True
        else:
            print("⚠ flake8: 发现问题")
            # 只显示前10行错误信息
            errors = result.stderr if result.stderr else result.stdout
            error_lines = errors.split("\n")[:10]
            for line in error_lines:
                if line.strip():
                    print(f"  {line}")

            total_errors = len(errors.split("\n")) - 1
            print(f"\n  共发现 {total_errors} 个问题（显示前10个）")
            print("  运行 'python -m flake8 .' 查看全部问题")
            return False
    except Exception as e:
        print(f"✗ flake8检查失败: {e}")
        return False


def check_black_formatting():
    """检查代码是否符合black格式"""
    print("\n" + "=" * 60)
    print("检查 black 代码格式...")
    print("=" * 60)

    # 检查black是否安装
    try:
        subprocess.run(
            [sys.executable, "-m", "black", "--version"], check=True, capture_output=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠ black 未安装，跳过检查")
        print("  安装命令: pip install black")
        return None

    # 检查代码格式
    try:
        result = subprocess.run(
            [sys.executable, "-m", "black", "--check", "."], capture_output=True, text=True
        )

        if result.returncode == 0:
            print("✅ black: 代码格式正确")
            return True
        else:
            print("⚠ black: 代码格式需要调整")
            # 显示需要格式化的文件
            output = result.stdout if result.stdout else result.stderr
            files_to_format = []
            for line in output.split("\n"):
                if line.startswith("would reformat") or line.startswith("Oh no!"):
                    print(f"  {line}")
                    # 提取文件名
                    if " " in line:
                        parts = line.split(" ")
                        for part in parts:
                            if part.endswith(".py"):
                                files_to_format.append(part)

            if files_to_format:
                print(f"\n  需要格式化的文件: {len(files_to_format)} 个")
                print("  运行 'python -m black .' 自动格式化")

            return False
    except Exception as e:
        print(f"✗ black检查失败: {e}")
        return None


def create_code_quality_configs():
    """创建代码质量配置文件"""
    print("\n" + "=" * 60)
    print("创建代码质量配置文件...")
    print("=" * 60)

    configs_created = []

    # 1. 创建 .pylintrc
    pylintrc_content = """[MASTER]
jobs=0
persistent=yes

[MESSAGES CONTROL]
disable=
    C0103,  # invalid-name (变量名规范)
    C0114,  # missing-module-docstring (模块文档字符串)
    C0115,  # missing-class-docstring (类文档字符串)
    C0116,  # missing-function-docstring (函数文档字符串)
    R0902,  # too-many-instance-attributes (太多实例属性)
    R0903,  # too-few-public-methods (太少公共方法)
    R0913,  # too-many-arguments (太多参数)
    R0914,  # too-many-locals (太多局部变量)
    W0613,  # unused-argument (未使用的参数)
    W0718,  # broad-exception-caught (捕获太宽泛的异常)

[FORMAT]
max-line-length=100
indent-after-paren=4
single-line-if-stmt=no

[BASIC]
good-names=i,j,k,ex,Run,_
bad-names=foo,bar,baz,toto,tutu,tata

[DESIGN]
max-args=7
max-locals=20
max-returns=6
max-branches=15
max-statements=60
max-parents=7
max-attributes=12

[IMPORTS]
deprecated-modules=
preferred-modules=
    pandas:pd,
    numpy:np,
    datetime:dt

[TYPECHECK]
ignored-modules=
ignored-classes=optparse.Values,thread._local,_thread._local
"""

    try:
        with open(".pylintrc", "w") as f:
            f.write(pylintrc_content)
        configs_created.append(".pylintrc")
        print("✅ 创建 .pylintrc 配置文件")
    except Exception as e:
        print(f"✗ 创建 .pylintrc 失败: {e}")

    # 2. 创建 .flake8
    flake8_content = """[flake8]
max-line-length = 100
exclude = .git,__pycache__,build,dist,.venv,venv
ignore = 
    E203,  # whitespace before ':'
    E266,  # too many leading '#' for block comment
    W503,  # line break before binary operator
    W504,  # line break after binary operator
    C901,  # too complex
per-file-ignores = 
    __init__.py:F401
"""

    try:
        with open(".flake8", "w") as f:
            f.write(flake8_content)
        configs_created.append(".flake8")
        print("✅ 创建 .flake8 配置文件")
    except Exception as e:
        print(f"✗ 创建 .flake8 失败: {e}")

    # 3. 更新 pyproject.toml
    try:
        with open("pyproject.toml", "r") as f:
            pyproject_content = f.read()

        # 添加black配置
        if "[tool.black]" not in pyproject_content:
            black_config = """

[tool.black]
line-length = 100
target-version = ['py310']
include = '\\.pyi?$'
extend-exclude = '''
/(
  \\.eggs
  | \\.git
  | \\.hg
  | \\.mypy_cache
  | \\.tox
  | \\.venv
  | _build
  | buck-out
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
"""
            with open("pyproject.toml", "a") as f:
                f.write(black_config)
            configs_created.append("pyproject.toml (更新)")
            print("✅ 更新 pyproject.toml 添加 black/isort 配置")
    except Exception as e:
        print(f"✗ 更新 pyproject.toml 失败: {e}")

    return configs_created


def main():
    """主函数"""
    print("=" * 60)
    print("代码质量检查工具")
    print("=" * 60)
    print(f"项目路径: {os.getcwd()}")
    print(f"Python版本: {sys.version.split()[0]}")
    print()

    # 检查是否需要创建配置文件
    config_files = [".pylintrc", ".flake8"]
    missing_configs = [f for f in config_files if not Path(f).exists()]

    if missing_configs:
        print(f"发现缺失的配置文件: {', '.join(missing_configs)}")
        # 自动创建配置文件（非交互模式）
        print("自动创建代码质量配置文件...")
        created = create_code_quality_configs()
        if created:
            print(f"\n✅ 已创建配置文件: {', '.join(created)}")

    # 运行检查
    print("\n" + "=" * 60)
    print("开始代码质量检查")
    print("=" * 60)

    results = []

    # 运行各种检查
    results.append(("pylint", run_pylint()))
    results.append(("flake8", run_flake8()))
    black_result = check_black_formatting()
    if black_result is not None:
        results.append(("black", black_result))

    # 汇总结果
    print("\n" + "=" * 60)
    print("检查结果汇总")
    print("=" * 60)

    passed = 0
    total = 0

    for tool_name, result in results:
        total += 1
        if result:
            passed += 1
            status = "✅ 通过"
        elif result is False:
            status = "⚠ 发现问题"
        else:
            status = "ℹ️ 跳过"
            total -= 1  # 不计入总数

        print(f"{tool_name:10} {status}")

    if total > 0:
        print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")

    # 提供建议
    print("\n" + "=" * 60)
    print("下一步建议")
    print("=" * 60)

    if passed < total:
        print("需要改进的方面:")
        if any(tool == "pylint" and not result for tool, result in results):
            print("1. 修复pylint发现的问题")
            print("   运行: python -m pylint . --rcfile=.pylintrc")
        if any(tool == "flake8" and not result for tool, result in results):
            print("2. 修复flake8发现的问题")
            print("   运行: python -m flake8 .")
        if any(tool == "black" and not result for tool, result in results):
            print("3. 使用black格式化代码")
            print("   运行: python -m black .")

        print("\n自动化修复命令:")
        print("  python -m black .  # 格式化代码")
        print("  python check_code_quality.py  # 重新检查")
    else:
        print("✅ 代码质量良好！")

    print("\n" + "=" * 60)

    # 返回适当的退出码
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
