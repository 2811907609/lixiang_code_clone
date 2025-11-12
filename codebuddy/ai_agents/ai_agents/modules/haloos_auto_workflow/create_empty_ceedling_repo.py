# This Python file uses the following encoding: utf-8
# ##############################################################################
# Copyright (c) 2025 Li Auto Inc. and its affiliates
# Licensed under the Apache License, Version 2.0(the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ##############################################################################

import argparse
import sys
import os
import yaml
from pathlib import Path
import shutil
import copy
import subprocess
import re

def get_input_args():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("-c", "--create", required=False, help="创建新的测试套")
    parser.add_argument("-r", "--run", required=False, help="运行测试套")
    parser.add_argument("-s", "--show", required=False, help="展示测试套的结果")

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args = parser.parse_args()
    return args

class CreateCeedlingRepo:
    def __init__(self, base_path, suite_path,create=True):
        self.suite_path = suite_path
        self.base_path = base_path
        self.path_name = os.path.basename(suite_path).split('.')[0]
        self.project_yml = ""
        self.current_file_path = os.path.dirname(os.path.abspath(__file__))
        self.root_path = os.path.abspath(os.path.join(self.current_file_path, "..", ".."))
        self.work_path = os.getcwd()
        self.gcov_path = os.path.join(self.work_path, "gcov_result")
        self.ret_status = 0
        self.total_result = {}
        self.top_path = ""
        self.create = create

    def parse_args(self):
        self.project_yml = os.path.join(self.suite_path, "project.yml")
        self.files_yml = os.path.join(self.suite_path, "files.yml")

    def is_path_exist(self):
        if os.path.exists(self.suite_path) and os.path.isdir(self.suite_path):
            if os.path.exists(self.project_yml) and os.path.isfile(self.project_yml):
                return True
        else:
            return False

    def create_mock_folder(self, add_mock_file=False):
        if add_mock_file:
            Path(os.path.join(self.suite_path, 'mock')).mkdir(exist_ok=True)
            with open(os.path.join(self.suite_path, 'mock', '.gitkeep'), 'w', encoding='utf-8') as f:
                f.write(" ")
        with open(os.path.join(self.suite_path, 'src', '.gitkeep'), 'w', encoding='utf-8') as f:
            f.write(" ")

    def create_files_yml(self):
        data = '''
SRC_FILES: # 添加需要测试的源文件路径, 包括.c和.h, 这些文件在执行python mock_test.py -r xxx时, 会被拷贝到src下
  #- components/memory/memif/src/memif.c
  #- components/memory/memif/inc/memif.h
'''
        with open(self.files_yml, 'w', encoding='utf-8') as f:
            f.write(data)

    def modify_project_yml(self, use_32_bit_for_compile=True):
        data = {}
        with open(self.project_yml, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            print(yaml.dump(data, allow_unicode=True, sort_keys=False))
        # :plugins :enable gcov
        data[':plugins'][':enabled'].append('gcov')

        # add enable ReturnThruPtr_value, IgnoreArg_value
        data[':cmock'][':plugins'].append(':ignore_arg')
        data[':cmock'][':plugins'].append(':return_thru_ptr')

        # :gcov :reports + HtmlDetailed - HtmlBasic
        data[':gcov'][':reports'].remove('HtmlBasic')
        data[':gcov'][':reports'].append('HtmlDetailed')

        data[':defines'][':release'].append('static=')
        data[':defines'][':release'].append('inline=')
        data[':defines'][':release'].append('inline_function=')
        data[':defines'][':test'].append('static=')
        data[':defines'][':test'].append('inline=')
        data[':defines'][':test'].append('inline_function=')

        if use_32_bit_for_compile:
            # 添加 flags 配置
            data[':flags'] = {
                ':test': {
                    ':link': {
                        ':*': ['-m32']
                    },
                    ':compile': {
                        ':*': ['-m32']
                    }
                }
            }
        with open(self.project_yml, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    def create_project_by_ceedling(self):

        os.chdir(self.base_path)
        cmd = f"ceedling new {self.path_name}"
        os.system(cmd)
        self.create_mock_folder()
        # self.create_files_yml()
        self.modify_project_yml()

    def parse_ceedling_result(self, context):
        pattern = re.compile(
            r'TESTED:\s*(\d+)\s*[\r\n]+PASSED:\s*(\d+)\s*[\r\n]+FAILED:\s*(\d+)\s*[\r\n]+IGNORED:\s*(\d+)',
            re.MULTILINE
        )
        match = pattern.search(context)

        if match:
            tested, passed, failed, ignored = map(int, match.groups())
            dict = {
                "TESTED": tested,
                "PASSED": passed,
                "FAILED": failed,
                "IGNORED": ignored,
            }
            self.total_result[self.suite_path] = dict
        else:
            print("没有找到匹配内容")

    def summary_gcov_result(self):
        if os.path.exists(self.gcov_path):
            shutil.rmtree(self.gcov_path)
        os.makedirs(self.gcov_path)
        os.makedirs(os.path.join(self.gcov_path, "src"))

        for root, _, files in os.walk(self.top_path):
            if "gcov_result" not in root: # 防止遍历到自己
                if root.endswith("src"):
                    for file in files:
                        if file.endswith('.c') or file.endswith('.h'):
                            src_file = os.path.join(root, file)
                            dst_file = os.path.join(self.gcov_path, "src", file)
                            shutil.copy2(src_file, dst_file)

                for file in files:
                    if file.endswith('.gcda') or file.endswith('.gcno'):
                        src_file = os.path.join(root, file)
                        dst_file = os.path.join(self.gcov_path, file)
                        shutil.copy2(src_file, dst_file)
        os.chdir(self.gcov_path)
        os.system("gcovr -r . --html-details -o merged.html --gcov-ignore-errors")
        merged_html = os.path.join(self.gcov_path, "merged.html")
        print(f"\ngcov详情查看{merged_html}")
        os.chdir(self.work_path)

    def build_project_by_ceedling(self):
        os.chdir(self.suite_path)
        result = subprocess.run('ceedling clobber', shell=True, capture_output=True, text=True)
        result = subprocess.run('ceedling gcov:all', shell=True, capture_output=True, text=True)
        print(result.stdout)
        print(result.stderr)
        self.ret_status = result.returncode or self.ret_status
        self.parse_ceedling_result(result.stdout + result.stderr)
        os.chdir(self.work_path)


    def show_result(self):
        str_suite = "suite_name"
        str_tested = "TESTED"
        str_passed = "PASSED"
        str_failed = "FAILED"
        str_ignored = "IGNORED"
        print("** SUMARRY **")
        print(f"{str_suite:<64} {str_tested:<7} {str_passed:<7} {str_failed:<7} {str_ignored:<7}")
        for suite, result in self.total_result.items():
            print(f"{suite:<64} {result['TESTED']:<7} {result['PASSED']:<7} {result['FAILED']:<7} {result['IGNORED']:<7}")

    def create_suite(self):
        if self.is_path_exist():
            raise ValueError(f"{self.suite_path} existed, can not create new one!")
        else:
            self.create_project_by_ceedling()

    def run_suite(self):
        self.top_path = copy.deepcopy(self.suite_path)
        for dirpath, _, filenames in os.walk(self.top_path):
            if 'project.yml' in filenames:
                self.suite_path = dirpath
                self.project_yml = os.path.join(self.suite_path, "project.yml")
                self.files_yml = os.path.join(self.suite_path, "files.yml")
                print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
                print("READY TO RUN", self.suite_path)
                # self.read_file_yml_and_copy_src()
                self.build_project_by_ceedling()
        self.show_result()
        self.summary_gcov_result()


    def show_suite(self):
        pass

    def main(self):
        self.parse_args()
        if self.create:
            self.create_suite()
        else:
            raise ValueError("Invalid argument")
        # exit(self.ret_status)
