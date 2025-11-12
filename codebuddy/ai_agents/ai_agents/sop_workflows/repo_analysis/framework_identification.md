# 框架和库识别指南

## 概述

本指南提供系统化的框架和库识别方法，通过分析依赖配置、代码模式、目录结构等特征，准确识别项目使用的框架、库和工具。

## Web 框架识别

### Python Web 框架
- **Django**: `manage.py`, `settings.py`, `urls.py`, Django 依赖
- **Flask**: `app.py`, Flask 依赖, `templates/` 目录
- **FastAPI**: `fastapi` 依赖, `uvicorn`, Pydantic 模型
- **Tornado**: tornado 依赖, 异步处理
- **Pyramid**: pyramid 依赖, 配置文件

### JavaScript/TypeScript Web 框架
- **React**: react 依赖, JSX/TSX 文件, `src/App.js`
- **Vue.js**: vue 依赖, `.vue` 文件, `vue.config.js`
- **Angular**: `angular.json`, `@angular/core` 依赖, `.component.ts`
- **Next.js**: next 依赖, `next.config.js`, `pages/` 目录
- **Express.js**: express 依赖, `app.js`, 中间件模式
- **Nuxt.js**: nuxt 依赖, `nuxt.config.js`
- **Svelte**: svelte 依赖, `.svelte` 文件

### 其他语言 Web 框架
- **Spring Boot**: `@SpringBootApplication`, spring-boot-starter 依赖
- **Ruby on Rails**: `Gemfile` 中的 rails, `config/routes.rb`
- **ASP.NET Core**: `*.csproj` 中的 Microsoft.AspNetCore
- **Laravel**: `composer.json` 中的 laravel/framework
- **Gin**: go.mod 中的 gin-gonic/gin
- **Actix Web**: Cargo.toml 中的 actix-web

## 数据库和ORM识别

### 关系型数据库
- **PostgreSQL**: `psycopg2`, `pg`, `postgresql://` 连接字符串
- **MySQL**: `mysql-connector-python`, `mysql2`, `mysql://` 连接字符串
- **SQLite**: `sqlite3`, `.db/.sqlite` 文件
- **SQL Server**: `mssql`, `tedious`, SQL Server 连接字符串

### NoSQL 数据库
- **MongoDB**: `pymongo`, `mongoose`, `mongodb://` 连接字符串
- **Redis**: `redis`, `ioredis`, `redis://` 连接字符串
- **Elasticsearch**: `elasticsearch`, 搜索和分析
- **Cassandra**: `cassandra-driver`, 分布式数据库

### ORM/ODM 框架
- **SQLAlchemy**: SQLAlchemy 依赖, Python ORM
- **Prisma**: `@prisma/client`, `schema.prisma` 文件
- **TypeORM**: typeorm 依赖, `@Entity()` 装饰器
- **Mongoose**: mongoose 依赖, MongoDB ODM
- **Sequelize**: sequelize 依赖, Node.js ORM
- **Django ORM**: Django 内置 ORM
- **Hibernate**: hibernate-core 依赖, Java ORM

## 前端技术栈识别

### CSS 框架和预处理器
- **Tailwind CSS**: tailwindcss 依赖, `tailwind.config.js`
- **Bootstrap**: bootstrap 依赖, Bootstrap CSS 类名
- **Sass/SCSS**: `.scss/.sass` 文件, sass 依赖
- **Less**: `.less` 文件, less 依赖
- **Styled Components**: styled-components 依赖
- **Emotion**: @emotion 依赖

### 状态管理
- **Redux**: redux 依赖, `store/` 目录, `useSelector/useDispatch`
- **Vuex**: vuex 依赖, Vue 状态管理
- **Pinia**: pinia 依赖, Vue 3 状态管理
- **MobX**: mobx 依赖, 响应式状态管理
- **Zustand**: zustand 依赖, 轻量状态管理

## 测试框架识别

### 多语言测试框架
- **pytest**: pytest 依赖, `conftest.py`, `test_*.py` 文件
- **unittest**: Python 标准库, `unittest.TestCase`
- **Jest**: jest 依赖, `jest.config.js`, `__tests__/` 目录
- **Mocha**: mocha 依赖, `test/` 目录
- **Cypress**: cypress 依赖, `cypress.config.js`, E2E 测试
- **Playwright**: @playwright/test 依赖, 跨浏览器测试
- **JUnit**: junit 依赖, `@Test` 注解
- **RSpec**: rspec gem, `spec/` 目录
- **PHPUnit**: phpunit 依赖, PHP 测试框架

## API 和通信框架

### REST API 框架
- **Django REST Framework**: djangorestframework 依赖, `rest_framework` 配置
- **Express.js API**: express 依赖, RESTful 路由
- **Spring Boot REST**: spring-boot-starter-web 依赖
- **Flask-RESTful**: flask-restful 依赖

### GraphQL 框架
- **Apollo Server**: apollo-server 依赖, `schema.graphql`
- **Graphene**: graphene 依赖, Python GraphQL
- **GraphQL.js**: graphql 依赖, JavaScript GraphQL
- **Hasura**: GraphQL 即服务

### 消息队列和通信
- **RabbitMQ**: pika 依赖, amqplib 依赖
- **Apache Kafka**: kafka-python 依赖, kafkajs 依赖
- **Redis Pub/Sub**: redis 依赖, 发布订阅模式
- **gRPC**: grpcio 依赖, `.proto` 文件

## Memory 更新 Key 示例

```
project.stack.frameworks.web
project.stack.frameworks.database
project.stack.frameworks.testing
project.stack.frameworks.frontend
project.stack.frameworks.api
project.stack.frameworks.messaging
```

## 识别策略

### 依赖分析优先级
1. **锁文件**: 最准确的版本信息
2. **主配置文件**: 声明的依赖和版本约束
3. **代码导入**: 实际使用的框架和库
4. **配置文件**: 框架特定的配置文件

### 版本兼容性检查
- 检查依赖版本之间的兼容性
- 识别过时或不安全的版本
- 分析版本约束的合理性
