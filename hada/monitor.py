import sys
import time
import os
import struct
from multiprocessing import shared_memory

def main():
    shm_name = sys.argv[1]
    shm = shared_memory.SharedMemory(name=shm_name)

    """
        1. I -> Context Max -> 0
        2. I -> Predict Max -> 4
        3. I -> Context     -> 8
        4. I -> Predict     -> 12
        5. d -> TPS         -> 16
    """
    try:
        while True:
            v1, v2 = struct.unpack_from("Id", shm.buf, 12)
            os.system("cls")
            print("Monitor")
            print("Tokens =", v1)
            print("TPS =", v2)
            time.sleep(0.25)
    finally:
        shm.close()

if __name__ == "__main__":
    main()