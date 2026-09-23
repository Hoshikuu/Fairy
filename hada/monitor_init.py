from subprocess import Popen as proc
from sys import executable
from struct import pack_into
from multiprocessing import shared_memory

class Monitor:
    def __init__(self):
        self.shm = shared_memory.SharedMemory(create=True, size=28)
    
    def run(self):
        proc(
            f'start cmd /k "{executable} hada/monitor.py {self.shm.name}"',
            shell=True
        )

    def pack(self, count: int, type: str, offset: int, items: list):
        pack_into(type, self.shm.buf, offset, items[0], items[1])

    def close(self):
        self.shm.close()
        self.shm.unlink()