from __future__ import annotations

from collections import deque

from .schemas import ImmutableObservation


class RegionModel:
    def topology(self, observation: ImmutableObservation) -> dict[str, object]:
        open_cells = {(x,y) for y,row in enumerate(observation.frame) for x,value in enumerate(row) if value == 0}
        regions = []
        while open_cells:
            start = next(iter(open_cells)); queue = deque([start]); open_cells.remove(start); region = {start}
            while queue:
                x,y = queue.popleft()
                for neighbor in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                    if neighbor in open_cells: open_cells.remove(neighbor); region.add(neighbor); queue.append(neighbor)
            regions.append(region)
        return {"region_count": len(regions), "region_sizes": tuple(sorted((len(item) for item in regions), reverse=True)), "reachable_cells": sum(map(len, regions))}

