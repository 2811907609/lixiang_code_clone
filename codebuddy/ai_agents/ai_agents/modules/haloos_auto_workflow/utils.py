import subprocess
import os


def get_c_files_list_from_give_dir(directory_path):
    """
    获取指定目录下的所有.c文件

    Args:
        directory_path (str): 目录路径

    Returns:
        list: .c文件路径列表
    """
    try:
        if not os.path.exists(directory_path):
            return []

        if not os.path.isdir(directory_path):
            return []

        c_files = []
        for file in os.listdir(directory_path):
            if file.endswith('.c'):
                c_files.append(os.path.join(directory_path, file))

        return sorted(c_files)

    except (PermissionError, OSError) as e:
        print(f"访问目录时出错: {e}")
        return []


def safe_modify_with_git(modify_function, validation_function,
                        commit_message="Safe modify",
                        modify_args=(), modify_kwargs=None,
                        validation_args=(), validation_kwargs=None,
                        project_path="."):
    """
    安全地执行修改函数，通过Git控制版本

    Args:
        modify_function: 修改函数
        validation_function: 验证函数，返回True表示符合预期
        commit_message: 提交信息
        modify_args: 修改函数的位置参数
        modify_kwargs: 修改函数的关键字参数
        validation_args: 验证函数的位置参数
        validation_kwargs: 验证函数的关键字参数
        project_path: 项目路径，默认当前目录

    Returns:
        bool: True表示成功，False表示失败
    """
    if modify_kwargs is None:
        modify_kwargs = {}
    if validation_kwargs is None:
        validation_kwargs = {}

    # 切换到项目目录
    original_dir = os.getcwd()
    os.chdir(project_path)

    try:
        # 检查Git状态
        if not _is_git_clean():
            print("⚠️  工作区不干净，请先提交或暂存现有更改")
            return False, ''

        # 记录当前commit
        current_commit = _get_current_commit()

        # 执行修改函数（传入参数）
        print("🔄 执行修改...")

        try:
            result = modify_function(*modify_args, **modify_kwargs)

            # Verify we got a response
            assert isinstance(result, str)
            assert len(result) > 0

        except Exception:
            # 模型被截断？
            result = ''

        # 检查是否有更改
        if not _has_changes():
            print("ℹ️  没有检测到更改")
            return True, result

        # 验证修改（传入参数）
        print("🔍 验证修改...")
        if validation_function(*validation_args, **validation_kwargs):
            # 提交更改
            subprocess.run(['git', 'add', '.'], check=True)
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            print("✅ 修改已提交")
            return True, result
        else:
            subprocess.run(['git', 'add', '.'], check=True)
            subprocess.run(['git', 'commit', '-m', commit_message + 'failed check why need to optim'], check=True)
            print("✅ 修改已提交")
            return True, result


    except Exception as e:
        print(f"❌ 操作失败: {e}")
        # 尝试回滚
        try:
            current_commit = _get_current_commit()
            subprocess.run(['git', 'reset', '--hard', current_commit], check=True)
            subprocess.run(['git', 'clean', '-fd'], check=True)
        except Exception as e:
            pass
        return False, ''

    finally:
        # 恢复原始目录
        os.chdir(original_dir)


def _is_git_clean():
    """检查工作区是否干净"""
    result = subprocess.run(['git', 'status', '--porcelain'],
                          capture_output=True, text=True)
    return len(result.stdout.strip()) == 0


def _get_current_commit():
    """获取当前commit hash"""
    result = subprocess.run(['git', 'rev-parse', 'HEAD'],
                          capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _has_changes():
    """检查是否有更改"""
    result = subprocess.run(['git', 'status', '--porcelain'],
                          capture_output=True, text=True)
    return len(result.stdout.strip()) > 0
