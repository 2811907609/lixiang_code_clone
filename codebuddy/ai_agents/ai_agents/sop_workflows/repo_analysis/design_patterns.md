# 设计模式识别指南

## 概述

本指南提供系统化的设计模式识别方法，通过分析代码结构、类关系、方法命名等特征，准确识别项目中使用的设计模式。

## 创建型模式 (Creational Patterns)

### 单例模式 (Singleton)
**识别标志**：
- 私有构造函数或 `__new__` 方法控制
- 静态实例变量 `_instance`
- `getInstance()` 方法
- 线程安全机制 (Lock)

### 工厂模式 (Factory)
**识别标志**：
- `create*`, `make*`, `build*` 方法命名
- 工厂类或工厂方法
- 产品接口和具体产品类
- 配置驱动的对象创建

### 建造者模式 (Builder)
**识别标志**：
- 链式方法调用 (Fluent Interface)
- `build()` 或 `create()` 最终构建方法
- 复杂对象的分步构建
- Builder 类和 Director 类

## 结构型模式 (Structural Patterns)

### 适配器模式 (Adapter)
**识别标志**：
- Adapter 类名后缀
- 包装或继承旧接口
- 接口转换逻辑
- 第三方库集成

### 装饰器模式 (Decorator)
**识别标志**：
- `@decorator` 语法 (Python)
- Decorator 类名后缀
- 组件包装和功能增强
- 透明的接口保持

### 外观模式 (Facade)
**识别标志**：
- Facade 类名后缀
- 聚合多个子系统
- 简化复杂操作的统一接口
- 高层接口设计

## 行为型模式 (Behavioral Patterns)

### 观察者模式 (Observer)
**识别标志**：
- Observer/Subject 接口
- `subscribe`, `unsubscribe`, `notify` 方法
- 事件驱动架构
- 回调函数列表

### 策略模式 (Strategy)
**识别标志**：
- Strategy 接口和具体策略类
- Context 类持有策略引用
- 运行时策略切换
- 算法族的封装

### 命令模式 (Command)
**识别标志**：
- Command 接口和具体命令类
- `execute()`, `undo()` 方法
- Invoker 类管理命令
- 命令历史和撤销功能

### 模板方法模式 (Template Method)
**识别标志**：
- 抽象基类定义模板方法
- 抽象方法和钩子方法
- 算法骨架固定，细节可变
- 继承关系和方法重写

## 架构级模式

### Repository 模式
**识别标志**：
- Repository 接口和实现类
- 数据访问抽象
- 领域对象的持久化
- 查询方法的标准化命名

### MVC 模式
**识别标志**：
- Model, View, Controller 目录分离
- 控制器协调模型和视图
- 视图负责展示逻辑
- 模型包含业务逻辑和数据

### 依赖注入模式
**识别标志**：
- 构造函数注入
- 接口依赖而非具体实现
- IoC 容器配置
- 依赖倒置原则应用

## Memory 更新 Key 示例

```
project.patterns.design_patterns
project.patterns.architectural_patterns
project.patterns.quality_assessment
project.patterns.anti_patterns
```

## 识别策略

### 代码分析方法
1. **类名模式**: 识别常见的模式命名约定
2. **方法签名**: 分析方法名和参数模式
3. **继承关系**: 分析类的继承和接口实现
4. **依赖关系**: 分析类之间的依赖和组合关系

### 模式验证
1. **结构验证**: 检查模式的结构是否完整
2. **行为验证**: 验证模式的行为是否符合预期
3. **使用场景**: 分析模式使用是否合适
4. **实现质量**: 评估模式实现的质量

### 反模式识别
- **God Object**: 过于庞大的类
- **Spaghetti Code**: 混乱的代码结构
- **Copy-Paste Programming**: 重复代码
- **Magic Numbers**: 硬编码的数字和字符串
