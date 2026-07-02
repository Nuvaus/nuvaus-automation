# Prompt maestro — optimización completa de Jarvis en una pasada

Pegar TODO el bloque de abajo en el Claude Code local de la Mac
(el que corre en `/Users/nuvaus-ariel`). Es autocontenido: diagnostica,
te muestra el plan, **frena UNA vez a pedir tu OK antes de tocar nada**,
y recién ahí ejecuta todo, incluido el reinicio del daemon.

---

```text
Sos el optimizador de Jarvis (mi asistente Claude Code que corre como daemon
por Telegram en esta Mac). Objetivo: que responda más rápido manteniendo
exactamente la misma funcionalidad. Trabajá en estos pasos EN ORDEN.
Los pasos 1 y 2 son SOLO LECTURA. Frenás una única vez, en el paso 3,
y no tocás ningún archivo hasta mi OK.

## Paso 1 — Diagnóstico del daemon (solo lectura)
1. Identificá cómo corre el daemon: launchctl list | grep -i -E "jarvis|claude",
   pm2 list, ps aux | grep -i claude. Anotá el comando/plist/script que lo lanza.
2. Inspeccioná ese launcher: ¿usa --bare, --settings, --mcp-config,
   --append-system-prompt, --continue/--resume? Esto define QUÉ archivos
   carga Jarvis realmente. Si usa --settings o --mcp-config propios, los
   cambios van en ESOS archivos, no en ~/.claude/. Si usa --bare, avisame
   porque el plan cambia.
3. Localizá el MEMORY.md que el daemon carga de verdad (según su directorio
   de trabajo, en ~/.claude/projects/<proyecto>/memory/). Si no es
   inequívoco, preguntámelo en el paso 3.
4. Leé ~/.claude/settings.json (o el que use el daemon) y anotá model y
   effortLevel actuales.
5. Corré claude mcp list. Para saber qué servers usa Jarvis DE VERDAD,
   buscá evidencia en transcripts recientes:
   grep -rlo "mcp__<server>" ~/.claude/projects/ (últimas 2-4 semanas).

## Paso 2 — Auditoría del CLAUDE.md (solo lectura)
Leé ~/.claude/CLAUDE.md completo y corré: wc -l -c ~/.claude/CLAUDE.md
Inventariá sección por sección y clasificá cada una:
- QUEDA — identidad (máx 5 líneas), reglas duras, regla de uso de memoria,
  lista de skills (una línea c/u), datos usados en >50% de las charlas,
  y SIEMPRE las reglas de formato de salida para Telegram (parse mode,
  largos, estilo) — eso es contrato con el bridge, nunca va a BORRA.
  Reglas de velocidad: si el daemon ya inyecta asesor-persona.md, en
  CLAUDE.md va solo un puntero de una línea, no el bloque duplicado.
- SKILL — workflows multi-paso → ~/.claude/skills/<nombre>/SKILL.md
  (frontmatter name + description corta; el cuerpo carga al invocarse).
  IMPORTANTE: NO uses disable-model-invocation en estas skills — Jarvis
  debe poder dispararlas solo cuando Ariel se lo pide por Telegram.
- MEMORIA — datos de referencia (clientes, precios, historia) → topic
  files referenciados desde el índice MEMORY.md localizado en el paso 1.3.
- ANIDADO — reglas de un solo repo/proyecto → CLAUDE.md dentro de esa
  carpeta (cargan lazy, solo al trabajar ahí).
- BORRA — cosas que Claude ya sabe (git, sintaxis, buenas prácticas
  genéricas), ejemplos redundantes (dejar máx 1), relleno.

Reglas técnicas (verificadas en docs oficiales):
- Meta: <200 líneas. NO uses @imports para adelgazar: se expanden completos
  al inicio y cuentan contra el contexto igual.
- El texto que queda: bullets imperativos, tablas en vez de prosa.

## Paso 3 — Plan (FRENÁ ACÁ y esperá mi OK explícito)
Mostrame:
1. Tabla de decisiones: sección | destino | por qué | chars ahorrados.
2. Cómo corre el daemon y qué archivos carga (hallazgos del paso 1).
3. Propuesta de settings: effort para el daemon (preferí --effort medium o
   CLAUDE_CODE_EFFORT_LEVEL=medium en el launcher, NO tocar el settings.json
   global salvo que yo lo pida — es global para toda la Mac) y qué MCP
   servers deshabilitar según la evidencia de uso (de a uno, con su scope:
   los de .mcp.json van por disabledMcpjsonServers; los agregados con
   claude mcp add a nivel usuario se sacan con claude mcp remove).
4. Confirmá si la sección "Velocidad de respuesta" ya existe en
   /Users/nuvaus-ariel/repos/nuvaus/scripts/asesor-persona.md.
NO toques nada hasta que yo apruebe.

## Paso 4 — Ejecución (solo tras mi OK)
1. Detené el daemon (con el método hallado en el paso 1.1).
2. Backups con timestamp completo, abortando si ya existen (cp -n):
   TS=$(date +%F-%H%M%S)
   cp -n ~/.claude/CLAUDE.md ~/.claude/CLAUDE.md.bak-$TS
   cp -n ~/.claude/settings.json ~/.claude/settings.json.bak-$TS
   cp -n <MEMORY.md del paso 1.3> <mismo path>.bak-$TS
3. En /Users/nuvaus-ariel/repos/nuvaus/scripts/asesor-persona.md: si no
   existe la sección "Velocidad de respuesta", agregá al final EXACTAMENTE
   este bloque; si existe (cualquier versión), reemplazala completa:

## Velocidad de respuesta (CRÍTICO)

- El índice MEMORY.md ya está inyectado en contexto. No leas archivos
  individuales salvo que necesites un dato puntual que no esté en el índice.
- Preguntas conversacionales o que no requieran datos externos: respondé
  directo, sin herramientas.
- Máximo 2 llamadas a herramientas por respuesta en conversación normal.
  Si necesitás más, respondé con lo que tenés y preguntá si profundizo.
- Excepción: los workflows que Ariel pide explícitamente (armar propuesta,
  sync a Notion, resumen semanal, etc.) se ejecutan COMPLETOS, con todas
  las herramientas que hagan falta. El límite de 2 aplica solo a
  conversación, no a workflows pedidos.
- WebSearch solo si Ariel pide explícitamente precios o datos de mercado.
  Nunca de forma preventiva.
- Reutilizá el contexto que ya tenés en la conversación; no vuelvas a
  buscar algo que ya recuperaste.

4. Reescribí ~/.claude/CLAUDE.md compacto según la tabla aprobada, con esta
   estructura: 1) línea "Config: v2 (<fecha de hoy>)"; 2) Identidad, 3-5
   líneas con puntero a asesor-persona.md; 3) Reglas duras; 4) Velocidad
   (puntero o bloque según lo decidido); 5) Regla de uso de memoria;
   6) Lista de skills, una línea c/u; 7) Datos operativos mínimos en tabla;
   8) Formato Telegram.
5. Creá las skills y topic files con el contenido movido. Nada se borra sin
   reubicar, salvo lo marcado BORRA en la tabla aprobada.
6. Actualizá el índice MEMORY.md (el del paso 1.3): entradas de UNA línea
   por topic file. Después corré wc -l -c sobre él y verificá que quede
   <200 líneas y <25KB (solo eso se carga; si desborda, Jarvis "olvida"
   entradas sin aviso).
7. Aplicá los settings aprobados en el paso 3 (effort en el launcher del
   daemon; MCP según scope). Si tocaste algún JSON, validalo:
   python3 -m json.tool <archivo> — un JSON roto deja a Jarvis mudo.
8. Verificá: wc -l -c ~/.claude/CLAUDE.md (<200 líneas) y mostrame el
   mapping viejo→nuevo de cada sección movida.

## Paso 5 — Commit
En ~/repos/nuvaus: git add scripts/asesor-persona.md y commit con mensaje
"perf(jarvis): reglas de velocidad en asesor-persona" (en el cuerpo,
mencioná los cambios externos al repo: CLAUDE.md compacto, skills, memoria,
effort). ~/.claude no es repo: ya quedaron los .bak.

## Paso 6 — Reinicio y prueba
1. Reiniciá el daemon forzando SESIÓN NUEVA (sin --continue/--resume; si el
   launcher resume sesión, arrancá una fresca).
2. Avisame que el PRIMER mensaje por Telegram va a ser más lento (cache
   frío) — medir velocidad recién desde el segundo.
3. Prueba de humo que voy a correr por Telegram (dejámela lista):
   a. "¿qué versión de config tenés?" → debe decir "v2".
   b. "hola" → respuesta en segundos, sin herramientas.
   c. Pregunta por un dato MOVIDO a memoria → lo responde bien.
   d. Pedir un workflow migrado a skill → lo ejecuta completo.
   e. Una acción por cada MCP server que quedó activo.

## Rollback (si algo sale mal)
Si Jarvis deja de saber algo que sabía o falla un workflow: NO arregles en
caliente. Restaurá los .bak-$TS sobre sus originales, git revert del commit
de persona, reiniciá el daemon con sesión nueva, y revisamos el plan.

Al final resumime: chars antes/después del CLAUDE.md, qué se movió a dónde,
qué settings cambiaron y cómo reiniciar/rollbackear.
```
