#!/bin/bash
export PATH="/usr/bin:$PATH"
export PYTHON="/usr/bin/python3"

# 预定义信息
COV_EVALUATION_DIRPATH=/home/chehejia/programs/lixiang/cov-evalution/
export COVERITY_ANALYSE_LOGPATH="${COV_EVALUATION_DIRPATH}/mvbs/logs/coverity_analyse.log"
export RAW_ALL_ERRORS_JSONPATH="${COV_EVALUATION_DIRPATH}/all_errors.json"
export WORK_DIR="${COV_EVALUATION_DIRPATH}/mvbs"
export AGENT_DIR="${COV_EVALUATION_DIRPATH}/agent"
export RAW_CONTENT_HASH_KEY_2_ISSUE_DICT_JSONPATH="${COV_EVALUATION_DIRPATH}/mvbs/logs/raw_content_hash_key_2_issue_dict.json"
export NEW_CONTENT_HASH_KEY_2_ISSUE_DICT_JSONPATH="${COV_EVALUATION_DIRPATH}/mvbs/logs/new_content_hash_key_2_issue_dict.json"
export COV_DIR=/data/jenkins/cov-int
export FILES_DIRPATH=${COV_EVALUATION_DIRPATH}/files
export LOG_DIRPATH="/home/chehejia/programs/lixiang/code-complete/codebuddy/ai_agents/examples/logs"

exec_dirpath=/home/chehejia/programs/lixiang/code-complete/codebuddy/ai_agents/
cd ${exec_dirpath}
source ${exec_dirpath}/.env.zyy.sh
uv sync --extra haloos
uv pip list
# 静态检测修复脚本 - 精简版
# 用法: ./static_detection_repair_simple.sh [日志后缀]
# 示例: ./static_detection_repair_simple.sh test_run


# LOG_SUFFIX="${1:-$(date '+%Y%m%d')}"
# DATE="$(date '+%Y%m%d')"

# 获取日志后缀参数
# LOG_SUFFIX="${1:-$(date '+%Y%m%d')}"
# 设置日志目录和文件
# LOG_DIR="./logs"
LOG_DIR="${exec_dirpath}/examples/logs"
DATE="$(date '+%Y%m%d')"
mkdir -p ${LOG_DIR}/${DATE}
LOG_SUFFIX=$1
WORK_DIR=$2
COMBINED_LOG="${LOG_DIR}/${DATE}/static_detection_repair_${LOG_SUFFIX}.log"
ERROR_LOG="${LOG_DIR}/${DATE}/static_detection_repair_error_${LOG_SUFFIX}.log"
echo "DATE=${DATE}"

# 创建日志目录
mkdir -p "$LOG_DIR"

echo "=== 静态检测修复任务开始 ===" | tee "$COMBINED_LOG"
echo "开始时间: $(date)" | tee -a "$COMBINED_LOG"
echo "日志后缀: $LOG_SUFFIX" | tee -a "$COMBINED_LOG"
echo "整体日志: $COMBINED_LOG" | tee -a "$COMBINED_LOG"
echo "错误日志: $ERROR_LOG" | tee -a "$COMBINED_LOG"
echo "================================" | tee -a "$COMBINED_LOG"
echo "" | tee -a "$COMBINED_LOG"

# 执行主程序，保存整体日志和错误日志
exec_pypath="${exec_dirpath}/examples/static_detection_repair.py"
echo "执行命令: uv run static_detection_repair.py" | tee -a "$COMBINED_LOG"
echo "--------------------------------" | tee -a "$COMBINED_LOG"

# WORKDIR="/home/chehejia/programs/lixiang/cov-evalution/mvbs"

{
    uv run ${exec_pypath} --workdir ${WORK_DIR}
    EXIT_CODE=$?
} 2> >(tee -a "$ERROR_LOG" >&2) | tee -a "$COMBINED_LOG"

# 记录结束信息
echo "" | tee -a "$COMBINED_LOG"
echo "================================" | tee -a "$COMBINED_LOG"
echo "结束时间: $(date)" | tee -a "$COMBINED_LOG"
echo "退出代码: $EXIT_CODE" | tee -a "$COMBINED_LOG"
echo "=== 静态检测修复任务完成 ===" | tee -a "$COMBINED_LOG"

# 显示日志文件信息
echo ""
echo "📁 日志文件已保存："
echo "   整体日志: $COMBINED_LOG"
echo "   错误日志: $ERROR_LOG"
echo ""
echo "💡 查看日志命令："
echo "   tail -f $COMBINED_LOG        # 实时查看整体日志"
echo "   less $COMBINED_LOG           # 分页查看整体日志"
echo "   cat $ERROR_LOG               # 查看错误日志"

# 退出时使用原程序的退出代码
exit $EXIT_CODE
