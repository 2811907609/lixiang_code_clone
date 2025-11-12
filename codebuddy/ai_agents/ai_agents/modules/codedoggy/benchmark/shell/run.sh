#!/bin/bash
# run_benchmark.sh
# ---------------------
# 运行 Python 脚本，并保证 SSH 断开后仍继续运行直到任务结束
# ---------------------

# 设置环境变量（按需修改）demo.env
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="./benchmark_$TIMESTAMP.log"

# 3. 启动 Python 脚本（nohup 后台运行，输出到日志）
nohup python ../main.py \
    > "$LOG_FILE" 2>&1 &

# 4. 显示信息
PID=$!
echo "任务已启动 (PID=$PID)"
echo "日志文件: $LOG_FILE"
echo "实时查看日志： tail -f $LOG_FILE"
