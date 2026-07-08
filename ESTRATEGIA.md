# Nuvaus — Estrategia y sistema de oportunidades

Documento índice. Consolida el análisis del 8-jul-2026 sobre (a) llevar la facturación de Nuvaus a CLP 1M/mes rápido, (b) convertir Jarvis en producto SaaS estrella, (c) el radar automático de oportunidades, y (d) desbloquear WhatsApp.

---

## Mapa de documentos

| Documento | Qué contiene |
|---|---|
| [`nuvaus/plan-facturacion-1M.md`](nuvaus/plan-facturacion-1M.md) | **Caja rápida.** Ruta a CLP 1M/mes en 2–6 semanas: 3 paquetes de servicios, precios reales del mercado chileno, canales de venta y plan semana a semana. |
| [`jarvis/producto-saas-estrategia.md`](jarvis/producto-saas-estrategia.md) | **Producto.** Jarvis como SaaS: mercado y competidores, unit economics, posicionamiento ("chief of staff en español"), arquitectura multi-tenant, beta, open core, veredicto. |
| [`jarvis/radar-oportunidades.md`](jarvis/radar-oportunidades.md) | **Radar.** Oportunidades vigentes de capital, ahorro y proyectos, verificadas. Se regenera solo cada lunes (ver "Loop" abajo). |
| [`jarvis/whatsapp-desbloqueo.md`](jarvis/whatsapp-desbloqueo.md) | **WhatsApp.** Diagnóstico del ticket NV-NUV-0227 y pasos para activar el número en Meta Cloud API. |

---

## La tesis en tres capas

**1. Ahora (semanas 1–6): caja con servicios.**
Nuvaus vende automatización productizada a pymes chilenas. El mercado ya paga CLP 250k–600k de setup + CLP 35k–90k/mes. Con agentes Claude como fuerza de desarrollo, Nuvaus entrega en 7 días lo que la competencia entrega en 3–4 semanas. Meta: 2 setups + 3–4 mensualidades = CLP 1M/mes. → `nuvaus/plan-facturacion-1M.md`.

**2. En paralelo (semanas 2–8): producto Jarvis v1.**
El asistente interno se vuelve producto: "chief of staff de IA en español" para profesionales/pymes de LatAm. Foso = memoria unificada MCP propia. Beta de 20 founding members de pago (US$29–35/mes vitalicio) que financian y validan. NO WhatsApp-first (canal vetado por Meta): Telegram + app + voz. → `jarvis/producto-saas-estrategia.md`.

**3. Con el tiempo (6–18 meses): la apuesta que mueve la aguja.**
Si la beta retiene (D30 >30–60%, margen sano), se escala la cohorte, se agregan verticales (voz, finanzas, salud) y el bundle multiagente "acceso a todo". Recién ahí tiene sentido capital de riesgo (YC/Platanus/Prosus) con métricas reales. El servidor de memoria MCP se libera open source → adquisición + programa Claude for OSS (6 meses de Max gratis).

**Regla de oro:** el SaaS NO reemplaza los servicios hasta estar validado. Servicios = combustible; producto = cohete. No enciendas el cohete con el estanque vacío.

---

## Loop automático: Radar de Oportunidades

Se creó una **Routine semanal** (lunes 09:00 hora de Chile) que ejecuta un workflow multiagente Fable 5/Opus:
1. Escanea 5 dimensiones (capital público chileno, aceleradoras/VC, créditos y programas gratis, canales de proyectos, ahorros del stack).
2. Verifica cada hallazgo de forma adversarial contra la fuente oficial (vigencia, deadline real, si Nuvaus califica).
3. Compara contra la memoria de Jarvis y se queda solo con lo nuevo.
4. Crea eventos en Google Calendar (prefijo `[Radar]`) para deadlines nuevos, con sesión de trabajo agendada con margen antes del cierre.
5. Actualiza `jarvis/radar-oportunidades.md`, commit + push.
6. Registra el resumen en la bitácora de Jarvis (= notificación a Ariel).

Así el radar "no descansa": cada semana barre el mercado y solo interrumpe cuando hay algo accionable nuevo.

---

## Nota de branding

"Jarvis" es nombre de trabajo. El asistente evolucionará a **voz** y su nombre definitivo se decide más adelante (registrado en jarvis-memoria id 20). No fijar el nombre en marca/producto todavía.
