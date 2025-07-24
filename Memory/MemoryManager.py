import os

from Memory.LongMemory import LongMemory
from Memory.ShortMemory import ShortMemory

class MemoryManager:
    def __init__(self) -> None:
        self.short_memory = ShortMemory()
        self.long_memory = LongMemory()