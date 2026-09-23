import os

from fairseq import checkpoint_utils

def load_hubert(config):
    models, _, _ = checkpoint_utils.load_model_ensemble_and_task(
        ["hada/models/hubert/hubert_base.pt"],
        suffix="",
    )
    hubert_model = models[0]
    hubert_model = hubert_model.to(config.device)
    if config.is_half:
        hubert_model = hubert_model.half()
    else:
        hubert_model = hubert_model.float()
    return hubert_model.eval()
