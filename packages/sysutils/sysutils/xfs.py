import os


def print_tree(start_path, level=2):
    print('\n')

    def _print_tree(directory_path, current_level, max_level, prefix=''):
        if current_level > max_level:
            return

        contents = sorted(os.listdir(directory_path))
        for i, name in enumerate(contents):
            path = os.path.join(directory_path, name)
            is_last = (i == len(contents) - 1)

            if os.path.isdir(path):
                # print(f"{prefix}{'└── ' if is_last else '├── '}{name}")
                print(f"{prefix}{'    ' if is_last else '    '}{name}")
                _print_tree(path, current_level + 1, max_level,
                            f"{prefix}{'    ' if is_last else '│   '}")
            else:
                # print(f"{prefix}{'└── ' if is_last else '├── '}{name}")
                print(f"{prefix}{'    ' if is_last else '    '}{name}")

    _print_tree(start_path, 1, level)


def count_files(dir, ignore_git_dir=True):
    count = 0
    if dir is None:
        return count
    git_dir = os.path.join(dir, '.git')
    if git_dir is None:
        return count
    for root, _dirs, files in os.walk(dir):
        if ignore_git_dir and root.startswith(git_dir):
            continue
        count += len(files)
    return count
