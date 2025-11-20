# Integración Futura: Claude / Otros Proveedores

Este documento describe cómo se añadirá soporte para proveedores externos como Claude.

## Objetivo

Permitir cambiar entre ejecución local (Hugging Face) y proveedores remotos sin alterar la lógica de negocio ni los endpoints existentes.

## Abstracción

- Interfaz base: `app/providers/base.py` (`BaseLLMProvider`).
- Implementaciones futuras:
  - `ClaudeProvider` (usa API hosted, requiere `CLAUDE_API_KEY`).
  - `OpenAIProvider` (usa `OPENAI_API_KEY`).

## Selección

Se define `provider` en `config/config.json` o variable de entorno `LLM_PROVIDER`.

```
{
  "selected_model": "gpt2",
  "provider": "hf"
}
```

Cambiar a `claude` activará la rama lógica que instanciará `ClaudeProvider` (pendiente).

## Variables de Entorno Previstas

- `LLM_PROVIDER=claude`
- `CLAUDE_API_KEY="sk-..."`
- (Opcional) parámetros como temperatura, top_p específicos.

## Flujo /predict

1. Router recibe prompt.
2. Llama a `model_manager.generate()`.
3. `model_manager` delega en proveedor según `config.provider`.
4. Respuesta unificada: `{ generated_text }`.

## Manejo de Errores

- Timeout proveedor → 504.
- Auth inválida → 401/403.
- Cuota excedida → 429.

## Seguridad

- Nunca registrar API keys en logs.
- Usar variables de entorno y opcionalmente gestor de secretos.

## Próximos Pasos

1. Implementar `ClaudeProvider` stub.
2. Añadir tests de selección de proveedor.
3. Añadir métricas por proveedor.

---

Documento preliminar.
