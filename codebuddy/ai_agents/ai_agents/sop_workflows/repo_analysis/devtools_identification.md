# 开发工具识别指南

## 概述

本指南提供系统化的开发工具识别方法，包括构建工具、CI/CD、代码质量工具、容器化、监控等开发生态系统的各个方面。

## 构建工具识别

### 前端构建工具
- **Webpack**: `webpack.config.js`, `webpack-dev-server` 依赖
- **Vite**: `vite.config.js`, 快速开发服务器
- **Rollup**: `rollup.config.js`, 专注库打包
- **Parcel**: `.parcelrc`, 零配置构建
- **Gulp**: `gulpfile.js`, 任务运行器
- **Grunt**: `Gruntfile.js`, 任务自动化

### 后端构建工具
- **Maven**: `pom.xml`, `mvnw` wrapper, `target/` 目录
- **Gradle**: `build.gradle`, `gradlew` wrapper, `build/` 目录
- **Poetry**: `pyproject.toml`, `poetry.lock`
- **Cargo**: `Cargo.toml`, `Cargo.lock`, `target/` 目录
- **Go Modules**: `go.mod`, `go.sum`
- **Composer**: `composer.json`, `composer.lock`

## CI/CD 工具识别

- **GitHub Actions**: `.github/workflows/` 目录, YAML 工作流文件
- **GitLab CI**: `.gitlab-ci.yml` 配置文件
- **Jenkins**: `Jenkinsfile` 流水线文件, `jenkins/` 目录
- **Travis CI**: `.travis.yml` 配置文件
- **CircleCI**: `.circleci/config.yml` 配置文件
- **Azure DevOps**: `azure-pipelines.yml` 配置文件
- **Bitbucket Pipelines**: `bitbucket-pipelines.yml`

## 代码质量工具识别

### 静态代码分析
- **ESLint**: `.eslintrc.*` 配置文件, `eslint-config-*` 包
- **Prettier**: `.prettierrc.*` 配置文件, `.prettierignore`
- **SonarQube**: `sonar-project.properties` 配置文件
- **Black**: `pyproject.toml` 中的配置
- **flake8**: `.flake8`, `setup.cfg` 配置
- **Pylint**: `.pylintrc` 配置文件
- **RuboCop**: `.rubocop.yml` 配置文件

### 类型检查
- **TypeScript**: `tsconfig.json`, `.ts/.tsx` 文件, `.d.ts` 类型定义
- **mypy**: `mypy.ini`, `pyproject.toml` 配置
- **Flow**: `.flowconfig` 配置文件

## 容器化和部署工具

- **Docker**: `Dockerfile`, `.dockerignore`
- **Docker Compose**: `docker-compose.yml`, 多服务编排
- **Kubernetes**: `k8s/` 目录, `.yaml` 资源定义文件
- **Helm**: `Chart.yaml`, `values.yaml`, `templates/` 目录
- **Terraform**: `*.tf` 文件, 基础设施即代码
- **Ansible**: `playbook.yml`, 配置管理

## 包管理工具识别

### 多语言包管理器
- **npm**: `package-lock.json`, `.npmrc`
- **Yarn**: `yarn.lock`, `.yarnrc.yml`
- **pnpm**: `pnpm-lock.yaml`
- **pip**: `requirements.txt`, `pip.conf`
- **Poetry**: `pyproject.toml`, `poetry.lock`
- **Pipenv**: `Pipfile`, `Pipfile.lock`
- **Composer**: `composer.json`, `composer.lock`
- **Bundler**: `Gemfile`, `Gemfile.lock`
- **NuGet**: `packages.config`, `*.csproj`

### Monorepo 管理工具
- **Lerna**: `lerna.json`, `packages/` 目录, JavaScript/TypeScript
- **Nx**: `nx.json`, `workspace.json`, `apps/` 和 `libs/` 目录
- **Rush**: `rush.json`, `common/` 目录, Microsoft 开发
- **Yarn Workspaces**: `package.json` 中的 `workspaces` 字段
- **pnpm Workspaces**: `pnpm-workspace.yaml`
- **Turborepo**: `turbo.json`, 高性能构建系统
- **Bazel**: `WORKSPACE`, `BUILD` 文件, Google 开发
- **Bit**: `.bitmap`, 组件驱动开发

## 监控和日志工具

### 应用性能监控
- **Prometheus**: `prometheus.yml`, `/metrics` 端点
- **Grafana**: `grafana.ini`, 仪表板配置
- **New Relic**: `newrelic.ini`, APM 代理
- **DataDog**: `datadog.yaml`, DD_* 环境变量
- **Sentry**: 错误监控和性能追踪

### 日志管理
- **ELK Stack**: `logstash.conf`, Elasticsearch 配置
- **Fluentd**: `fluent.conf`, 日志收集配置
- **Winston**: Node.js 日志库
- **Loguru**: Python 日志库

## 安全工具识别

### 依赖安全扫描
- **npm audit**: 内置安全扫描
- **Snyk**: `.snyk` 配置文件
- **OWASP Dependency Check**: CVE 漏洞检测
- **Safety**: Python 依赖安全检查

### 代码安全扫描
- **CodeQL**: GitHub 安全分析
- **Bandit**: `.bandit` Python 安全检查
- **ESLint Security**: JavaScript 安全规则
- **SonarQube**: 综合安全分析

## Memory 更新 Key 示例

```
project.stack.tools.build
project.stack.tools.cicd
project.stack.tools.quality
project.stack.tools.deployment
project.stack.tools.monitoring
project.stack.tools.security
project.stack.tools.monorepo
```
