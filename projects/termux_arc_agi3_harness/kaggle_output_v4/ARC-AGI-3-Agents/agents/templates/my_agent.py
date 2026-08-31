
import hashlib, random, math
from collections import Counter, defaultdict, deque
import numpy as np

try:
    from agents.agent import Agent
except Exception:
    class Agent: pass

try:
    from adaptive_priors import ADAPTIVE_ACTION_PRIORS
except Exception:
    ADAPTIVE_ACTION_PRIORS = {}

ACTION_NAMES = {
    1: 'ACTION1', 2: 'ACTION2', 3: 'ACTION3',
    4: 'ACTION4', 5: 'ACTION5', 6: 'ACTION6', 7: 'ACTION7'
}

def frame_array(obs):
    if hasattr(obs, 'frame'):
        f = obs.frame
    elif isinstance(obs, dict) and 'frame' in obs:
        f = obs['frame']
    else:
        f = obs
    if isinstance(f, (list, tuple)) and len(f):
        f = f[-1]
    arr = np.asarray(f)
    if arr.ndim == 3 and arr.shape[0] == 1:
        arr = arr[0]
    return arr.astype(np.int16, copy=False)

def frame_hash(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()[:16]

def available_ids(obs):
    vals = []
    for name in ('available_actions', 'actions'):
        xs = getattr(obs, name, None)
        if xs:
            for a in xs:
                try: vals.append(int(a.value if hasattr(a, 'value') else a))
                except Exception: pass
    return sorted(set(vals)) or [1,2,3,4,5,6]

class SoftPriorVoteLearn:
    def __init__(self):
        self.value = defaultdict(float)
        self.trials = Counter()
        self.recent = deque(maxlen=12)
        self.prev_frame = None
        self.prev_state = None
        self.prev_action = None
        self.prev_level = 0

    def choose(self, obs, game_id='unknown', level=0):
        arr = frame_array(obs)
        state = frame_hash(arr)
        avail = available_ids(obs)
        root = str(game_id).split('-')[0]

        scores = defaultdict(float)
        reasons = defaultdict(list)

        for a in avail:
            scores[a] += 0.01
            reasons[a].append('base_safe')
            scores[a] += 0.08 * math.tanh(self.value[(state, a)])
            if self.recent.count(a) >= 4:
                scores[a] -= 0.40
                reasons[a].append('repeat_penalty')

        for key in (f'{root}:{level}', f'{root}:None'):
            for item in ADAPTIVE_ACTION_PRIORS.get(key, []):
                a = int(item.get('action', 0))
                if a in avail:
                    scores[a] += 0.20 * float(item.get('score', 0))
                    reasons[a].append('termux_soft_prior')

        # Low-cost BlindSight bias: prefer movement keys when available.
        for a in [1,2,3,4]:
            if a in avail:
                scores[a] += 0.02
                reasons[a].append('movement_probe')

        best = max(avail, key=lambda a: scores[a])
        self.recent.append(best)
        self.prev_frame = arr.copy()
        self.prev_state = state
        self.prev_action = best
        return best, {'reason': '+'.join(reasons[best]), 'score': scores[best]}

    def learn(self, obs, level=0):
        if self.prev_frame is None or self.prev_action is None:
            return
        arr = frame_array(obs)
        delta = int(np.sum(arr != self.prev_frame)) if arr.shape == self.prev_frame.shape else 999
        reward = 0.0
        if delta > 0: reward += min(0.25, delta / max(64.0, float(arr.size)))
        else: reward -= 0.30
        if level > self.prev_level: reward += 1.5
        self.value[(self.prev_state, self.prev_action)] = 0.85 * self.value[(self.prev_state, self.prev_action)] + reward
        self.trials[(self.prev_state, self.prev_action)] += 1
        self.prev_level = level

class MyAgent(Agent):
    def __init__(self, *args, **kwargs):
        try: super().__init__(*args, **kwargs)
        except Exception: pass
        self.policy = SoftPriorVoteLearn()
        self.game_id = str(kwargs.get('game_id', 'unknown'))
        self.level = 0

    def choose_action(self, obs):
        try:
            info = getattr(obs, 'info', {}) or {}
            self.level = int(info.get('local_level_index', info.get('level', self.level)))
        except Exception:
            pass
        self.policy.learn(obs, self.level)
        action_id, meta = self.policy.choose(obs, self.game_id, self.level)
        name = ACTION_NAMES.get(int(action_id), 'ACTION1')
        try:
            from arc import Action
            act = getattr(Action, name)
            act.reasoning = {'action': name, **meta}
            return act
        except Exception:
            return int(action_id)
