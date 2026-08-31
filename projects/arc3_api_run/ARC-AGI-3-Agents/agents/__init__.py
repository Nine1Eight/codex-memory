from typing import Type, cast

from dotenv import load_dotenv

from .agent import Agent, Playback
from .recorder import Recorder
from .swarm import Swarm
from .templates.random_agent import Random
from .nine18_world_model_agent import Nine18WorldModel
from .no_priors_agent import NoPriorsAgent

# Some template agents depend on optional third-party packages (for example
# langsmith/langgraph). Keep imports soft so the package can still be used for
# lighter-weight agents and unit tests without those extras installed.
try:
    from .templates.openclaw_agent import OpenClaw
    from .templates.langgraph_functional_agent import LangGraphFunc, LangGraphTextOnly
    from .templates.langgraph_random_agent import LangGraphRandom
    from .templates.langgraph_thinking import LangGraphThinking
    from .templates.llm_agents import LLM, FastLLM, GuidedLLM, ReasoningLLM
    from .templates.multimodal import MultiModalLLM
    from .templates.reasoning_agent import ReasoningAgent
    from .templates.smolagents import SmolCodingAgent, SmolVisionAgent
except ModuleNotFoundError as exc:
    if exc.name not in {"openai", "langsmith", "langgraph", "PIL", "smolagents"}:
        raise

    OpenClaw = None
    LangGraphFunc = LangGraphTextOnly = LangGraphRandom = LangGraphThinking = None
    LLM = FastLLM = GuidedLLM = ReasoningLLM = None
    MultiModalLLM = ReasoningAgent = SmolCodingAgent = SmolVisionAgent = None

load_dotenv()

AVAILABLE_AGENTS: dict[str, Type[Agent]] = {
    cls.__name__.lower(): cast(Type[Agent], cls)
    for cls in Agent.__subclasses__()
    if cls.__name__ != "Playback"
}

# add all the recording files as valid agent names
for rec in Recorder.list():
    AVAILABLE_AGENTS[rec] = Playback

# update the agent dictionary to include subclasses of LLM class
AVAILABLE_AGENTS["reasoningagent"] = ReasoningAgent

__all__ = [
    "Swarm",
    "Random",
    "Nine18WorldModel",
    "NoPriorsAgent",
    "LangGraphFunc",
    "LangGraphTextOnly",
    "LangGraphThinking",
    "LangGraphRandom",
    "LLM",
    "FastLLM",
    "ReasoningLLM",
    "GuidedLLM",
    "ReasoningAgent",
    "SmolCodingAgent",
    "SmolVisionAgent",
    "Agent",
    "Recorder",
    "Playback",
    "AVAILABLE_AGENTS",
    "MultiModalLLM",
    "OpenClaw",
]
