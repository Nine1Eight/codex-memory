from agents.no_priors_agent import Effect, NoPriorsAgent


def bare_agent() -> NoPriorsAgent:
    return object.__new__(NoPriorsAgent)


def test_scene_fingerprint_is_stable_and_sensitive() -> None:
    agent = bare_agent()
    first = agent._scene([[0, 0, 0], [0, 2, 0], [0, 0, 0]])
    same = agent._scene([[0, 0, 0], [0, 2, 0], [0, 0, 0]])
    moved = agent._scene([[0, 0, 0], [0, 0, 2], [0, 0, 0]])
    assert first.key == same.key
    assert first.key != moved.key
    assert first.components == ((2, 1, 1, 1, 1, 1),)


def test_effect_prefers_progress_and_penalizes_death() -> None:
    progress = Effect(tries=2, changes=2, progress=1)
    death = Effect(tries=2, changes=2, deaths=1)
    assert progress.value() > death.value()


def test_compact_macro_drops_known_no_effect_actions_and_triples() -> None:
    agent = bare_agent()
    agent.action_priors = {1: Effect(tries=2, changes=2), 2: Effect(tries=3, changes=0)}
    macro = agent._compact_macro([(2, None), (1, None), (1, None), (1, None), (1, None)])
    assert macro == [(1, None), (1, None)]


def test_no_game_specific_identifiers_in_policy_source() -> None:
    import inspect

    source = inspect.getsource(NoPriorsAgent).lower()
    for forbidden in ("ls20", "ft09", "wa30", "tr87", "su15", "ka59"):
        assert forbidden not in source


def test_remote_vlm_endpoint_is_rejected() -> None:
    agent = bare_agent()
    agent.vlm_url = "https://example.com/v1"
    agent.vlm_frames = [[[0]]]
    assert agent._vlm_choose(agent._scene([[0]]), []) is None


def test_json_extraction_handles_fenced_response() -> None:
    agent = bare_agent()
    assert agent._json_object('```json\n{"action":"left"}\n```') == {"action": "left"}
