## **1. 任务名称**
AI CodeReview 建议结果匹配与准确性分析


## **2. 任务目标**
对 AI CodeReview 工具生成的问题建议进行验证，完成以下两个分析任务：

1. **已知问题匹配判断**
   判断 AI 生成的建议是否匹配到已知问题列表中的问题。

2. **建议准确性判断**
   判断 AI 建议在当前代码上下文中是否准确有效。


## **3. 任务输入**

### **3.1 已知问题列表（expect_suggestions）**
- **名称**：`expect_suggestions`
- **结构**：
```json
{
  "文件路径": [
    {
      "resolveCode": "string - 原解决代码片段",
      "suggestionContent": "string - 建议描述",
      "suggestionLine": 123
    }
  ]
}
```
- **说明**：
  - `文件路径`为相对于仓库根目录的路径
  - `suggestionLine` 是建议涉及的代码行号
  - `resolveCode` 原解决代码片段，便于匹配验证

#### **示例**
```json
{
  "expect_suggestions": {
    "config_plug_in/generator/context/functions.py": [
      {
        "resolveCode": "for core_name, value in core_cfg.items(): ...",
        "suggestionContent": "变量 core_number 可能未赋值",
        "suggestionLine": 140
      }
    ],
    "inc/rtfw_task_internal.h": [
      {
        "resolveCode": "#if defined(CONFIG_RT_FRAMEWORK_SHARE_TASK_STACK) ...",
        "suggestionContent": "新增宏定义缺少条件编译保护",
        "suggestionLine": 57
      }
    ]
  }
}
```

### **3.2 AI 生成建议列表**
- **名称**：`ai_suggestions`
- **结构**：
```json
[
  {
    "relevantFile": "string - 归属文件路径",
    "existingCode": "string - 原始代码段",
    "improvedCode": "string - 改进后代码段",
    "suggestionContent": "string - 建议描述",
    "suggestionLine": 56,
    "label": "string - 建议类型标签",
    "score": 8,
    "why": "string - 原因说明",
    "message": "string - 完整文本建议"
  }
]
```

#### **示例**
```json
[
  {
    "relevantFile": "services/copilot/server/routes.go",
    "existingCode": "user, err := s.GetFullUserInfoByToken(token) ...",
    "improvedCode": "user, err := s.GetFullUserInfoByToken(token) ... if user == nil { ... }",
    "suggestionContent": "返回 (pointer, error) 时未检测 user 是否为 nil",
    "label": "逻辑问题",
    "suggestionLine": 56,
    "score": 8,
    "why": "如果 user 为 nil 而 err 为空，将造成空指针引用",
    "message": "完整建议内容"
  }
]
```


### **3.3 Diff 信息**
- 原始 Git diff 文本或已解析的结构化 diff
- 用于辅助上下文提取


### **3.4 任务元信息**
- commit hash / PR 编号 / branch 等
- 用于确保上下文准确性


## **4. 任务输出**

### **4.1 输出规则**
- 核心输出字段由 Agent 保证：
  - `recognized_known_issues_count`：正确识别的已知问题个数
  - `known_issues_total`：已知问题总数
  - `valid_ai_issues_count`：有效建议个数（上下文确认有效）
  - `ai_generated_issues_total`：AI 生成建议总数
  - `matched_known_issues`：命中的已知问题详细列表
  - `invalid_ai_issues`：错误建议列表

- 允许额外扩展字段（如匹配原因、判断依据、版本号、调试信息等）


### **4.2 输出结构示例**
```json
{
  "recognized_known_issues_count": 8,
  "known_issues_total": 10,
  "valid_ai_issues_count": 9,
  "ai_generated_issues_total": 12,
  "matched_known_issues": [
    {
      "file_path": "config_plug_in/generator/context/functions.py",
      "line": 140,
      "description": "变量 core_number 可能未赋值"
    }
  ],
  "invalid_ai_issues": [
    {
      "file_path": "services/copilot/server/routes.go",
      "line": 56,
      "description": "缺少 user == nil 检查"
    }
  ],
  "score_distribution": {
    "high": 5,
    "medium": 4,
    "low": 3
  },
  "meta_agent_version": "1.1.0"
}
```

## **5. 注意事项**
- 文件路径与行号匹配需容忍小范围偏移（根据diff变更情况）
- 核心字段输出必须完整，不得缺失或乱序
- 相似度匹配需允许轻微语义差异
- 已知问题匹配判断应基于文件路径、行号、问题描述的综合相似度
- 准确性判断需要结合 diff 上下文和代码逻辑进行分析
- 对于每个 AI 建议，都需要明确给出匹配状态和准确性判断


---
接下来是具体的评测示例上下文，请基于以下信息完成任务：

执行的工作目录： {work_path}
source_commit : {source_commit}
target_commit : {target_commit}
expect_suggestions: {expect_suggestions}
ai_suggestions: {ai_suggestions}
diff_content: {diff_content}
