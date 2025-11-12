
import filecmp
import os

def compare_files_filecmp(file1, file2):
    """使用filecmp模块比较两个文件"""
    return filecmp.cmp(file1, file2, shallow=False)


def trace_dir_for_verify(dir_path):

    false_list = []
    for path_item in os.listdir(dir_path):

        read_me = os.path.join(dir_path,path_item,'README.txt')
        with open(read_me,'r') as f:
            souece_file_name = f.read().strip()

        file_base_name = os.path.basename(souece_file_name)

        now_file = os.path.join(dir_path,path_item,'src',file_base_name)

        compare_flag = compare_files_filecmp(souece_file_name,now_file)

        if compare_flag:
            print("pass: ",path_item, "souece_file_name: ", souece_file_name, "now_file: ", now_file)
        else:
            false_list.append(path_item)

    print("false",false_list)
