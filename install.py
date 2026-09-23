# ----------------------------------------------------
# Hoshikuu - https://github.com/Hoshikuu
# ----------------------------------------------------
# HadaAI/install.py - V0.0.1

import os
from huggingface_hub import hf_hub_download

def descargar_modelo():
    repo_id = "bartowski/Qwen_Qwen3.5-35B-A3B-GGUF"
    filename = "Qwen_Qwen3.5-35B-A3B-Q2_K_L.gguf"

    directorio_destino = r".\hada\models"
    os.makedirs(directorio_destino, exist_ok=True)

    nuevo_nombre = "HadaAI-big.gguf"
    ruta_final = os.path.join(directorio_destino, nuevo_nombre)

    print(f"Iniciando descarga de {filename} (Aprox. 13.14 GB)...")
    print("Si la descarga se interrumpe, vuelve a ejecutar el script y continuará por donde se quedó.")

    model_path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        local_dir=directorio_destino,
    )

    if os.path.abspath(model_path) != os.path.abspath(ruta_final):
        if os.path.exists(ruta_final):
            os.remove(ruta_final)
        os.rename(model_path, ruta_final)

    print(f"\n¡Descarga completada con éxito!")
    print(f"Ruta del modelo: {ruta_final}")
    return ruta_final

if __name__ == "__main__":
    descargar_modelo()