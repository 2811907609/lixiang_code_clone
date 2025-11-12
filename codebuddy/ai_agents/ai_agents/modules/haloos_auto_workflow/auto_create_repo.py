
import shutil
import os
from ai_agents.modules.haloos_auto_workflow.create_empty_ceedling_repo import CreateCeedlingRepo

def find_c_files(folder_path):
    """递归搜索文件夹中的所有.c文件"""
    c_files = []

    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.c'):
                full_path = os.path.join(root, file)
                c_files.append(full_path)

    return c_files


def get_testcase_repo_dir_name(write_repo, read_file):
    basename = os.path.basename(read_file).split('.')[0]

    write_repo_name = basename + '_test'

    return os.path.join(write_repo, write_repo_name)

def create_gitignore_with_build(path):
    """
    在指定路径下创建.gitignore文件，并写入'build'
    :param path: 文件夹路径（str）
    """
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
    gitignore_path = os.path.join(path, '.gitignore')
    with open(gitignore_path, 'w', encoding='utf-8') as f:
        f.write('build\n')


def move_and_copy_to_src(src_file, target_dir):
    """
    将src_file移动到target_dir下，并在target_dir/src下复制一份
    :param src_file: 源文件路径
    :param target_dir: 目标文件夹路径
    """
    if not os.path.isfile(src_file):
        raise FileNotFoundError(f"源文件 {src_file} 不存在")

    target_dir = os.path.join(target_dir, 'src')

    src_copy_file = os.path.join(target_dir, os.path.basename(src_file))
    # 复制移动后的目标文件到 src 子目录下
    print("src_file",src_file)
    print("src_copy_file",src_copy_file)
    shutil.copy2(src_file, src_copy_file)

    # 修改文件权限为544
    os.chmod(src_copy_file, 0o544)

    # 修改target_dir权限为555
    os.chmod(target_dir, 0o555)

# 更原子的操作：给定源文件路径，创建文件
def use_source_file_create_empty_ceedling_repo(source_file_full_path, output_write_repo_path):

    repo_path = get_testcase_repo_dir_name(output_write_repo_path, source_file_full_path)

    print(f'开始创建{repo_path}')

    mocks = CreateCeedlingRepo(output_write_repo_path, repo_path)
    mocks.main()

    print('************************************************')
    # gitignore文件
    create_gitignore_with_build(repo_path)

    # 源文件路径copy到src下
    move_and_copy_to_src(source_file_full_path, repo_path)

    # git init
    os.system(f'cd {repo_path} && git init')
    # git add .
    os.system(f'cd {repo_path} && git add .')
    # git commit -m "init"
    os.system(f'cd {repo_path} && git commit -m "init"')

    return repo_path
