from setup.llama_setup import main as llama_main
from setup.whisper_setup import main as whisper_main
from setup.model_setup import main as model_main


def main() -> int:
    for installer in (llama_main, whisper_main, model_main):
        result = installer()
        if result != 0:
            return result
        print()

    print("Fairy setup completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
