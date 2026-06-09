"""Agent 文件结构预置（参考 prompts/memory/tools/workflows/skills/knowledge/configs）"""

from app.models.agent import AgentType


def _base_files(agent_name: str, role: str, tasks: str) -> dict:
    return {
        "prompts": {
            "system-prompt.md": f"""# {agent_name} 系统提示

你是企业级 AI 自动化测试平台的专业智能体。

## 角色
{role}

## 行为边界
- 仅输出任务要求的内容，不编造未提供的事实
- 测试设计需覆盖正常、异常、边界场景
- 输出格式严格遵守 output-format.md
""",
            "task-router.md": f"""# 任务路由

根据用户任务类型选择执行策略：

{tasks}

路由规则：优先使用 skills 中对应技能模板，再结合 knowledge 领域知识。
""",
            "role-config.md": f"""# 角色配置

| 项 | 值 |
|---|---|
| 名称 | {agent_name} |
| 职责 | {role} |
| 协作 | 可调用测试设计、执行、报告模块 |
| 权限 | 只读需求/用例，不直接修改生产数据 |
""",
            "output-format.md": """# 输出格式

- 测试点：JSON 树，节点含 id、name、children
- 用例：JSON 数组，含 name、precondition、steps、expected_result、priority
- 核查报告：JSON，含 score、issues、summary
- 禁止 Markdown 代码块包裹（除非明确要求）
""",
        },
        "memory": {
            "user-profile.md": "# 用户画像\n\n记录项目偏好、常用测试类型、优先级策略（运行时更新）。",
            "session-context.md": "# 会话上下文\n\n当前项目、版本、关联需求文档 ID、选中测试点。",
            "long-term-memory.md": "# 长期记忆\n\n历史缺陷模式、高频失败模块、团队规范摘要。",
            "knowledge-notes.md": "# 知识笔记\n\n项目特有术语、业务流程备忘。",
        },
        "tools": {
            "browser-tool.md": "# 浏览器工具\n\n用于 E2E 场景描述与页面元素推断（不直接执行）。",
            "code-executor.md": "# 代码执行\n\n生成/审查 pytest、Playwright 脚本片段。",
            "api-connectors.md": "# API 连接器\n\n解析 OpenAPI/接口文档，生成接口测试用例。",
            "search-tool.md": "# 检索工具\n\n检索知识库 RAG 片段与历史用例。",
        },
        "workflows": {
            "plan-execute.md": """# 计划-执行工作流

1. 解析需求文档
2. 提取功能模块
3. 生成测试点树
4. 用户确认后生成用例
5. 可选：关联测试计划
""",
            "rag-pipeline.md": """# RAG 流水线

1. 检索 knowledge 与需求文档片段
2. 重排序 Top-K
3. 注入 prompts 上下文
4. 生成结构化输出
""",
            "multi-agent.md": "# 多智能体协作\n\n设计 Agent → 核查 Agent → 执行 Agent 串联。",
            "evaluation-loop.md": "# 评估闭环\n\n生成 → 核查评分 → 低于阈值则重写。",
        },
        "skills": {
            "writing.md": "# 写作技能\n\n清晰、可执行、无歧义的测试步骤描述。",
            "coding.md": "# 编码技能\n\n生成可运行的自动化脚本骨架。",
            "analysis.md": "# 分析技能\n\n风险分析、缺陷模式识别、覆盖度评估。",
            "design.md": "# 设计技能\n\n等价类、边界值、场景法设计测试点与用例。",
        },
        "knowledge": {
            "domain-faq.md": "# 领域 FAQ\n\n测试平台常见操作与规范问答。",
            "product-docs.md": "# 产品文档\n\n被测系统功能说明（由需求文档同步）。",
            "policy-rules.md": "# 策略规则\n\n用例优先级定义、通过/失败判定标准。",
            "glossary.md": "# 术语表\n\n测试点、用例、计划、执行等领域术语。",
        },
        "configs": {
            "model-settings.yaml": "temperature: 0.7\ntop_p: 0.9\nmax_tokens: 4096\n",
            "tool-permissions.yaml": "browser: read\ncode_executor: suggest\napi: read\nsearch: read\n",
            "env.example": "# API Key 在 AI 模型管理中单独配置\n",
            "agent-profile.json": '{"version":"1.0","locale":"zh-CN"}',
        },
        "README.md": f"# {agent_name}\n\n企业级测试智能体，配置见各子目录 Markdown 文件。",
        "agent-index.md": f"""# {agent_name} 索引

- prompts/ 提示词与输出规范
- memory/ 记忆模块
- tools/ 工具说明
- workflows/ 工作流
- skills/ 技能包
- knowledge/ 知识库
- configs/ 运行参数
""",
    }


DESIGN_AGENT_VARIANTS: list[dict] = [
    {
        "name": "测试设计智能体",
        "model_provider": "qwen",
        "model_name": "qwen-plus",
        "description_suffix": "（通义千问 Plus）",
    },
    {
        "name": "测试设计·GPT-4o",
        "model_provider": "openai",
        "model_name": "gpt-4o",
        "description_suffix": "（OpenAI GPT-4o）",
    },
    {
        "name": "测试设计·DeepSeek",
        "model_provider": "deepseek",
        "model_name": "deepseek-chat",
        "description_suffix": "（DeepSeek Chat）",
    },
]

_DESIGN_BASE = {
    "agent_type": AgentType.DESIGN,
    "description": "根据需求文档与知识库生成测试点树、用例，并支持用例核查",
    "extra_role": "测试分析与用例设计专家，负责测试点树与结构化用例生成。",
    "tasks": "- test_points：生成测试点树\n- test_cases：生成用例\n- verify_cases：核查用例",
    "task_prompts": {
        "test_points": """你是测试设计智能体。结合需求文档、功能列表与知识库参考，生成测试点树 JSON。
节点：id、name、children。覆盖正常/异常/边界。仅返回 JSON。

{input}""",
        "test_cases": """根据测试点生成用例 JSON 数组。
字段：name、precondition、steps、expected_result、priority、test_types

测试点：{test_point}
需求：{requirements}
仅返回 JSON。""",
        "verify_cases": """核查用例质量，返回 JSON：score、issues、summary

{cases}""",
    },
}

def design_presets() -> list[dict]:
    """同类型多模型：测试设计 Agent 变体"""
    presets = []
    for v in DESIGN_AGENT_VARIANTS:
        p = {**_DESIGN_BASE, **v}
        p["description"] = _DESIGN_BASE["description"] + v.get("description_suffix", "")
        presets.append(p)
    return presets


AGENT_PRESETS: list[dict] = [
    {
        "name": "代码分析智能体",
        "agent_type": AgentType.CODE_ANALYSIS,
        "model_provider": "deepseek",
        "model_name": "deepseek-chat",
        "description": "分析代码仓库，生成接口/单元测试建议与脚本",
        "task_prompts": {
            "analyze": "分析以下代码并给出测试建议 JSON：files、risks、suggested_cases\n\n{input}",
        },
        "extra_role": "代码静态分析与测试脚本生成专家。",
        "tasks": "- analyze：代码风险与用例建议",
    },
    {
        "name": "自愈修复智能体",
        "agent_type": AgentType.HEALING,
        "model_provider": "openai",
        "model_name": "gpt-4o-mini",
        "description": "根据失败日志分析根因并给出修复脚本",
        "task_prompts": {
            "heal": "分析失败日志，返回 JSON：root_cause、fixed_script、confidence\n\n日志：{log}\n脚本：{script}",
        },
        "extra_role": "执行失败诊断与脚本自愈专家。",
        "tasks": "- heal：失败根因与修复建议",
    },
    {
        "name": "缺陷预测智能体",
        "agent_type": AgentType.DEFECT_PREDICTION,
        "model_provider": "qwen",
        "model_name": "qwen-turbo",
        "description": "基于历史与变更预测高风险缺陷区域",
        "task_prompts": {
            "predict": "根据变更与历史数据预测缺陷风险 JSON：hotspots、score、reason\n\n{input}",
        },
        "extra_role": "质量风险与缺陷热点预测专家。",
        "tasks": "- predict：缺陷热点预测",
    },
]


def build_agent_config(preset: dict) -> dict:
    files = _base_files(preset["name"], preset["extra_role"], preset["tasks"])
    files["prompts"]["task-prompts.json"] = preset.get("task_prompts", {})
    return {
        "agent_files": files,
        "description": preset.get("description", ""),
        "version": "1.0",
    }
