# Aprendizajes de Fairy

## [LRN-20261031-001] Dependencias de la demo

**Category**: correction
**Status**: applied
**Summary**: Fairy debe funcionar sin FairyWeb. llama.cpp vive en `llama/` en la raíz y los GGUF en `models/`.
**Evidence**: Peticiones del usuario y `fairy/paths.py`.
**Revalidation**: Revisar si cambian las rutas o el instalador.

## [LRN-20261031-002] Consola y mensajes

**Category**: correction
**Status**: applied
**Summary**: El instalador usa líneas compactas con barras al estilo de `bfairy`, sin separadores decorativos. Los mensajes del bot y sus respuestas se solicitan en inglés.
**Evidence**: Peticiones del usuario, `fairy/installation/progress.py` y `fairy/prompts/system.txt`.
**Revalidation**: Revisar si cambia la preferencia del usuario.

## [LRN-20261031-003] LFM3 Omni y herramientas

**Category**: knowledge_gap
**Status**: verified
**Summary**: LFM3-Omni-2B no admite modo thinking; usar `--reasoning off`. El protocolo realtime documenta tool calling, pero Fairy todavía no lo implementa.
**Evidence**: https://huggingface.co/LiquidAI/LFM3-Omni-2B-GGUF y https://github.com/ggml-org/llama.cpp/blob/b11960/tools/server/README.md#realtime-conversation
**Revalidation**: Verificar con la ficha del modelo y versión de llama.cpp al cambiar cualquiera.
