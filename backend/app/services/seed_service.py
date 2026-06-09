"""预置大模型与 Agent 种子数据"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.agent_presets import AGENT_PRESETS, build_agent_config, design_presets
from app.data.model_presets import get_preset_models
from app.models.agent import AgentInstance, AgentTemplate, AgentStatus, AgentType
from app.models.ai_model import AIModelConfig


async def seed_ai_models(db: AsyncSession) -> dict[str, AIModelConfig]:
    """预置常用大模型，Key 来自 .env 可后续在前端单独更新"""
    key_map: dict[str, AIModelConfig] = {}
    for preset in get_preset_models():
        result = await db.execute(
            select(AIModelConfig).where(
                AIModelConfig.provider == preset["provider"],
                AIModelConfig.model_name == preset["model_name"],
            )
        )
        m = result.scalar_one_or_none()
        if not m:
            m = AIModelConfig(
                provider=preset["provider"],
                model_name=preset["model_name"],
                api_endpoint=preset["api_endpoint"],
                api_key_encrypted=preset["api_key"] or None,
                parameters=preset.get("parameters"),
                rate_limit=preset.get("rate_limit", 60),
                is_enabled=True,
            )
            db.add(m)
            await db.flush()
        else:
            if not m.api_endpoint:
                m.api_endpoint = preset["api_endpoint"]
            if not m.api_key_encrypted and preset["api_key"]:
                m.api_key_encrypted = preset["api_key"]
            if not m.parameters:
                m.parameters = preset.get("parameters")
        key_map[f"{preset['provider']}:{preset['model_name']}"] = m
    return key_map


async def _upsert_agent(db: AsyncSession, preset: dict, model_map: dict[str, AIModelConfig]) -> None:
    cfg = build_agent_config(preset)
    model_key = f"{preset['model_provider']}:{preset['model_name']}"
    model = model_map.get(model_key)

    tpl_exists = await db.execute(select(AgentTemplate).where(AgentTemplate.name == preset["name"]))
    if not tpl_exists.scalar_one_or_none():
        db.add(
            AgentTemplate(
                name=preset["name"],
                agent_type=preset["agent_type"],
                description=preset["description"],
                default_prompt=cfg["agent_files"]["prompts"].get("system-prompt.md"),
                default_config=cfg,
            )
        )

    result = await db.execute(
        select(AgentInstance).where(
            AgentInstance.name == preset["name"],
            AgentInstance.project_id.is_(None),
        )
    )
    agent = result.scalar_one_or_none()
    task_prompts = preset.get("task_prompts", {})
    primary_prompt = task_prompts.get("test_points") or task_prompts.get("analyze") or next(iter(task_prompts.values()), None)

    if not agent:
        db.add(
            AgentInstance(
                name=preset["name"],
                agent_type=preset["agent_type"],
                project_id=None,
                model_id=model.id if model else None,
                status=AgentStatus.ENABLED,
                prompt_template=primary_prompt,
                config=cfg,
            )
        )
    else:
        agent.model_id = model.id if model else agent.model_id
        agent.config = cfg
        agent.agent_type = preset["agent_type"]
        if not agent.prompt_template and primary_prompt:
            agent.prompt_template = primary_prompt
        agent.status = AgentStatus.ENABLED


async def seed_agents(db: AsyncSession, model_map: dict[str, AIModelConfig]) -> None:
    for preset in design_presets():
        await _upsert_agent(db, preset, model_map)

    for preset in AGENT_PRESETS:
        await _upsert_agent(db, preset, model_map)

    old = await db.execute(
        select(AgentInstance).where(
            AgentInstance.name == "默认测试设计智能体",
            AgentInstance.project_id.is_(None),
        )
    )
    legacy = old.scalar_one_or_none()
    if legacy:
        await db.delete(legacy)
