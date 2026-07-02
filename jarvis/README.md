# Jarvis — Paquete de optimización de velocidad

Entregables para hacer que Jarvis (el asistente Claude Code de Ariel, daemon
por Telegram) responda más rápido sin perder funcionalidad.

| Archivo | Qué es | Cómo se usa |
|---|---|---|
| [`PROMPT-OPTIMIZACION.md`](PROMPT-OPTIMIZACION.md) | **Prompt maestro** — ejecuta toda la optimización en una pasada | Copiar el bloque y pegarlo en el Claude Code local de la Mac. Diagnostica en solo-lectura, frena UNA vez a pedir OK antes de tocar nada, ejecuta, reinicia el daemon y deja lista la prueba de humo |
| [`GUIA-OPTIMIZACION.md`](GUIA-OPTIMIZACION.md) | Playbook completo: cómo carga contexto Claude Code, las 7 palancas de velocidad, prueba de humo y rollback, con fuentes oficiales | Referencia — leer si querés entender el porqué de cada cambio |
| [`CLAUDE.template.md`](CLAUDE.template.md) | Esqueleto de referencia del `~/.claude/CLAUDE.md` compacto (<200 líneas) | El prompt maestro lleva la misma estructura embebida; usar este archivo para comparar el resultado final |
| [`persona-velocidad.md`](persona-velocidad.md) | Sección "Velocidad de respuesta" para `asesor-persona.md` | Incluida idéntica en el prompt maestro; también se puede pegar a mano |

## Resumen ejecutivo (las 4 palancas grandes)

1. **Effort del modelo**: la sesión corre en `xhigh` → para chat conversacional,
   `medium` recorta segundos por turno. Aplicarlo **al launcher del daemon**
   (`--effort medium` / `CLAUDE_CODE_EFFORT_LEVEL=medium`), no global.
2. **CLAUDE.md a dieta**: 43.1k chars → meta <200 líneas. Mover workflows a
   skills (cargan on-demand), datos a topic files de memoria, y borrar lo que
   Claude ya sabe. ⚠️ Los `@imports` NO reducen contexto.
3. **Persona con reglas de velocidad**: límite de tool calls en conversación
   (con excepción para workflows pedidos), sin WebSearch preventivo,
   responder directo lo conversacional.
4. **Ciclo de vida del daemon**: nada aplica sin detener → editar → reiniciar
   con sesión nueva. El primer mensaje post-reinicio es lento (cache frío) —
   medir desde el segundo. Verificación: preguntar "¿qué versión de config
   tenés?" → "v2".

Verificado contra docs oficiales (fuentes en `GUIA-OPTIMIZACION.md`) y
revisado adversarialmente: fact-check de cada afirmación técnica + revisión
de coherencia y completitud (19 hallazgos aplicados).
