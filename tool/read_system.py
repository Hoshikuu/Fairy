def system_prompt():
    with open("prompt/system.txt") as f:
        r = f.read()
        return r