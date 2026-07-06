# jarvis-whatsapp — Jarvis en WhatsApp (migración desde Telegram)

Puerta WhatsApp del Asesor Personal Unificado. **No reescribe el núcleo**: importa
`asesor-listener.py` (carriles chat/action/deep, memoria rodante, confirmación de
dos pasos, voz) y solo cambia el transporte a WhatsApp Business Cloud API (Meta).

```
Ariel (WhatsApp) ──► Meta Cloud API ──► POST https://whatsapp.nuvaus.com/webhook
                                              │ (firma verificada, ACK inmediato)
                                              ▼
                              jarvis-whatsapp.py (10.0.1.1:8932, systemd)
                                              │ importlib
                                              ▼
                              asesor-listener.py :: handle_text()
                              (mismo cerebro, misma memoria, mismos carriles)
                                              │
                              POST graph.facebook.com/v23.0/{PHONE_ID}/messages
```

**Costo: $0.** Desde el 1-jul-2025 Meta solo cobra mensajes de *plantilla*;
los mensajes libres dentro de la ventana de servicio de 24h (que se abre cada
vez que TÚ le escribes) son gratis. Un asistente reactivo de un solo usuario
no paga nada. (Verificado 06-jul-2026 contra la doc oficial de pricing.)

---

## Estado del despliegue

| Pieza | Estado | Quién |
|---|---|---|
| Servicio `jarvis-whatsapp.service` en vps-hub | ✅ desplegado | Claude (esta sesión) |
| DNS `whatsapp.nuvaus.com → 5.78.107.39` | ✅ creado vía Porkbun API | Claude |
| Traefik + certificado Let's Encrypt | ✅ | Claude |
| `WHATSAPP_VERIFY_TOKEN` en `.secrets` del VPS | ✅ generado | Claude |
| App en Meta for Developers + credenciales | ⬜ pendiente | **Ariel** (requiere tu login de Meta) |

## Lo que falta — pasos de Ariel en Meta (15-20 min, una vez)

1. **Crear la app**: [developers.facebook.com](https://developers.facebook.com) →
   My Apps → Create App → caso de uso **"Connect with customers through WhatsApp"**
   → crea (o elige) un portfolio de negocio (sirve Nuvaus SpA; **no** requiere
   verificación de negocio para este uso).
2. **API Setup** (WhatsApp → API Setup): Meta te genera un **número de prueba**
   gratis. Anota el **Phone number ID**.
   - En "Manage phone number list" agrega **tu número personal** como destinatario
     y confírmalo con el código OTP que te llega por WhatsApp (máx. 5 destinatarios;
     solo necesitas 1).
3. **Token permanente**: [business.facebook.com/latest/settings](https://business.facebook.com/latest/settings)
   → System users → Add → crea un usuario de sistema → Assign Assets: la app
   (full control) y la WABA (full control) → **Generate token** con permisos
   `whatsapp_business_messaging`, `whatsapp_business_management`,
   `business_management`, expiración **never**.
4. **App Secret**: App Dashboard → App settings → Basic → **App Secret** (Show).
5. **Cargar credenciales en el VPS** (desde tu Mac):
   ```bash
   ssh jarvis@vps-hub   # o: tailscale ssh jarvis@vps-hub
   cat >> ~/.claude/.secrets <<'EOF'
   WHATSAPP_ACCESS_TOKEN=<token del paso 3>
   WHATSAPP_PHONE_NUMBER_ID=<phone number id del paso 2>
   WHATSAPP_APP_SECRET=<app secret del paso 4>
   WHATSAPP_ALLOWED_WA_ID=569XXXXXXXX   # tu número, sin + ni espacios
   EOF
   sudo systemctl restart jarvis-whatsapp
   ```
6. **Configurar el webhook**: App Dashboard → WhatsApp → Configuration → Webhook:
   - Callback URL: `https://whatsapp.nuvaus.com/webhook`
   - Verify token: el valor de `grep WHATSAPP_VERIFY_TOKEN ~/.claude/.secrets` (en el VPS)
   - Verify and save → suscribe el campo **messages**.
7. **Probar**: mándale "hola" al número de prueba desde tu WhatsApp.
   Jarvis debería responder con toda su memoria y persona.
   Logs en vivo: `journalctl -u jarvis-whatsapp -f`.

### Nota sobre tu wa_id (paso 5)
Si no estás seguro del formato de tu número: deja `WHATSAPP_ALLOWED_WA_ID` sin
definir, mándale un mensaje al bot y mira el log — el servicio rechaza el mensaje
pero **imprime el wa_id exacto** para que lo copies. Fail-closed por diseño.

---

## Decisiones de diseño (y sus porqués)

- **Puente, no reescritura**: `handle_text()` del listener es transporte-agnóstico
  y encapsula 1.600 líneas probadas (ruteo 3 carriles, rodante, outbox proactivo,
  /nueva /cierre /inbox). El puente tiene ~500 líneas y cero dependencias (stdlib).
- **Confirmación de dos pasos portada 1:1** (`resolve_pending_wa`): el código de
  una acción irreversible lo verifica y ejecuta el puente vía `asesor-action.py`,
  **nunca el modelo** — paridad exacta con la doctrina del listener Telegram.
- **Fail-closed**: sin `WHATSAPP_APP_SECRET` se rechaza todo POST; sin
  `WHATSAPP_ALLOWED_WA_ID` se rechaza todo mensaje (y se loguea el wa_id).
- **Dedupe persistido**: Meta reintenta entregas hasta 7 días; se recuerdan los
  últimos 500 `message_id` en `~/.claude/claw/whatsapp-state.json`.
- **Ráfagas agrupadas**: mensajes seguidos en ~2 s se procesan como UN turno del
  núcleo (paridad con `process_group` de Telegram).
- **Notas de voz entrantes**: se transcriben con el mismo `asesor-stt.py`
  (faster-whisper del VPS) y entran al núcleo como texto marcado.
- **Voz saliente (regla espejo)**: implementada pero **apagada por defecto**
  (`JARVIS_WA_VOICE_OUT=1` en `.secrets` la activa). Actívala después de validar
  el flujo de texto.
- **Imágenes**: v2 (el carril deep con visión requiere descargar media y pasarla
  al núcleo — mismo patrón que voz, se agrega después de validar).

## Límites conocidos (léelos antes de apagar Telegram)

1. **Ventana de 24h / lado proactivo**: `jarvis-proactivo.py` (avisos push) hoy
   empuja por Telegram. En WhatsApp, fuera de la ventana de 24h solo se pueden
   enviar **plantillas aprobadas** (las utility cuestan centavos; dentro de
   ventana abierta son gratis). Opciones:
   - (a) dejar los avisos proactivos en Telegram por ahora (recomendado v1),
   - (b) crear una plantilla utility "aviso de Jarvis" y portar jarvis-proactivo,
   - (c) confiar en que le escribes a Jarvis a diario y la ventana casi siempre
     está abierta (el outbox ya drena avisos pendientes cuando escribes).
2. **Número de prueba de Meta**: la doc oficial no declara expiración, pero hay
   evidencia consistente de que exige **renovación cada ~90 días** desde el panel.
   Si Jarvis deja de responder, revisa el estado del número en API Setup.
   Plan definitivo: un segundo número dedicado (SIM/eSIM barata). **Nunca tu
   número personal**: un número registrado en Cloud API queda inutilizable para
   WhatsApp normal.
3. **"3 mejoras del día"** (`resolve_mejoras`): en v1 esa respuesta pasa por el
   modelo en vez del despacho determinista. Degradación menor; se porta en v2.
4. **Convivencia Telegram+WhatsApp**: ambos comparten estado (rodante/sesión).
   Funciona, pero úsalos de a uno. Cuando valides WhatsApp:
   `sudo systemctl disable --now jarvis-listener` (reversible cuando quieras).

## Operación

```bash
systemctl status jarvis-whatsapp          # estado
journalctl -u jarvis-whatsapp -f          # logs en vivo
curl -sS http://10.0.1.1:8932/salud       # health local (desde el VPS)
curl -sS https://whatsapp.nuvaus.com/salud # health público
# Auditoría de intercambios:
ls ~/.claude/logs/asesor/wa-*.jsonl
```

Re-desplegar tras cambios (desde un nodo del tailnet, en este repo):

```bash
./jarvis-whatsapp/deploy-whatsapp.sh
```
