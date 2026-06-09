from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.deps import get_current_user
from app.models.user import User
from app.services.ai_hub import AIHub

router = APIRouter()


class OrchestrateRequest(BaseModel):
    input: str
    context: dict = {}


@router.post("/orchestrate")
async def orchestrate(data: OrchestrateRequest, _: User = Depends(get_current_user)):
    hub = AIHub()
    return await hub.orchestrate(data.input, data.context)


@router.post("/design/generate-points")
async def design_generate_points(features_text: str, kb_context: str = "", _: User = Depends(get_current_user)):
    from app.services.ai_hub import TestDesignAgent
    agent = TestDesignAgent()
    return await agent.generate_test_points(features_text, kb_context)


@router.post("/healing/fix")
async def healing_fix(log: str, script: str = "", _: User = Depends(get_current_user)):
    from app.services.ai_hub import HealingAgent
    agent = HealingAgent()
    return await agent.heal_script(log, script)
