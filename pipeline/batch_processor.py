"""Parallel processing utilities for tile pipeline."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple


class BatchProcessor:
    def __init__(self, num_workers: int = 4):
        self.num_workers = max(1, int(num_workers))

    def process_tiles(self, tile_list: List[Tuple[int, str]], processor) -> List[Dict]:
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            results = list(executor.map(processor.process, tile_list))
        return [r for r in results if r is not None]

