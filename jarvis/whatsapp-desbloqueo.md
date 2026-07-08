# Desbloqueo de Jarvis en WhatsApp (ticket NV-NUV-0227)

**Fecha diagnóstico:** 2026-07-08 · **Estado:** servicio desplegado y sano, esperando credenciales de Meta.

## Diagnóstico

`https://whatsapp.nuvaus.com/salud` responde `ok: true`, pero la configuración de Meta Cloud API está vacía:

```json
{"ok": true, "servicio": "jarvis-whatsapp", "config": {
  "access_token": false,   ← falta
  "phone_id": false,       ← falta
  "app_secret": false,     ← falta
  "verify_token": true,    ✓ listo
  "allowed_wa_id": false,  ← falta
  "voice_out": false
}}
```

El puente (systemd en vps-hub, DNS + TLS OK, importa `handle_text()` del listener de Telegram) está 100% operativo. **Jarvis no está en WhatsApp por una sola razón: nunca se registró un número en Meta Cloud API.** No es un problema técnico del código.

## Pasos para desbloquear (en orden)

1. **Comprar SIM prepago dedicada** (cualquier operador chileno, ~CLP 3.000–5.000).
   - El número NO debe haber estado registrado en WhatsApp personal ni WhatsApp Business app. Si lo estuvo, eliminar esa cuenta primero (Ajustes → Cuenta → Eliminar cuenta) y esperar ~3 minutos.
   - Evitar números virtuales/VoIP: Meta rechaza la mayoría. SIM física = camino seguro.
   - Solo se necesita recibir UN SMS o llamada de verificación; después la SIM puede guardarse (el número queda anclado a la Cloud API, no al teléfono).
2. **Registrar el número** en [developers.facebook.com](https://developers.facebook.com) → app de Nuvaus → WhatsApp → API Setup → *Add phone number* → verificar por SMS. (Meta Business ya está verificado ✓, ese prerequisito está cumplido.)
   - Anotar el **`phone_number_id`** que aparece tras registrar.
3. **Generar token permanente**: Business Settings → System Users → crear/usar system user admin → *Generate token* seleccionando la app, con permisos `whatsapp_business_messaging` + `whatsapp_business_management`. (El token temporal del panel dura 24 h; no usarlo para producción.)
4. **Copiar el App Secret**: App Settings → Basic → App Secret.
5. **Configurar el webhook** en la app → WhatsApp → Configuration:
   - Callback URL: la ruta de webhook de `jarvis-whatsapp` (servida bajo `https://whatsapp.nuvaus.com`)
   - Verify token: el que ya está configurado en el servicio (`verify_token: true` en /salud)
   - Suscribir el campo **`messages`**.
6. **Cargar variables en vps-hub** (`.secrets` / unidad systemd del servicio) y reiniciar:
   - `WHATSAPP_ACCESS_TOKEN` (paso 3), `PHONE_ID` (paso 2), `APP_SECRET` (paso 4), `ALLOWED_WA_ID` (el wa_id del número personal de Ariel, formato `569XXXXXXXX`, para que solo Ariel pueda hablarle a Jarvis).
7. **Verificar**: `/salud` debe mostrar todo `true`; enviar "hola" desde el WhatsApp personal y confirmar respuesta de Jarvis.

## Costos de operación

- Meta cobra por conversación iniciada; las conversaciones de **servicio (respuestas a mensajes del usuario) son gratis e ilimitadas** desde nov 2024. Para el caso de uso de Jarvis (Ariel escribe → Jarvis responde) el costo de mensajería es **$0**.
- Costo real total: la SIM (una vez) + mantener el número activo según política del operador (recarga mínima esporádica).

## Nota para el futuro asistente de voz

`voice_out: false` en /salud sugiere que el puente ya contempla salida de voz. Al activar el número, considerar habilitar notas de voz (WhatsApp soporta audio en Cloud API) como primer paso hacia el asistente de voz (nombre por definir — decisión registrada en jarvis-memoria id 20).
