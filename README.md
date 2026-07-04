# Private_Education - 家教学习记录系统

将家教课程录音转文字稿，通过 AI 自动处理，生成面向教师、家长、学生的 HTML 汇报。

## 工作流

1. 上课时录音，课后用转写软件将录音转为 TXT（带说话人标记）
2. 将 TXT 放入 `input/学生姓名/` 目录
3. 运行 `python -m src.cli 学生姓名`
4. 在 `output/学生姓名/` 中查看生成的 HTML 汇报

## 前置注释（可选）

在 TXT 文件开头可添加元数据，以 `---` 分隔：

```
科目：数学
备注：学生对称轴概念薄弱，需要加强练习
课后作业：《五三》P42-44 二次函数章节练习
课程类型：新课
---
发言人1
今天我们来讲二次函数...
```

## 配置

1. 复制 `.env.example` 为 `.env`，填入 DeepSeek API Key
2. 为每个学生在 `input/学生姓名/config.json` 中配置基本信息

## 使用

```bash
# 安装依赖
pip install -r requirements.txt

# 处理单个学生的新课程（增量）
python -m src.cli 张三

# 全量重建
python -m src.cli 张三 --rebuild

# 处理所有学生
python -m src.cli --all
```

## 输出结构

```
output/张三/
├── index.html          # 汇总索引页
├── homework.json       # 作业追踪数据
├── 数学/
│   ├── 2026-07-01_教师.html
│   ├── 2026-07-01_家长.html
│   └── 2026-07-01_学生.html
└── 英语/
    └── ...
```
