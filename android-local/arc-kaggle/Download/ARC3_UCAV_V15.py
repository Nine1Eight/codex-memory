# === ARC3 v15 — UNIFIED CAUSAL ACTION-VALUE PLANNER (UCAV) ===
import heapq as _v15_heapq
import math as _v15_math
import re as _v15_re
from collections import Counter as _V15Counter, defaultdict as _V15DefaultDict
from dataclasses import dataclass as _v15_dataclass, field as _v15_field
from pathlib import Path as _V15Path

ARC3_V15_POLICY_LOG = WORKING_DIR / "ucav_v15_policy_events.jsonl"
try:
    ARC3_V15_POLICY_LOG.unlink(missing_ok=True)
except Exception as _v15_exc:
    raise RuntimeError(f"Failed to clear stale UCAV v15 log: {_v15_exc}") from _v15_exc


@_v15_dataclass
class _V15ActionEvidence:
    uses: int = 0
    successes: int = 0
    no_impact: int = 0
    loops: int = 0
    progress_sum: float = 0.0
    score_gain: float = 0.0
    reward_gain: float = 0.0
    level_gain: int = 0
    last_move: int = 0
    next_states: _V15Counter = _v15_field(default_factory=_V15Counter)


@_v15_dataclass
class _V15GamePolicyState:
    game_id: str
    current_state: str = "unknown"
    current_level: int = 0
    move: int = 0
    state_actions: dict = _v15_field(default_factory=dict)
    global_actions: dict = _v15_field(default_factory=dict)
    predecessors: dict = _v15_field(default_factory=lambda: _V15DefaultDict(list))
    success_states: set = _v15_field(default_factory=set)
    state_visits: _V15Counter = _v15_field(default_factory=_V15Counter)
    recent_state_actions: list = _v15_field(default_factory=list)


class UnifiedCausalActionValuePlanner:
    """Current-game-only action prior over legal ARC-AGI-3 actions.

    UCAV does not step, clone, reset, or inspect hidden state. It converts the
    already-audited PRE/POST stream into a compact numeric prior that ranks
    legal actions by expected progress, information value, ReversePath bridge
    value, loop/no-impact risk, and state-local exhaustion.
    """

    MODE_WEIGHTS = {
        "HARD_EXPLOIT": dict(success=4.20, progress=2.80, change=0.90, info=0.20, reverse=3.00, structured=2.20, risk=3.40, repeat=2.40, exhaust=5.00),
        "EXPLOIT": dict(success=3.50, progress=2.35, change=0.90, info=0.45, reverse=2.50, structured=2.00, risk=3.00, repeat=2.10, exhaust=4.70),
        "EXPLOIT_PROTECTED": dict(success=3.70, progress=2.55, change=0.85, info=0.35, reverse=2.65, structured=2.10, risk=3.10, repeat=2.20, exhaust=4.80),
        "CAUTIOUS_EXPLOIT": dict(success=2.90, progress=2.00, change=1.00, info=0.75, reverse=2.10, structured=1.75, risk=2.75, repeat=2.00, exhaust=4.50),
        "BALANCED": dict(success=2.35, progress=1.65, change=1.10, info=1.20, reverse=1.75, structured=1.50, risk=2.55, repeat=2.10, exhaust=4.40),
        "EXPLORE": dict(success=1.35, progress=1.00, change=1.25, info=2.45, reverse=1.00, structured=0.90, risk=2.20, repeat=2.35, exhaust=4.80),
        "CHANGE_POLICY": dict(success=1.55, progress=1.10, change=1.35, info=2.75, reverse=1.25, structured=1.10, risk=3.25, repeat=3.10, exhaust=6.00),
        "TERMINAL": dict(success=0.0, progress=0.0, change=0.0, info=0.0, reverse=0.0, structured=0.0, risk=0.0, repeat=0.0, exhaust=0.0),
    }

    def __init__(self, log_path=None):
        self._states = {}
        self._lock = threading.RLock()
        self._log_path = _V15Path(log_path) if log_path is not None else None

    @staticmethod
    def _normalize_action(action):
        if action is None:
            return "UNKNOWN"
        if isinstance(action, Mapping):
            for key in ("action_name", "action", "name", "type"):
                if key in action and action[key] is not None:
                    return UnifiedCausalActionValuePlanner._normalize_action(action[key])
        name = getattr(action, "name", None)
        if name is not None and not isinstance(action, str):
            text = str(name)
        else:
            text = str(action)
        text = " ".join(text.strip().split())
        upper = text.upper()
        match = _v15_re.search(r"\bACTION[\s_.:-]*(\d+)\b", upper)
        if match:
            return f"ACTION{int(match.group(1))}"
        for token in ("UP", "DOWN", "LEFT", "RIGHT", "UNDO", "CLICK", "SELECT", "RESET"):
            if _v15_re.search(rf"\b{token}\b", upper):
                return token
        return upper[:120] if upper else "UNKNOWN"

    @classmethod
    def _legal_actions(cls, valid_actions):
        if valid_actions is None:
            return []
        values = []
        if isinstance(valid_actions, Mapping):
            bool_map = valid_actions and all(isinstance(v, bool) for v in valid_actions.values())
            values = [k for k, v in valid_actions.items() if (v if bool_map else True)]
        elif isinstance(valid_actions, (str, bytes)):
            values = [valid_actions]
        else:
            try:
                values = list(valid_actions)
            except Exception:
                values = [valid_actions]
        ordered = []
        seen = set()
        for value in values:
            normalized = cls._normalize_action(value)
            if normalized == "UNKNOWN" or normalized in seen:
                continue
            seen.add(normalized)
            ordered.append(normalized)
        return ordered

    @staticmethod
    def _context_state(signature, level):
        return f"L{int(level or 0)}:{signature or 'unknown'}"

    def state(self, game_id):
        key = str(game_id or "unknown")
        with self._lock:
            if key not in self._states:
                self._states[key] = _V15GamePolicyState(game_id=key)
            return self._states[key]

    @staticmethod
    def _evidence_copy(evidence):
        if evidence is None:
            return _V15ActionEvidence()
        return evidence

    @staticmethod
    def _merge_evidence(local, global_ev):
        if local is None and global_ev is None:
            return _V15ActionEvidence()
        if local is None:
            # Global evidence is deliberately discounted: same-game transfer is
            # useful but must not overpower state-local contradictions.
            return _V15ActionEvidence(
                uses=int(round(global_ev.uses * 0.35)),
                successes=int(round(global_ev.successes * 0.35)),
                no_impact=int(round(global_ev.no_impact * 0.35)),
                loops=int(round(global_ev.loops * 0.35)),
                progress_sum=float(global_ev.progress_sum) * 0.35,
                score_gain=float(global_ev.score_gain) * 0.35,
                reward_gain=float(global_ev.reward_gain) * 0.35,
                level_gain=int(round(global_ev.level_gain * 0.35)),
                last_move=int(global_ev.last_move),
                next_states=_V15Counter(),
            )
        if global_ev is None or global_ev is local:
            return local
        return _V15ActionEvidence(
            uses=local.uses + int(round(global_ev.uses * 0.15)),
            successes=local.successes + int(round(global_ev.successes * 0.15)),
            no_impact=local.no_impact + int(round(global_ev.no_impact * 0.15)),
            loops=local.loops + int(round(global_ev.loops * 0.15)),
            progress_sum=local.progress_sum + float(global_ev.progress_sum) * 0.15,
            score_gain=local.score_gain + float(global_ev.score_gain) * 0.15,
            reward_gain=local.reward_gain + float(global_ev.reward_gain) * 0.15,
            level_gain=local.level_gain + int(round(global_ev.level_gain * 0.15)),
            last_move=max(local.last_move, global_ev.last_move),
            next_states=_V15Counter(local.next_states),
        )

    def observe(self, game_id, action, before, after, event):
        with self._lock:
            st = self.state(game_id)
            action_key = self._normalize_action(action)
            move = int(event.get("move", st.move + 1) or (st.move + 1))
            before_level = int(before.get("levels", st.current_level) or st.current_level or 0)
            after_level = int(after.get("levels", before_level) or before_level)
            before_sig = before.get("signature") or before.get("core_signature") or "unknown-before"
            after_sig = after.get("signature") or after.get("core_signature") or "unknown-after"
            before_state = self._context_state(before_sig, before_level)
            after_state = self._context_state(after_sig, after_level)

            local_key = (before_state, action_key)
            local = st.state_actions.setdefault(local_key, _V15ActionEvidence())
            global_ev = st.global_actions.setdefault(action_key, _V15ActionEvidence())
            success = bool(
                int(event.get("level_delta", 0) or 0) > 0
                or float(event.get("score_delta", 0.0) or 0.0) > 0.0
                or float(event.get("reward", 0.0) or 0.0) > 0.0
            )
            no_impact = bool(event.get("no_impact"))
            loop = bool(event.get("loop_signal")) or before_state == after_state
            progress = float(event.get("progress_value", 0.0) or 0.0)
            score_gain = max(0.0, float(event.get("score_delta", 0.0) or 0.0))
            reward_gain = max(0.0, float(event.get("reward", 0.0) or 0.0))
            level_gain = max(0, int(event.get("level_delta", 0) or 0))

            for target in (local, global_ev):
                target.uses += 1
                target.successes += int(success)
                target.no_impact += int(no_impact)
                target.loops += int(loop)
                target.progress_sum += progress
                target.score_gain += score_gain
                target.reward_gain += reward_gain
                target.level_gain += level_gain
                target.last_move = move
            local.next_states[after_state] += 1

            edge = (before_state, action_key)
            if edge not in st.predecessors[after_state]:
                st.predecessors[after_state].append(edge)
                st.predecessors[after_state] = st.predecessors[after_state][-128:]
            if success:
                st.success_states.add(after_state)

            st.move = max(st.move, move)
            st.current_level = after_level
            st.current_state = after_state
            st.state_visits[after_state] += 1
            st.recent_state_actions.append((move, before_state, action_key, after_state, success, no_impact, loop))
            st.recent_state_actions = st.recent_state_actions[-32:]

    @staticmethod
    def _entropy(counter):
        total = sum(counter.values())
        if total <= 0 or len(counter) <= 1:
            return 0.0
        entropy = 0.0
        for count in counter.values():
            p = count / total
            entropy -= p * _v15_math.log(max(p, 1e-12))
        return entropy / _v15_math.log(len(counter))

    def _edge_cost(self, st, before_state, action):
        ev = st.state_actions.get((before_state, action)) or st.global_actions.get(action)
        if ev is None or ev.uses <= 0:
            return 1.75
        uses = max(ev.uses, 1)
        success_rate = ev.successes / uses
        noimpact_rate = ev.no_impact / uses
        loop_rate = ev.loops / uses
        progress_mean = max(-1.0, min(1.0, ev.progress_sum / uses))
        return max(0.10, 1.0 + 1.8 * noimpact_rate + 1.4 * loop_rate - 0.8 * success_rate - 0.35 * max(0.0, progress_mean))

    def _reverse_path(self, st, current_state, max_depth=10):
        if not current_state or not st.success_states:
            return {"first_action": None, "actions": [], "cost": None, "depth": 0}
        queue = []
        best = {}
        for target in sorted(st.success_states):
            _v15_heapq.heappush(queue, (0.0, 0, target, []))
            best[target] = 0.0
        while queue:
            cost, depth, node, reverse_steps = _v15_heapq.heappop(queue)
            if cost > best.get(node, float("inf")) + 1e-12:
                continue
            if depth >= max_depth:
                continue
            for previous, action in st.predecessors.get(node, ()): 
                edge_cost = self._edge_cost(st, previous, action)
                new_cost = cost + edge_cost
                path = [(action, node)] + reverse_steps
                if previous == current_state:
                    actions = [step[0] for step in path]
                    return {
                        "first_action": actions[0] if actions else None,
                        "actions": actions,
                        "cost": round(new_cost, 6),
                        "depth": len(actions),
                    }
                if new_cost + 1e-12 < best.get(previous, float("inf")):
                    best[previous] = new_cost
                    _v15_heapq.heappush(queue, (new_cost, depth + 1, previous, path))
        return {"first_action": None, "actions": [], "cost": None, "depth": 0}


    @staticmethod
    def _game_key(game_id):
        try:
            if "_dwe_game_key" in globals():
                return str(_dwe_game_key(game_id))
        except Exception:
            pass
        text = str(game_id or "unknown").strip()
        return text.split("-", 1)[0] if text else "unknown"

    def _structured_prior(self, st, action):
        """Fuse V14 DifferenceRule + TrajectoryRule evidence without crossing games."""
        core = globals().get("SOTA_LEARNING_CORE")
        if core is None:
            return {"value": 0.0, "difference": 0.0, "trajectory": 0.0, "status": "none"}
        game_key = self._game_key(st.game_id)
        visual_signature = st.current_state.split(":", 1)[1] if ":" in st.current_state else st.current_state
        mapped_signature = globals().get("SOTA_SIGNATURE_BRIDGE", {}).get((game_key, visual_signature))
        try:
            with core._lock:
                action_rules = [
                    rule for rule in core.rules.values()
                    if str(rule.game_key) == game_key and self._normalize_action(rule.action) == action
                ]
                exact_rules = [
                    rule for rule in action_rules
                    if mapped_signature and str(rule.before_signature) == str(mapped_signature)
                ]
                selected_rules = exact_rules or action_rules
                locality = 1.0 if exact_rules else 0.35

                trajectories = [
                    rule for rule in core.trajectories.values()
                    if str(rule.game_key) == game_key
                    and getattr(rule, "actions", ())
                    and self._normalize_action(rule.actions[0]) == action
                ]
                exact_traj = [
                    rule for rule in trajectories
                    if str(getattr(rule, "start_signature", "")) == str(visual_signature)
                ]
                selected_traj = exact_traj or trajectories
                traj_locality = 1.0 if exact_traj else 0.30
        except Exception:
            return {"value": 0.0, "difference": 0.0, "trajectory": 0.0, "status": "unavailable"}

        wins = sum(int(getattr(r, "wins", 0) or 0) for r in selected_rules)
        losses = sum(int(getattr(r, "losses", 0) or 0) for r in selected_rules)
        score_gain = sum(float(getattr(r, "score_gain", 0.0) or 0.0) for r in selected_rules)
        support = wins + losses + sum(int(getattr(r, "neutral", 0) or 0) for r in selected_rules)
        if selected_rules:
            p = (wins + 1.0) / (wins + losses + 2.0)
            directional = 2.0 * (p - 0.5)
            score_term = max(-1.0, min(1.0, score_gain))
            difference_value = locality * (1.25 * directional + 0.45 * score_term + 0.08 * min(support, 6))
            if losses >= 2 and p <= 0.30:
                difference_value -= 1.50 * locality
            elif wins >= 2 and p >= 0.70:
                difference_value += 1.00 * locality
        else:
            difference_value = 0.0

        tw = sum(int(getattr(r, "wins", 0) or 0) for r in selected_traj)
        tl = sum(int(getattr(r, "losses", 0) or 0) for r in selected_traj)
        tscore = sum(float(getattr(r, "total_score_delta", 0.0) or 0.0) for r in selected_traj)
        if selected_traj:
            tp = (tw + 1.0) / (tw + tl + 2.0)
            trajectory_value = traj_locality * (1.10 * (2.0 * (tp - 0.5)) + 0.35 * max(-1.0, min(1.0, tscore)))
            if tw >= 1 and tp >= 0.60:
                trajectory_value += 0.75 * traj_locality
            if tl >= 2 and tp <= 0.35:
                trajectory_value -= 1.00 * traj_locality
        else:
            trajectory_value = 0.0

        value = max(-3.0, min(3.0, difference_value + trajectory_value))
        status = (
            "exact" if (exact_rules or exact_traj) else
            "game_global" if (selected_rules or selected_traj) else
            "none"
        )
        return {
            "value": round(value, 6),
            "difference": round(difference_value, 6),
            "trajectory": round(trajectory_value, 6),
            "status": status,
            "mapped_signature": mapped_signature,
        }

    def _score_action(self, st, current_state, action, mode, reverse_first, total_state_uses):
        local = st.state_actions.get((current_state, action))
        global_ev = st.global_actions.get(action)
        ev = self._merge_evidence(local, global_ev)
        uses = max(int(ev.uses), 0)
        successes = max(int(ev.successes), 0)
        no_impact = max(int(ev.no_impact), 0)
        loops = max(int(ev.loops), 0)

        # Conservative priors: untried actions are not presumed successful, but
        # receive an exploration bonus when the current policy is uncertain.
        p_success = (successes + 0.20) / (uses + 1.00)
        p_noimpact = (no_impact + 0.10) / (uses + 1.00)
        p_loop = (loops + 0.10) / (uses + 1.00)
        progress_mean = max(-1.0, min(1.0, ev.progress_sum / uses)) if uses else 0.0
        local_next = local.next_states if local is not None else _V15Counter()
        same_count = int(local_next.get(current_state, 0))
        p_change = 1.0 - (same_count / max(sum(local_next.values()), 1)) if local_next else 0.50
        transition_entropy = self._entropy(local_next)
        ucb = _v15_math.sqrt(_v15_math.log(total_state_uses + 2.0) / (uses + 1.0))
        info_value = min(2.0, ucb + 0.55 * transition_entropy)

        recent_hits = sum(1 for row in st.recent_state_actions[-6:] if row[1] == current_state and row[2] == action)
        repeat_penalty = min(1.0, recent_hits / 2.0)
        negative_rate = (no_impact + loops) / max(uses, 1) if uses else 0.0
        exhausted = bool(uses >= 2 and successes == 0 and (negative_rate >= 0.66 or progress_mean <= -0.10))
        reverse_bonus = 1.0 if reverse_first and action == reverse_first else 0.0
        risk = min(1.5, p_noimpact + 0.85 * p_loop)
        structured = self._structured_prior(st, action)

        weights = self.MODE_WEIGHTS.get(mode, self.MODE_WEIGHTS["BALANCED"])
        q = (
            weights["success"] * p_success
            + weights["progress"] * progress_mean
            + weights["change"] * p_change
            + weights["info"] * info_value
            + weights["reverse"] * reverse_bonus
            + weights["structured"] * structured["value"]
            - weights["risk"] * risk
            - weights["repeat"] * repeat_penalty
            - weights["exhaust"] * float(exhausted)
        )
        probe_value = (
            1.50 * info_value
            + 0.85 * p_change
            + 0.45 * p_success
            - 1.55 * p_noimpact
            - 1.20 * p_loop
            - 1.25 * repeat_penalty
            - 2.00 * float(exhausted)
        )
        exploit_value = (
            2.80 * p_success
            + 1.80 * progress_mean
            + 1.45 * reverse_bonus
            + 0.85 * structured["value"]
            + 0.55 * p_change
            - 1.70 * p_noimpact
            - 1.35 * p_loop
            - 1.10 * repeat_penalty
            - 2.50 * float(exhausted)
        )
        return {
            "action": action,
            "q": round(q, 6),
            "exploit_value": round(exploit_value, 6),
            "probe_value": round(probe_value, 6),
            "uses": uses,
            "p_success": round(p_success, 4),
            "p_change": round(p_change, 4),
            "info": round(info_value, 4),
            "p_noimpact": round(p_noimpact, 4),
            "p_loop": round(p_loop, 4),
            "progress_mean": round(progress_mean, 4),
            "reverse": bool(reverse_bonus),
            "structured": structured["value"],
            "structured_status": structured["status"],
            "difference_prior": structured["difference"],
            "trajectory_prior": structured["trajectory"],
            "recent_repeat": round(repeat_penalty, 4),
            "exhausted": exhausted,
        }

    def rank(self, game_id, valid_actions, mode=None):
        with self._lock:
            st = self.state(game_id)
            legal = self._legal_actions(valid_actions)
            if mode is None:
                try:
                    mode = str(DWE_ALLOCATOR.state(game_id).decision or "BALANCED")
                except Exception:
                    mode = "BALANCED"
            if not legal:
                return {
                    "game_id": st.game_id,
                    "move": st.move + 1,
                    "mode": mode,
                    "state": st.current_state,
                    "legal_actions": [],
                    "ranked": [],
                    "exploit_candidate": None,
                    "explore_candidate": None,
                    "reverse_path": self._reverse_path(st, st.current_state),
                    "confidence": 0.0,
                    "reason": "valid action set unavailable; UCAV refuses to invent legality",
                }
            total_state_uses = sum(
                ev.uses for (state_key, _), ev in st.state_actions.items() if state_key == st.current_state
            )
            reverse = self._reverse_path(st, st.current_state)
            scored = [
                self._score_action(st, st.current_state, action, mode, reverse.get("first_action"), total_state_uses)
                for action in legal
            ]
            scored.sort(key=lambda row: (-row["q"], row["exhausted"], row["uses"], row["action"]))

            non_exhausted = [row for row in scored if not row["exhausted"]] or scored
            exploit = max(non_exhausted, key=lambda row: (row["exploit_value"], row["q"], -row["uses"], row["action"]))
            explore_pool = [row for row in non_exhausted if row["action"] != exploit["action"]] or non_exhausted
            explore = max(explore_pool, key=lambda row: (row["probe_value"], row["info"], -row["uses"], row["action"]))

            margin = scored[0]["q"] - scored[1]["q"] if len(scored) > 1 else abs(scored[0]["q"])
            confidence = 1.0 - _v15_math.exp(-max(0.0, margin))
            return {
                "game_id": st.game_id,
                "move": st.move + 1,
                "mode": mode,
                "state": st.current_state,
                "legal_actions": legal,
                "ranked": scored,
                "exploit_candidate": exploit["action"] if exploit else None,
                "explore_candidate": explore["action"] if explore else None,
                "reverse_path": reverse,
                "confidence": round(confidence, 4),
                "reason": "current-game posterior + information value + weighted ReversePath + exhaustion control",
            }

    def prompt(self, game_id, valid_actions):
        result = self.rank(game_id, valid_actions)
        if not result["ranked"]:
            return (
                "UCAV_V15_ACTION_PRIOR:\n"
                f"STEP={result['move']} MODE={result['mode']} STATE={result['state']}\n"
                "RANKED_LEGAL=unavailable\n"
                "RULE=Do not infer an action is legal from memory; obey the environment-provided valid action set."
            )
        rows = []
        for index, row in enumerate(result["ranked"][:7], 1):
            rows.append(
                f"{index}:{row['action']} q={row['q']:+.3f} exploit={row['exploit_value']:+.3f} "
                f"probe={row['probe_value']:+.3f} use={row['uses']} ps={row['p_success']:.2f} "
                f"chg={row['p_change']:.2f} info={row['info']:.2f} noop={row['p_noimpact']:.2f} "
                f"loop={row['p_loop']:.2f} reverse={int(row['reverse'])} struct={row['structured']:+.2f}/{row['structured_status']} exhausted={int(row['exhausted'])}"
            )
        reverse = result["reverse_path"]
        return (
            "UCAV_V15_ACTION_PRIOR:\n"
            f"STEP={result['move']} MODE={result['mode']} STATE={result['state']} CONF={result['confidence']:.3f}\n"
            f"REVERSEPATH_FIRST={reverse.get('first_action') or 'none'} DEPTH={reverse.get('depth', 0)} COST={reverse.get('cost')}\n"
            "RANKED_LEGAL=" + " | ".join(rows) + "\n"
            f"A_EXPLOIT_PRIOR={result['exploit_candidate']}\n"
            f"B_EXPLORE_PRIOR={result['explore_candidate']}\n"
            "RULE=Build A/B only from currently legal actions. Prefer A when verified causal value dominates; "
            "prefer B when uncertainty is valuable or the current strategy is stalled. Never repeat an exhausted "
            "state-action pair unless every legal alternative is exhausted or new frame-local evidence changes the hypothesis."
        )

    def log_pre(self, game_id, valid_actions):
        result = self.rank(game_id, valid_actions)
        if self._log_path is not None:
            payload = {"schema": "arc3.ucav.pre.v15", **result}
            _cm_write_jsonl(self._log_path, payload)
        return result


UNIFIED_CAUSAL_ACTION_VALUE = UnifiedCausalActionValuePlanner(ARC3_V15_POLICY_LOG)

# V14 used two state-signature spaces: a 16-hex visual SHA1 for GhostBridge and
# a stable RDL hash for DifferenceRule evidence. Bridge them after each audited
# transition, then make DifferenceRule guidance fall back to game-local evidence
# rather than silently disappearing on a signature mismatch.
SOTA_SIGNATURE_BRIDGE = {}
_V15_BASE_SOTA_GUIDANCE = SOTA_LEARNING_CORE.guidance if "SOTA_LEARNING_CORE" in globals() else None


def _v15_sota_guidance(game_id, before_signature=None):
    if _V15_BASE_SOTA_GUIDANCE is None:
        return "SOTA learning core not initialized"
    game_key = UnifiedCausalActionValuePlanner._game_key(game_id)
    candidates = []
    if before_signature is not None:
        mapped = SOTA_SIGNATURE_BRIDGE.get((game_key, str(before_signature)))
        if mapped:
            candidates.append(mapped)
        candidates.append(before_signature)
    candidates.append(None)
    seen = set()
    last = "no run-local DifferenceRule/TrajectoryRule yet"
    for signature in candidates:
        marker = str(signature)
        if marker in seen:
            continue
        seen.add(marker)
        text = _V15_BASE_SOTA_GUIDANCE(game_id, signature)
        last = text
        if not str(text).startswith("no run-local"):
            if signature is None and before_signature is not None:
                return text + "; scope=game-local-fallback"
            if signature != before_signature and signature is not None:
                return text + "; scope=signature-bridge"
            return text
    return last


if "SOTA_LEARNING_CORE" in globals():
    SOTA_LEARNING_CORE.guidance = _v15_sota_guidance

# Wrap the final observational DWE POST (installed by the previous cell). This is
# still one observation of one already-committed action; it does not add an
# environment step or weaken the v4 exactly-once action boundary.
_V15_BASE_OBSERVATIONAL_POST = DWE_ALLOCATOR.post


def _v15_observational_post(self, game_id, action, before, after):
    event = _V15_BASE_OBSERVATIONAL_POST(game_id, action, before, after)
    game_key = UnifiedCausalActionValuePlanner._game_key(game_id)
    visual_before = str(before.get("signature") or before.get("core_signature") or "")
    rdl_before = str(event.get("rdl_before_hash") or "")
    if visual_before and rdl_before:
        SOTA_SIGNATURE_BRIDGE[(game_key, visual_before)] = rdl_before
    UNIFIED_CAUSAL_ACTION_VALUE.observe(game_id, action, before, after, event)
    return event


try:
    DWE_ALLOCATOR.post = _rdl_types.MethodType(_v15_observational_post, DWE_ALLOCATOR)
except Exception:
    import types as _v15_types
    DWE_ALLOCATOR.post = _v15_types.MethodType(_v15_observational_post, DWE_ALLOCATOR)

# Inject the numeric action prior after the existing causal-memory + GhostBridge
# prompt. The LLM still makes the final legal action choice, but it no longer has
# to re-estimate state-action value from prose on every move.
_V15_BASE_BUILD_USER_PROMPT = GhostBridgePreMoveADLToolAgent._build_user_prompt


def _v15_build_user_prompt(
    self,
    action_num: int,
    *,
    valid_actions=None,
    current_frame=None,
    history_entries=None,
    previous_step_summary=None,
):
    base = _V15_BASE_BUILD_USER_PROMPT(
        self,
        action_num,
        valid_actions=valid_actions,
        current_frame=current_frame,
        history_entries=history_entries,
        previous_step_summary=previous_step_summary,
    )
    game_id = self._ghostbridge_premove_game_id
    prior = UNIFIED_CAUSAL_ACTION_VALUE.prompt(game_id, valid_actions)
    pre = UNIFIED_CAUSAL_ACTION_VALUE.log_pre(game_id, valid_actions)
    return (
        base
        + "\n\n"
        + prior
        + "\n\nUCAV_SELECTION_CONTRACT: Candidate A should be the best verified low-risk exploitation action "
        "and candidate B the best non-exhausted information action unless current-frame evidence justifies a different legal pair. "
        "When CHANGE_POLICY is active, diversity and information value outrank repeating the locally best exhausted action. "
        f"The current numeric prior confidence is {pre['confidence']:.3f}; treat low confidence as a reason to discriminate, not to repeat."
    )


GhostBridgePreMoveADLToolAgent._build_user_prompt = _v15_build_user_prompt


def _v15_self_tests():
    tests = []

    # 1) Repeated no-impact action must lose to an untried legal alternative in CHANGE_POLICY.
    p = UnifiedCausalActionValuePlanner()
    for move in (1, 2):
        p.observe(
            "g-noop", "ACTION1",
            {"signature": "S", "levels": 0},
            {"signature": "S", "levels": 0},
            {"move": move, "no_impact": True, "loop_signal": True, "progress_value": -0.25, "score_delta": 0.0, "reward": 0.0, "level_delta": 0},
        )
    r = p.rank("g-noop", ["ACTION1", "ACTION2"], mode="CHANGE_POLICY")
    assert r["ranked"][0]["action"] == "ACTION2", r
    assert next(row for row in r["ranked"] if row["action"] == "ACTION1")["exhausted"], r
    tests.append("noop_exhaustion")

    # 2) Weighted ReversePath must recover the first bridge action from current state to a verified success state.
    p = UnifiedCausalActionValuePlanner()
    p.observe("g-reverse", "ACTION1", {"signature": "S0", "levels": 0}, {"signature": "S1", "levels": 0}, {"move": 1, "progress_value": 0.1})
    p.observe("g-reverse", "ACTION2", {"signature": "S1", "levels": 0}, {"signature": "G", "levels": 1}, {"move": 2, "progress_value": 1.0, "level_delta": 1})
    p.state("g-reverse").current_state = p._context_state("S0", 0)
    p.state("g-reverse").current_level = 0
    r = p.rank("g-reverse", ["ACTION1", "ACTION3"], mode="BALANCED")
    assert r["reverse_path"]["first_action"] == "ACTION1", r
    tests.append("weighted_reversepath")

    # 3) Verified state-local progress should dominate an untried action in exploit mode.
    p = UnifiedCausalActionValuePlanner()
    p.observe("g-exploit", "ACTION3", {"signature": "S", "levels": 0}, {"signature": "T", "levels": 0}, {"move": 1, "progress_value": 0.8, "score_delta": 0.5})
    p.state("g-exploit").current_state = p._context_state("S", 0)
    r = p.rank("g-exploit", ["ACTION3", "ACTION4"], mode="EXPLOIT")
    assert r["exploit_candidate"] == "ACTION3", r
    assert "structured" in r["ranked"][0], r
    tests.append("verified_exploit")

    # 4) Memory for an unavailable action can never make it into a legal ranking.
    p = UnifiedCausalActionValuePlanner()
    p.observe("g-legal", "ACTION9", {"signature": "S", "levels": 0}, {"signature": "G", "levels": 1}, {"move": 1, "progress_value": 1.0, "level_delta": 1})
    p.state("g-legal").current_state = p._context_state("S", 0)
    r = p.rank("g-legal", ["ACTION1", "ACTION2"], mode="EXPLOIT")
    assert all(row["action"] in {"ACTION1", "ACTION2"} for row in r["ranked"]), r
    tests.append("legal_set_fail_closed")

    # 5) Action normalization must collapse enum-like spellings without inventing coordinates/data.
    assert p._normalize_action("GameAction.ACTION6") == "ACTION6"
    assert p._normalize_action("action_7") == "ACTION7"
    tests.append("action_normalization")

    return tests


ARC3_V15_SELF_TESTS = _v15_self_tests()
print(
    "UCAV v15 ACTIVE: deterministic legal-action prior + Bayesian state-action evidence + "
    "weighted ReversePath + DifferenceRule/TrajectoryRule fusion + signature bridge + information value + exhaustion control; "
    f"self_tests={len(ARC3_V15_SELF_TESTS)}/{len(ARC3_V15_SELF_TESTS)}",
    flush=True,
)
