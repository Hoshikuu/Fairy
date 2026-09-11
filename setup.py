from setup.llama_setup import main as llama_main
from setup.model_setup import main as model_main

def main():
    llama_main()
    print()
    model_main()

if __name__ == "__main__":
    main()