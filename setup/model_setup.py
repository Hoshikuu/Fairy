"""
Fairy model installer.

Downloads the default LLM models used by Fairy from Hugging Face.

Models:
- Spark-X2.5-4B Q4_K_M
- MiniCPM5-2B Q8_0

Requirements:
    pip install huggingface_hub

Models are downloaded to:
    ./models/
"""

from dataclasses import dataclass
from pathlib import Path

from huggingface_hub import hf_hub_download


# =========================================================
# CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"


# =========================================================
# DATA
# =========================================================

@dataclass
class Model:
    name: str
    repo: str
    filename: str
    size_gb: float


MODELS = [
    Model(
        name="Spark-X2.5-4B",
        repo="XHToken/Spark-X2.5-4B-GGUF",
        filename="Spark-X2.5-4B-Q4_K_M.gguf",
        size_gb=2.60
    ),
    Model(
        name="MiniCPM5-2B",
        repo="openbmb/MiniCPM5-2B-GGUF",
        filename="MiniCPM5-2B-Q8_0.gguf",
        size_gb=2.68
    )
]


# =========================================================
# UTILITIES
# =========================================================

def model_path(model: Model) -> Path:
    """Return the expected local model path."""

    return MODELS_DIR / model.filename


def is_installed(model: Model) -> bool:
    """Check whether a model is already installed."""

    path = model_path(model)

    return (
        path.exists()
        and path.is_file()
        and path.stat().st_size > 0
    )


def ask_confirmation(message: str) -> bool:
    """Ask the user for Y/N confirmation."""

    while True:
        answer = input(
            f"{message} [Y/N]: "
        ).strip().lower()

        if answer in ("y", "yes"):
            return True

        if answer in ("n", "no"):
            return False

        print("Please enter Y or N.")


def format_size(size_gb: float) -> str:
    """Format the model size."""

    return f"{size_gb:.2f} GB"


# =========================================================
# DOWNLOAD
# =========================================================

def download_model(model: Model) -> bool:
    """Download a model from Hugging Face."""

    print()
    print(f"Downloading {model.name}...")

    try:
        path = hf_hub_download(
            repo_id=model.repo,
            filename=model.filename,
            local_dir=MODELS_DIR
        )

    except Exception as error:
        print()
        print(
            f"Failed to download {model.name}:"
        )
        print(error)

        return False

    print()
    print(
        f"{model.name} downloaded successfully."
    )

    print(
        f"Model path: {path}"
    )

    return True


# =========================================================
# INSTALLATION
# =========================================================

def install_models():
    """Install every required model that is currently missing."""

    MODELS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    missing_models = [
        model
        for model in MODELS
        if not is_installed(model)
    ]

    if not missing_models:
        print(
            "All models are already installed."
        )
        return

    total_size = sum(
        model.size_gb
        for model in missing_models
    )

    print("Models to install:")
    print()

    for model in missing_models:
        print(
            f"  - {model.name} "
            f"({format_size(model.size_gb)})"
        )

    print()
    print(
        f"Required download size: "
        f"{format_size(total_size)}"
    )

    print()

    if not ask_confirmation(
        "Do you want to download the required Fairy models "
        f"({format_size(total_size)} total)?"
    ):
        print()
        print(
            "Model installation cancelled."
        )
        return

    print()
    print(
        "Downloading models..."
    )

    successful = 0

    for model in missing_models:
        if download_model(model):
            successful += 1

    print()

    if successful == len(missing_models):
        print(
            "All required models were installed successfully."
        )
    else:
        print(
            f"{successful}/{len(missing_models)} "
            "models were installed successfully."
        )

    print(
        f"Models directory: {MODELS_DIR}"
    )


# =========================================================
# DISPLAY
# =========================================================

def print_models():
    """Display the current installation status."""

    print("Models:")
    print()

    for model in MODELS:
        status = (
            "Installed"
            if is_installed(model)
            else "Not installed"
        )

        print(
            f"  {model.name}"
        )

        print(
            f"    Size:   "
            f"{format_size(model.size_gb)}"
        )

        print(
            f"    Status: {status}"
        )

        print()


# =========================================================
# MAIN
# =========================================================

def main():
    print(
        "Fairy Model Installer"
    )

    print(
        "====================="
    )

    print()

    print_models()

    install_models()


if __name__ == "__main__":
    main()