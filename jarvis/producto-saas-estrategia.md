# Jarvis como producto SaaS estrella de Nuvaus — Estrategia

**Fecha:** 2026-07-08 · **Autor:** análisis multiagente (Claude, sesión Nuvaus) · **Estado:** documento de decisión
**TC referencia:** US$1 = CLP $926 (Banco Central, 8-jul-2026)

> Nota de branding: "Jarvis" es el nombre de trabajo. El asistente evolucionará a **voz** y su nombre definitivo se define más adelante (decisión registrada en jarvis-memoria id 20). No fijar el nombre en marca/producto todavía.

---

## 1. Veredicto en una frase

**Sí, Jarvis puede ser un producto estrella de Nuvaus — pero NO como se planteó.** No es "asistente por WhatsApp para todo" (ese canal quedó legalmente cerrado y ese posicionamiento ya lo ganó Meta AI). Es un **"chief of staff de IA en español"** para profesionales y pymes de Chile/LatAm, con memoria persistente propia como foso, canal-agnóstico (Telegram + app/web + voz), y de pago desde el día 1. La v1 cobrable es construible en **6–8 semanas en paralelo con los servicios**, con alcance recortado.

**El orden correcto de prioridades para Nuvaus hoy:**
1. **Caja ya** (semanas 1–6): servicios productizados de automatización → llegar a CLP 1M/mes. Ver `nuvaus/plan-facturacion-1M.md`.
2. **Producto en paralelo** (semanas 2–8): construir la v1 SaaS de Jarvis con founding members de pago, financiada y validada por lo que aprendes vendiendo servicios.
3. El SaaS **no reemplaza** los servicios hasta que la retención D30 y el margen por usuario estén probados. Es la apuesta que mueve la aguja **con el tiempo**, no la que paga julio.

---

## 2. El golpe de realidad que redefine la estrategia: el veto de WhatsApp

**El 15 de enero de 2026 Meta prohibió los chatbots de propósito general en la API de WhatsApp Business.** Los "AI providers" quedan excluidos cuando la IA es la funcionalidad principal — "as determined by Meta in its sole discretion". ChatGPT, Perplexity, Copilot, **Luzia** y Poke tuvieron que salir de WhatsApp. Meta AI quedó como el único asistente general permitido dentro de la app.

- Hay investigaciones antimonopolio abiertas: UE (dic-2025), Italia/AGCM (suspendió la política 24-dic-2025), **Brasil/CADE (cautelar 12-13 ene-2026)**. En marzo 2026 Meta propuso readmitir chatbots **cobrándoles** el acceso.
- **Chile no tiene medida equivalente: para un producto chileno, el veto aplica.**
- **Consecuencia de diseño:** "WhatsApp-first" como canal principal de un asistente personal ya no es viable — es un riesgo existencial. Jarvis debe ser **canal-agnóstico**.

**Matiz importante para Nuvaus:** este veto aplica al *asistente personal de propósito general*. **NO** aplica al caso B2B de servicios (un bot de atención a clientes de una pyme, donde la IA es incidental al negocio del cliente) — ese es exactamente el `plan-facturacion-1M.md` y es 100% legítimo en WhatsApp. Es decir: WhatsApp sirve para el negocio de servicios, no para el producto Jarvis-consumer.

### Vías de canal para el producto Jarvis
- **Telegram como canal primario** — API abierta, bots de pleno derecho, sin riesgo de veto.
- **App/PWA propia** — soberanía de canal; es lo que salvó a Luzia y Zapia (migraron a app a tiempo).
- **Correo y calendario como "canales de acción"** (el asistente actúa sobre ellos).
- **Voz en fase 2** — diferenciador que en español nadie tiene (ni Luzia, ni Zapia, ni Meta AI).
- **WhatsApp solo condicionado**: si/cuando Meta abra acceso pagado, o para el modo B2B.

---

## 3. Mapa competitivo (2025–2026)

| Producto | Precio | Canales | Tracción | Ejecuta tareas reales | Español/LatAm |
|---|---|---|---|---|---|
| **Martin** ("Your AI like Jarvis") | US$21–49/mes | Voz, SMS, WhatsApp, email, tel. | ~100K usuarios, $2M seed (YC) | Sí | No |
| **Lindy** | US$49–199/mes | Web/app, integraciones | SaaS prosumer establecido | Sí (workflows) | No |
| **Ohai** | US$0–19,99/mes | SMS, email, app | Nicho familiar EE.UU. | Parcial | No |
| **Poke** (Interaction Co.) | Premium | iMessage → Apple Business | $15M seed (General Catalyst) | Sí | No |
| **Luzia** | Gratis | WhatsApp→app + Telegram | **85M registrados**, $56,5M | No (chat/utilidades) | **Sí (líder)** |
| **Zapia** (BrainLogic) | Gratis | WhatsApp→app | **6M+ usuarios**, $19,3M (Prosus) | **Sí (Zapia Max)** | **Sí (LatAm)** |
| **Meta AI** | Gratis | WhatsApp/IG/Messenger | **1.000M MAU** | No | Sí |

**Lecturas clave:**
- **Martin** es literalmente "tu IA como Jarvis": llegó a 100K usuarios con YC y $2M, pero sus fundadores lo describen como "our last product" y pivotearon a Letterbook. Señal dura: incluso con marca, YC y volumen, el asistente personal *standalone* fue difícil de sostener (soporte intensivo, churn, costos).
- **Lindy** valida que el prosumer paga US$50–200/mes cuando el asistente **ejecuta trabajo real** conectado a herramientas — la tesis multiagente+MCP de Jarvis.
- **Zapia** es el competidor más parecido a la visión de Jarvis (agente que ejecuta, LatAm, español, integraciones Google/Microsoft), respaldado por Prosus — pero sin memoria unificada compartida entre agentes, sin self-hosted, sin privacidad, foco masivo-consumer.
- **Meta AI** gana el Q&A casual gratis. Deja abierto el espacio del asistente que *hace* cosas sobre tus sistemas. El propio Zuckerberg admitió (jul-2026) que "los agentes de IA no han progresado tan rápido como esperaba".

**El hueco de mercado:** entre **Zapia** (masivo, gratis, superficial) y **Lindy** (potente, caro, en inglés) no hay nadie. Ese es el espacio de Jarvis: **potente + en español + precio LatAm**.

---

## 4. Diferenciadores defendibles (ordenados por foso real)

1. **Memoria unificada propia (servidor MCP) — el foso más fuerte.** Nadie ofrece memoria persistente, estructurada, consultable, editable y portable que viva *fuera* del canal y del modelo. Jarvis ya la tiene en producción (`memoria.nuvaus.com`). El costo de cambio de un asistente que acumula años de contexto es el foso clásico de la categoría.
2. **Multiagente con herramientas reales vía MCP** — calendario, Gmail, Notion, Drive, archivos, GitHub. Ventaja de velocidad (agregar integraciones más rápido que conectores propietarios), no foso permanente, pero real hoy.
3. **Self-hosted / privacidad** — único ángulo donde Meta/Luzia/Zapia estructuralmente no pueden seguir (su negocio depende de centralizar datos). Justifica precio premium en prosumer/B2B: estudios jurídicos, salud, finanzas, familias de alto patrimonio.
4. **Español nativo con contexto local (Chile/LatAm)** — RUT, UF, SII, FONASA, Previred, feriados, permiso de circulación. Luzia/Zapia cubren español general; el nivel local sigue abierto.
5. **Voz** (fase 2) — nadie en español tiene voz tipo Martin.

---

## 5. Unit economics (la condición de existencia del negocio)

### Costo de Claude por usuario/mes (con prompt caching disciplinado y ruteo Haiku-first)

| Perfil | Msgs/día | Costo API/mes |
|---|---|---|
| Moderado | 50 | ~US$15–30 |
| Intensivo | 100 | ~US$35–60 |
| Muy intensivo | 150 | ~US$55–90 |

Sin caching, estos números se multiplican ×3–5. **El caching (prefijo congelado, sin timestamps en el system prompt) + ruteo agresivo a Haiku 4.5 es la diferencia entre margen y pérdida**, no una optimización posterior.

- **Voz:** STT casi gratis con Groq whisper-turbo (~US$0.60/usuario/mes). TTS premium (ElevenLabs) es el costo real: ~US$18–30/usuario/mes → debe ser add-on de pago o usar TTS económico por defecto.
- **WhatsApp** (si se usa): conversaciones de servicio gratis; recordatorios proactivos ~US$0.60/usuario/mes. Marginal.
- **Infra** (VPS Hetzner): <US$0.50/usuario/mes con ≥30 usuarios. Irrelevante frente al costo de Claude.

### Precios con margen sano

| Plan | Precio | CLP aprox. | Costo esperado | Margen bruto |
|---|---|---|---|---|
| **Base** | US$29/mes | ~$26.900 | US$12–18 | ~40–55% |
| **Pro** | US$59/mes | ~$54.600 | US$30–42 | ~30–50% |
| **Founding (beta)** | US$25–35/mes **vitalicio** | ~$23.000–32.500 | — | delgado (compras validación) |

Referencias: Martin US$30/mes anual · Lindy US$49,99+ · Claude Pro ~US$20 (ancla psicológica). **Bajo US$25/mes no hay negocio con usuarios intensivos.** US$29–59 es defendible y queda bajo Martin/Lindy.

**Reglas duras:** caps de uso desde el día 1 + enrutamiento Haiku-first. El usuario intensivo sin caps cuesta más que cualquier precio vendible. Evitar el "lifetime deal de pago único": con costos variables mensuales es una bomba de tiempo.

---

## 6. Arquitectura SaaS mínima viable (de instancia personal a multi-tenant)

Partiendo de lo que **ya está en producción** (bridges Telegram/WhatsApp, MCP de memoria, VPS+Coolify):

1. **Aislamiento de memoria por usuario** — `tenant_id` en el MCP de memoria + row-level security en Postgres; scoping de toda herramienta por identidad. Lo más crítico y lo primero.
2. **Identidad y ruteo** — mapeo canal→tenant; una instancia del agente por conversación con **presupuesto de tokens y rate-limit por usuario** (sin esto, un usuario intensivo quiebra el margen).
3. **Onboarding conversacional** — registro por el propio canal → link de pago → activación por webhook del PSP. Cero web app al inicio (landing + waitlist basta).
4. **Billing** (Stripe NO opera nativo en Chile, confirmado 2026):
   - **MercadoPago Chile** (~3.79%, suscripciones, liquida CLP) para clientes chilenos.
   - **Paddle / Lemon Squeezy** (merchant of record, 5% + US$0.50, cobra en USD, gestiona impuestos) para internacional.
   - Recomendación v1: **MercadoPago para CLP + Paddle para USD**, o solo Paddle si se simplifica.
5. **Operación** — panel de uso/costo por usuario (los datos ya vienen en `usage` de cada respuesta), kill-switch por usuario, backups, ToS + privacidad.
   - ⚠️ **Ley 21.719 de datos personales entra en plena vigencia en Chile el 1-dic-2026.** Un asistente con memoria personal está en el centro de esa ley — diseñar consentimiento, export y borrado desde el inicio.

### Esfuerzo estimado (1 persona + agentes IA de desarrollo)

| Bloque | Semanas full-time |
|---|---|
| Multi-tenant memoria + identidad + budgets | 1.5–2 |
| Onboarding + webhook de pago | 1 |
| Billing (MercadoPago o Paddle) | 1 |
| Observabilidad de costos + panel mínimo | 0.5–1 |
| Hardening + legal + landing/waitlist | 1 |
| **Total** | **5–6 semanas full-time ≈ 8–12 semanas al 50%** |

---

## 7. Estrategia de beta

- **Waitlist + invitación por tandas** (como Martin/Lindy/Superhuman): controla el costo de API y crea escasez.
- **Founding members de pago desde el día 1** con **precio congelado de por vida**. La beta gratis atrae curiosos que no retienen ni validan disposición a pagar. Cobrar US$25–35/mes filtra y financia la API.
- **Cohorte inicial: 10–25 usuarios** — el máximo al que puedes dar soporte conversacional directo mientras sigues facturando servicios. 20 usuarios × US$30 ≈ US$600/mes, que aproximadamente paga la API de la propia cohorte.

**Métricas de validación (en orden):**
1. Costo API por usuario/día y su p95 (define los caps).
2. Retención D7/D30 y mensajes/día (<3 msgs/día = churn próximo). **Objetivo D30 >30%.**
3. % de tráfico resuelto por Haiku (objetivo >70%).
4. Margen bruto por usuario, churn mensual (<5%), feedback cualitativo semanal.

⚠️ **Riesgo de churn de la categoría:** las apps de IA retienen *peor* que las no-IA (RevenueCat 2026). Antídotos: memoria que mejora el producto cada semana (switching cost), acciones proactivas (el asistente escribe primero: briefing diario, alertas), anclaje en workflows pagados por empresas (B2B2C), precio anual con descuento.

---

## 8. Open core: liberar el servidor de memoria MCP

**Recomendación: sí, hazlo** — el ROI (adquisición + programa Claude for OSS + credibilidad) supera el costo.

- **Pros:** distribución y credibilidad casi gratis en el ecosistema MCP; el programa **Claude for Open Source** (6 meses de Claude Max 20x gratis, ~US$1.200) subsidia tu propio desarrollo; issues/PRs de terceros endurecen el producto.
- **Contras:** ya existen muchos servidores de memoria MCP (la diferenciación no está ahí, pero tampoco pierdes foso al abrirlo); carga de mantenimiento; documentación de calidad exige ~1 semana.
- **Regla:** abre el **motor de memoria genérico** (MIT/Apache). Mantén cerrado lo que es el producto: prompts, orquestación multiagente, bridges, y el bundle de integraciones.

---

## 9. Qué recortar del alcance para la v1 (el "bundle salud/finanzas/todo")

El bundle horizontal (salud + finanzas + "acceso a todo lo físico y tecnológico") es la **visión a 2–3 años**, no la v1. Para la v1 cobrable:

1. **Fuera el bundle salud/finanzas/todo.** La v1 = **memoria + productividad conversacional** (recordatorios, notas, email/calendario). Salud y finanzas agregan superficie regulatoria (Ley 21.719, regulación financiera) que no quieres en la beta.
2. **Fuera la voz en v1** (o solo notas de voz entrantes vía Groq STT, que cuesta centavos; nada de TTS/interfaz de voz — ElevenLabs destruye el margen base).
3. **Un solo canal público: Telegram** (WhatsApp vetado para este uso; app/PWA como respaldo de soberanía).
4. **Sin web app** — landing + waitlist + onboarding en el canal + link de pago.
5. **Caps + Haiku-first desde el día 1.**

---

## 10. Números de la v1 razonable

- **20 founding members × US$29–35 ≈ US$600–700/mes (~CLP $560.000–650.000)** con costo API ~US$300–450.
- **No reemplaza los servicios: compra la validación.** Si a los 60 días la retención D30 supera ~60% y el costo API por usuario queda bajo el 50% del precio → hay negocio para escalar la cohorte y recién ahí agregar voz y verticales (salud/finanzas), y evaluar el pitch a YC/Platanus/Prosus con métricas reales.

---

## 11. Riesgos duros (resumen)

1. **Unit economics** — usuario intensivo sin caps > cualquier precio vendible. Mitigación: caps + Haiku-first + caching (condición de existencia).
2. **Dependencia de un proveedor de modelo y de la política de WhatsApp** — mitigación: canal-agnóstico, y arquitectura que permita cambiar de modelo.
3. **Competencia de Meta AI gratis / ChatGPT-Gemini con memoria** — ventana de diferenciación por ejecución+memoria en español: **12–24 meses**, no eterna. Jarvis no puede ganar en Q&A genérico; gana en actuar sobre *tus* sistemas con memoria auditable y privacidad.
4. **Tu tiempo** — 20 founding members son manejables; 100 no, mientras sigas en servicios. Sistematiza soporte con plantillas y auto-monitoreo.

---

## Fuentes
Precios API Anthropic (doc oficial, jun-2026) · Groq/Deepgram/ElevenLabs pricing pages · trymartin.com/pricing · ycombinator.com/companies/letterbook · lindy.ai/pricing · ohai.ai · luzia.com/blog · zapia.com/blog · prosus.com (From Apps to Agents, 2026) · generalcatalyst.com · cnbc.com (Meta AI 1B MAU) · techcrunch.com (veto WhatsApp 18-10-2025, Brasil 13-01-2026, Zuckerberg 02-07-2026) · tlt.com / truthonthemarket.com (antitrust Meta/WhatsApp) · revenuecat.com (State of Subscription Apps 2026) · a16z.com (State of Consumer AI 2025) · pasarelas Chile: MercadoPago/Flow/Paddle/Lemon Squeezy · Hetzner (ajuste 15-06-2026) · Ley 21.719 (Chile, vigencia 01-12-2026).
