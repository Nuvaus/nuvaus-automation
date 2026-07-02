# Guía de optimización de Jarvis (velocidad + eficiencia de contexto)

Objetivo: que Jarvis responda rápido y siga haciendo exactamente lo mismo,
moviendo contenido de "siempre cargado" a "cargado solo cuando hace falta".

Todo lo técnico de esta guía está verificado contra docs oficiales de
Claude Code (fuentes al pie).

---

## 1. Diagnóstico

| Problema | Evidencia | Impacto |
|---|---|---|
| `~/.claude/CLAUDE.md` de 43.1k chars | Warning de Claude Code (umbral 40k chars); la guía oficial recomienda **<200 líneas** | Consume contexto en cada request y **reduce adherencia** a las instrucciones |
| Effort `xhigh` | Banner de la sesión: `claude-fable-5[1m] with xhigh` | Thinking extendido en cada turno → segundos extra de latencia en chat conversacional |
| Persona sin reglas de velocidad | Jarvis hacía tool calls innecesarios | Se resuelve con `persona-velocidad.md` (lo aplica el prompt maestro) |
| Muchos MCP servers conectados | — | Menor de lo esperado: el *tool search* ya difiere los schemas por defecto; pero las *instrucciones* de cada server sí cargan al inicio |

---

## 2. Cómo carga contexto Claude Code (verificado)

| Fuente | Cuándo carga | Implicación práctica |
|---|---|---|
| `CLAUDE.md` (usuario y proyecto) | Al **inicio de sesión**; queda en contexto todos los turnos (con prompt caching) | Cada char cuenta en cada request. Editarlo a mitad de sesión NO aplica hasta reiniciar / `/clear` |
| `@imports` dentro de CLAUDE.md | Al inicio, **expandidos completos** | ⚠️ **NO reducen contexto** — solo ordenan. No sirven para adelgazar |
| `CLAUDE.md` anidados (subcarpetas) | **Lazy**: solo cuando Claude toca archivos de esa subcarpeta | Ideal para reglas específicas de un proyecto/cliente |
| Memoria auto (`MEMORY.md`) | Índice: primeras **200 líneas o 25KB**. Topic files: **on-demand** | El patrón que ya usa Jarvis. Meter más contenido acá |
| Skills (`~/.claude/skills/*/SKILL.md`) | Solo **nombre + descripción** al inicio; el cuerpo al invocarse | El mejor lugar para workflows multi-paso. ⚠️ `disable-model-invocation: true` = costo cero, pero la skill solo se dispara tipeando `/nombre` — **NO usarlo en los workflows de Jarvis** (debe poder invocarlos solo cuando Ariel se lo pide por Telegram); reservarlo para utilidades manuales |
| Rules (`~/.claude/rules/`) | Path-scoped | Reglas que aplican solo a ciertas rutas |
| MCP tool schemas | Diferidos por defecto (tool search): solo nombres al inicio | No es la fuente principal de bloat; las instrucciones de server sí cargan |

---

## 3. Palancas, ordenadas por impacto/esfuerzo

### 3.1 Bajar el effort para chat (1 minuto, impacto alto)
Fable 5 usa effort `high` por defecto; la sesión de Ariel está en `xhigh`.
Para un asistente conversacional tipo Jarvis, `medium` responde mucho más
rápido sin pérdida perceptible en turnos de conversación.

- **Preferido — solo el daemon**: flag `--effort medium` o env
  `CLAUDE_CODE_EFFORT_LEVEL=medium` en el script/plist que lanza a Jarvis.
  Así las sesiones interactivas de trabajo pesado siguen en high/xhigh.
- En sesión interactiva: `/effort medium` (o el slider en `/model`).
- ⚠️ `"effortLevel": "medium"` en `~/.claude/settings.json` es **global para
  toda la Mac** — también baja el effort de las sesiones de código. Usarlo
  solo a sabiendas.
- Opcional chat ultrarrápido: `"alwaysThinkingEnabled": false`.

⚠️ Cambiar effort a mitad de sesión invalida el prompt cache (el turno
siguiente recalcula todo). Hacerlo al inicio de sesión.

### 3.2 Dieta del CLAUDE.md (la palanca estructural)
Meta: **<200 líneas / ~10-12k chars**. Regla de decisión por sección:

| La sección es… | Va a… |
|---|---|
| Identidad, reglas duras, reglas de velocidad, índice de memoria, punteros | **Queda** en CLAUDE.md |
| Workflow multi-paso ("cómo armar propuesta", "cómo sincronizar Notion") | **Skill** en `~/.claude/skills/<nombre>/SKILL.md` |
| Datos de referencia (clientes, precios, historia, contexto de negocio) | **Topic file** indexado por MEMORY.md |
| Reglas de un solo proyecto/repo | **CLAUDE.md anidado** en esa carpeta, o `~/.claude/rules/` |
| Cosas que Claude ya sabe (git, sintaxis, buenas prácticas genéricas), ejemplos redundantes, relleno | **Borrar** |

Técnicas de compactación del texto que queda:
- Prosa → bullets imperativos ("X → hacé Y").
- 0-1 ejemplo por regla, nunca 3.
- Tablas en vez de párrafos para listas.
- Sin justificaciones ni cortesías: solo la instrucción.

⚠️ **No** usar `@imports` como método de adelgazamiento: cargan igual.

### 3.3 Persona con reglas de velocidad (ya definido)
Ver `persona-velocidad.md` en esta carpeta → pegar al final de
`~/repos/nuvaus/scripts/asesor-persona.md`.

### 3.4 Higiene de MCP servers
- No adivinar qué servers "no se usan": buscar **evidencia** en transcripts
  recientes (`grep -rlo "mcp__<server>" ~/.claude/projects/`, últimas 2-4
  semanas). Un server poco frecuente pero crítico (Gmail 1×/semana) apagado
  es un fallo silencioso que aparece días después.
- El scope importa: `"disabledMcpjsonServers"` solo apaga servers definidos
  en `.mcp.json`; los agregados con `claude mcp add` a nivel usuario se
  sacan con `claude mcp remove`.
- Deshabilitar **de a uno** y probar la capacidad que queda viva (pedirle a
  Jarvis un mail, una consulta a Notion, etc.).
- El tool search (diferido) ya está activo por defecto — no tocar
  `ENABLE_TOOL_SEARCH` salvo problema puntual.
- Nota: los modelos Haiku NO soportan tool search (cargan todos los schemas);
  si el daemon usara Haiku, podar MCP importa mucho más.

### 3.5 Daemon headless (`claude -p`)
- `--allowedTools "Read,Grep,..."` → sin prompts de permiso.
- `--mcp-config <archivo>` + `--strict-mcp-config` → solo los servers que el daemon necesita.
- `--settings <archivo>` → settings mínimos y explícitos para el daemon.
- `--bare` skipea TODO (CLAUDE.md, memoria, skills): útil para scripts
  puntuales, **NO para el Jarvis principal** (perdería la persona).

### 3.6 Sesiones calientes y contexto largo
- Cache TTL con suscripción: ~1 hora. El daemon conviene que reuse sesión
  dentro de esa ventana en vez de arrancar en frío.
- `/rewind` reusa el cache (rápido); `/compact` lo invalida pero achica el
  historial (útil cuando la conversación ya es muy larga).
- Tareas verbosas (logs, tests, research) → subagentes: su contexto no
  contamina la sesión principal.

### 3.7 Ciclo de vida del daemon (crítico para que TODO lo anterior aplique)
- CLAUDE.md, settings y memoria se leen **al inicio de sesión**: editar con
  el daemon vivo NO aplica a la sesión en curso (y la memoria auto puede
  pisar tus cambios al guardar).
- Orden correcto: **detener daemon → editar → reiniciar con sesión NUEVA**
  (sin `--continue`/`--resume`, o los cambios siguen sin aplicar).
- Tras el reinicio, el primer mensaje es MÁS lento (cache frío). Medir
  velocidad desde el segundo mensaje.
- Truco de verificación: poner una línea `Config: v2 (fecha)` en el
  CLAUDE.md nuevo y preguntar por Telegram "¿qué versión de config tenés?"
  — si responde v2, los cambios aplicaron.
- Antes de asumir que `~/.claude/` le aplica al daemon, inspeccionar su
  launcher: si pasa `--settings`, `--mcp-config` o `--bare` propios, los
  cambios van en esos archivos.

---

## 4. Cómo medir (antes/después)

```bash
wc -l -c ~/.claude/CLAUDE.md        # meta: <200 líneas
```
- `/context` en sesión → qué está consumiendo espacio.
- `/cost` → uso; un ratio alto de cache reads = va bien.

### Prueba de humo: 5 mensajes por Telegram (tras reiniciar el daemon)
1. "¿Qué versión de config tenés?" → debe responder **v2** (prueba que los
   cambios aplicaron).
2. "Hola" → respuesta en segundos, **sin herramientas**.
3. Pregunta por un dato que se MOVIÓ a memoria (ej. un detalle de CECA) →
   lo responde bien (prueba que lee el topic file).
4. Pedir un workflow migrado a skill ("armame la propuesta para X") → lo
   ejecuta completo.
5. Una acción por cada MCP server que quedó activo (un mail, una consulta
   a Notion…).

Cronometrar 3 mensajes iguales antes y después — ignorando el primero
post-reinicio (cache frío, siempre es lento).

---

## 5. Checklist de implementación

- [ ] Daemon identificado (launcher, flags) y **detenido** antes de editar
- [ ] Backups con timestamp completo de CLAUDE.md, settings.json y MEMORY.md
      (`cp -n archivo archivo.bak-$(date +%F-%H%M%S)` — abortar si existe)
- [ ] Sección de velocidad agregada/reemplazada en `asesor-persona.md`
- [ ] CLAUDE.md reescrito <200 líneas (con línea `Config: v2`) según tabla aprobada
- [ ] Todo lo movido tiene destino (mapping viejo→nuevo, nada borrado sin reubicar)
- [ ] Workflows convertidos a skills e invocables (sin `disable-model-invocation`)
- [ ] Índice MEMORY.md actualizado y verificado <200 líneas / <25KB
- [ ] Effort `medium` aplicado **al daemon** (launcher), no global
- [ ] MCP: solo deshabilitados los sin evidencia de uso, de a uno, con scope correcto
- [ ] JSONs editados validados con `python3 -m json.tool`
- [ ] Daemon **reiniciado con sesión nueva** y prueba de humo (sección 4) pasada

## 6. Rollback

Si Jarvis deja de saber algo que sabía, falla un workflow o queda mudo:
**no arreglar en caliente.**

```bash
# restaurar cada backup sobre su original
cp ~/.claude/CLAUDE.md.bak-<TS> ~/.claude/CLAUDE.md
cp ~/.claude/settings.json.bak-<TS> ~/.claude/settings.json
cp <memoria>.bak-<TS> <memoria>
# revertir el cambio de persona
cd ~/repos/nuvaus && git revert <commit>
# reiniciar el daemon con sesión nueva
```

Después se revisa el plan con calma. Jarvis mudo suele ser JSON roto en
settings — validar con `python3 -m json.tool`.

---

## 7. Fuentes (docs oficiales)

- Memoria, imports, nested, límites: <https://code.claude.com/docs/en/memory.md>
- Skills y carga on-demand: <https://code.claude.com/docs/en/skills.md>
- Modelo y effort: <https://code.claude.com/docs/en/model-config.md>
- MCP y tool search: <https://code.claude.com/docs/en/mcp.md>
- Headless / daemon: <https://code.claude.com/docs/en/headless.md>
- Prompt caching: <https://code.claude.com/docs/en/prompt-caching.md>
