# 编程语言识别指南

## 概述

本指南提供系统化的编程语言识别方法，通过分析配置文件、文件扩展名、目录结构等特征，准确识别项目使用的编程语言和版本。

## 主要编程语言识别

### Python
- **配置文件**: `requirements.txt`, `setup.py`, `pyproject.toml`, `Pipfile`
- **文件扩展名**: `.py`, `.pyx`, `.pyi`
- **目录结构**: `__init__.py`, `venv/`, `.venv/`
- **版本文件**: `.python-version`, `runtime.txt`
- **框架标志**: `manage.py` (Django), `app.py` (Flask)

### JavaScript/TypeScript
- **配置文件**: `package.json`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`
- **文件扩展名**: `.js`, `.ts`, `.jsx`, `.tsx`, `.mjs`, `.cjs`
- **目录结构**: `node_modules/`
- **TypeScript**: `tsconfig.json`, `.d.ts` 文件
- **版本文件**: `.nvmrc`, `package.json` engines

### Java
- **构建工具**: `pom.xml` (Maven), `build.gradle` (Gradle)
- **文件扩展名**: `.java`, `.class`, `.jar`, `.war`
- **目录结构**: `src/main/java/`, `src/test/java/`, `target/`, `build/`
- **配置文件**: `application.properties`, `application.yml`

### Go
- **配置文件**: `go.mod`, `go.sum`
- **文件扩展名**: `.go`
- **入口文件**: `main.go`
- **目录结构**: `vendor/`, `cmd/`, `pkg/`, `internal/`

### Rust
- **配置文件**: `Cargo.toml`, `Cargo.lock`
- **文件扩展名**: `.rs`
- **入口文件**: `src/main.rs`, `src/lib.rs`
- **目录结构**: `target/`, `src/`

### C#
- **项目文件**: `*.csproj`, `*.sln`, `*.vbproj`
- **文件扩展名**: `.cs`, `.vb`, `.fs`
- **配置文件**: `appsettings.json`, `web.config`
- **目录结构**: `bin/`, `obj/`, `Properties/`

### PHP
- **配置文件**: `composer.json`, `composer.lock`
- **文件扩展名**: `.php`, `.phtml`
- **入口文件**: `index.php`, `app.php`
- **目录结构**: `vendor/`

### Ruby
- **配置文件**: `Gemfile`, `Gemfile.lock`, `*.gemspec`
- **文件扩展名**: `.rb`, `.rake`
- **版本文件**: `.ruby-version`
- **目录结构**: `lib/`, `spec/`, `test/`

### Swift
- **配置文件**: `Package.swift`, `*.xcodeproj`
- **文件扩展名**: `.swift`
- **目录结构**: `Sources/`, `Tests/`

### Kotlin
- **构建文件**: `build.gradle.kts`
- **文件扩展名**: `.kt`, `.kts`
- **目录结构**: `src/main/kotlin/`

## 多语言项目识别

### 混合项目特征
- **前后端分离**: 同时存在 `package.json` 和 `requirements.txt`
- **微服务架构**: 多个子目录包含不同语言的项目文件
- **移动应用**: 同时存在 `android/` (Java/Kotlin) 和 `ios/` (Swift/Objective-C)
- **Monorepo**: `packages/` 或 `apps/` 目录下包含多种语言的项目

### Monorepo 语言识别
- **工作空间配置**: 检查 `package.json` workspaces, `pnpm-workspace.yaml`
- **子项目扫描**: 分析每个子项目的语言和技术栈
- **共享代码**: 识别 `shared/`, `common/`, `libs/` 中的共享语言
- **构建工具**: Nx, Lerna, Turborepo 等工具的配置

### 主次语言判断
1. **代码行数统计**: 使用工具统计各语言代码行数
2. **构建配置**: 主要构建脚本使用的语言
3. **入口文件**: 应用程序主入口文件的语言
4. **依赖关系**: 核心业务逻辑使用的语言
5. **子项目数量**: Monorepo中各语言子项目的数量

## Memory 更新 Key 示例

```
project.stack.languages
project.stack.language_versions
project.stack.language_stats
```

## 识别策略

### 优先级顺序
1. **锁文件**: `package-lock.json`, `Cargo.lock`, `poetry.lock` 等
2. **配置文件**: `package.json`, `pyproject.toml`, `go.mod` 等
3. **文件扩展名**: 统计各类型文件数量
4. **目录结构**: 特定语言的典型目录结构

### 验证方法
1. **多维度确认**: 结合配置文件、文件扩展名、目录结构
2. **版本一致性**: 检查不同配置文件中版本信息的一致性
3. **依赖验证**: 验证依赖项与声明语言版本的兼容性
