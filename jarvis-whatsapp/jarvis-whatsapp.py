#!/usr/bin/env python3
"""jarvis-whatsapp.py - Jarvis: puerta WhatsApp del asesor personal (migracion desde Telegram).

Puente de TRANSPORTE, no reescritura: importa el nucleo probado de
asesor-listener.py (handle_text / ask_jarvis / carriles chat|action|deep,
memoria rodante, outbox proactivo) y solo cambia la puerta de entrada/salida
a WhatsApp Business Cloud API (Meta).

Flujo:
  Meta -> POST /webhook (firma X-Hub-Signature-256 verificada, ACK 200 inmediato)
       -> cola en memoria -> worker serial: nucleo -> POST graph /messages.

Seguridad (hereda doctrina SPEC-Asesor-Personal-Unificado):
- Solo mensajes de WHATSAPP_ALLOWED_WA_ID; el resto se loguea y se ignora.
  Si la variable falta, se RECHAZA todo y se loguea el wa_id entrante para
  que Ariel lo copie a .secrets (bootstrap sin adivinar el numero).
- Firma HMAC-SHA256 obligatoria con WHATSAPP_APP_SECRET; sin secreto
  configurado se rechaza todo POST (fail-closed).
- Confirmacion de dos pasos para acciones irreversibles portada 1:1: el
  codigo lo verifica y ejecuta ESTE proceso via asesor-action.py, nunca el
  modelo (paridad con resolve_pending del listener Telegram).
- Bind solo en la red interna de Coolify (10.0.1.1); TLS lo termina Traefik
  en whatsapp.nuvaus.com. Dedupe de message_id persistido (Meta reintenta).
- Audit JSONL por intercambio en ~/.claude/logs/asesor/wa-YYYY-MM-DD.jsonl.

Variables en ~/.claude/.secrets:
  WHATSAPP_ACCESS_TOKEN      token permanente (system user de Meta Business)
  WHATSAPP_PHONE_NUMBER_ID   id numerico del telefono en la app de Meta
  WHATSAPP_APP_SECRET        App Secret de la app (verifica firma del webhook)
  WHATSAPP_VERIFY_TOKEN      token de verificacion del webhook (lo genera deploy)
  WHATSAPP_ALLOWED_WA_ID     wa_id de Ariel (ej: 569XXXXXXXX, sin +)
  WHATSAPP_GRAPH_VERSION     opcional, default v23.0
  JARVIS_WA_VOICE_OUT        opcional, '1' activa respuesta hablada espejo

Uso:
  python3 jarvis-whatsapp.py            # daemon (systemd jarvis-whatsapp.service)
  python3 jarvis-whatsapp.py --salud    # chequeo local de configuracion
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import importlib.util
import json
import mimetypes
import os
import queue
import sys
import threading
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

HOME = Path.home()
SECRETS = HOME / '.claude' / '.secrets'
SCRIPTS = HOME / 'repos' / 'nuvaus' / 'scripts'
LISTENER = SCRIPTS / 'asesor-listener.py'
STATE_DIR = HOME / '.claude' / 'claw'
WA_STATE = STATE_DIR / 'whatsapp-state.json'
VOICE_TMP = STATE_DIR / 'wa-voice'

TZ = ZoneInfo('America/Santiago')
BIND_HOST = os.environ.get('JARVIS_WA_BIND', '10.0.1.1')
BIND_PORT = int(os.environ.get('JARVIS_WA_PORT', '8932'))
WA_TEXT_MAX = 4000            # margen bajo el limite real de WhatsApp (4096)
VOICE_MAX_SECONDS = 300       # paridad con el listener Telegram
DEDUPE_KEEP = 500             # message_id recordados contra reentregas de Meta
GROUP_DRAIN_SECONDS = 2.0     # ventana para agrupar rafagas en UN turno del nucleo

# ---------------------------------------------------------------- secretos


def read_secrets() -> dict:
    valores = {}
    if not SECRETS.exists():
        raise RuntimeError(f'.secrets no existe en {SECRETS}')
    for line in SECRETS.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            valores[k.strip()] = v.strip()
    return valores


SEC = read_secrets()
ACCESS_TOKEN = SEC.get('WHATSAPP_ACCESS_TOKEN', '')
PHONE_ID = SEC.get('WHATSAPP_PHONE_NUMBER_ID', '')
APP_SECRET = SEC.get('WHATSAPP_APP_SECRET', '')
VERIFY_TOKEN = SEC.get('WHATSAPP_VERIFY_TOKEN', '')
ALLOWED_WA_ID = SEC.get('WHATSAPP_ALLOWED_WA_ID', '')
GRAPH_VER = SEC.get('WHATSAPP_GRAPH_VERSION', 'v23.0')
VOICE_OUT = SEC.get('JARVIS_WA_VOICE_OUT', os.environ.get('JARVIS_WA_VOICE_OUT', '')) == '1'
GRAPH = f'https://graph.facebook.com/{GRAPH_VER}'


def log(msg: str) -> None:
    print(f'[{datetime.now(TZ).isoformat(timespec="seconds")}] {msg}', flush=True)


# ---------------------------------------------------------------- nucleo (asesor-listener como modulo)

_CORE = None


def core():
    """Carga asesor-listener.py una sola vez (nombre con guion, via importlib).

    Mismo patron que usa el propio listener para jarvis-mejoras.py. El modulo
    define solo constantes y funciones a nivel de import (main() esta guardado),
    asi que importarlo no arranca el polling de Telegram.
    """
    global _CORE
    if _CORE is None:
        spec = importlib.util.spec_from_file_location('asesor_listener', LISTENER)
        mod = importlib.util.module_from_spec(spec)
        sys.modules['asesor_listener'] = mod
        spec.loader.exec_module(mod)
        _CORE = mod
    return _CORE


def audit(entry: dict) -> None:
    entry = {'ts': datetime.now(TZ).isoformat(timespec='seconds'),
             'canal': 'whatsapp', **entry}
    d = core().AUDIT_DIR
    d.mkdir(parents=True, exist_ok=True)
    path = d / f'wa-{datetime.now(TZ).date().isoformat()}.jsonl'
    with path.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + '\n')


# ---------------------------------------------------------------- estado WhatsApp (dedupe)


def wa_state_load() -> dict:
    try:
        return json.loads(WA_STATE.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def wa_state_save(st: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = WA_STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(st, ensure_ascii=False), encoding='utf-8')
    tmp.replace(WA_STATE)


def already_seen(msg_id: str, st: dict) -> bool:
    vistos = st.setdefault('seen_ids', [])
    if msg_id in vistos:
        return True
    vistos.append(msg_id)
    if len(vistos) > DEDUPE_KEEP:
        st['seen_ids'] = vistos[-DEDUPE_KEEP:]
    wa_state_save(st)
    return False


# ---------------------------------------------------------------- Cloud API (salida)


def _graph_post(path: str, payload: dict) -> dict:
    req = Request(f'{GRAPH}/{path}',
                  data=json.dumps(payload).encode('utf-8'),
                  headers={'Authorization': f'Bearer {ACCESS_TOKEN}',
                           'Content-Type': 'application/json'})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def wa_send_text(to: str, text: str) -> None:
    """Envia texto plano, troceado bajo el limite de WhatsApp."""
    text = text.strip() or '(respuesta vacia)'
    trozos, resto = [], text
    while resto:
        if len(resto) <= WA_TEXT_MAX:
            trozos.append(resto)
            break
        corte = resto.rfind('\n', 0, WA_TEXT_MAX)
        if corte < WA_TEXT_MAX // 2:
            corte = WA_TEXT_MAX
        trozos.append(resto[:corte])
        resto = resto[corte:].lstrip('\n')
    for t in trozos:
        _graph_post(f'{PHONE_ID}/messages', {
            'messaging_product': 'whatsapp', 'recipient_type': 'individual',
            'to': to, 'type': 'text', 'text': {'preview_url': False, 'body': t},
        })


def wa_mark_read_typing(msg_id: str) -> None:
    """Marca leido + indicador 'escribiendo...' (mejor UX; fallar no es grave)."""
    try:
        _graph_post(f'{PHONE_ID}/messages', {
            'messaging_product': 'whatsapp', 'status': 'read',
            'message_id': msg_id, 'typing_indicator': {'type': 'text'},
        })
    except Exception as exc:  # noqa: BLE001 — UX opcional, jamas corta el flujo
        log(f'typing/read fallo (ignorado): {exc}')


def wa_upload_media(path: Path, mime: str) -> str:
    """Sube un archivo (multipart manual, stdlib) y devuelve el media id."""
    boundary = uuid.uuid4().hex
    data = path.read_bytes()
    cuerpo = b''.join([
        f'--{boundary}\r\nContent-Disposition: form-data; name="messaging_product"\r\n\r\nwhatsapp\r\n'.encode(),
        f'--{boundary}\r\nContent-Disposition: form-data; name="type"\r\n\r\n{mime}\r\n'.encode(),
        (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
         f'filename="{path.name}"\r\nContent-Type: {mime}\r\n\r\n').encode(),
        data, f'\r\n--{boundary}--\r\n'.encode(),
    ])
    req = Request(f'{GRAPH}/{PHONE_ID}/media', data=cuerpo, headers={
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': f'multipart/form-data; boundary={boundary}',
    })
    with urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8'))['id']


def wa_send_voice(to: str, path: Path) -> None:
    media_id = wa_upload_media(path, 'audio/ogg')
    _graph_post(f'{PHONE_ID}/messages', {
        'messaging_product': 'whatsapp', 'recipient_type': 'individual',
        'to': to, 'type': 'audio', 'audio': {'id': media_id},
    })


def wa_download_media(media_id: str) -> Path:
    """Resuelve la URL del media y lo baja a un archivo temporal."""
    req = Request(f'{GRAPH}/{media_id}',
                  headers={'Authorization': f'Bearer {ACCESS_TOKEN}'})
    with urlopen(req, timeout=30) as resp:
        info = json.loads(resp.read().decode('utf-8'))
    ext = mimetypes.guess_extension((info.get('mime_type') or '').split(';')[0]) or '.bin'
    VOICE_TMP.mkdir(parents=True, exist_ok=True)
    destino = VOICE_TMP / f'{media_id}{ext}'
    req2 = Request(info['url'], headers={'Authorization': f'Bearer {ACCESS_TOKEN}'})
    with urlopen(req2, timeout=60) as resp:
        destino.write_bytes(resp.read())
    return destino


# ---------------------------------------------------------------- voz entrante (STT, paridad Telegram)


def transcribe_wa_voice(media_id: str) -> str:
    import subprocess
    c = core()
    local = wa_download_media(media_id)
    try:
        proc = subprocess.run(
            [str(c.STT_PYTHON), str(c.STT_SCRIPT), str(local)],
            capture_output=True, text=True, timeout=c.STT_TIMEOUT,
        )
        if proc.returncode != 0:
            raise RuntimeError(f'stt rc={proc.returncode}: {proc.stderr.strip()[:300]}')
        return proc.stdout.strip()
    finally:
        local.unlink(missing_ok=True)


# ---------------------------------------------------------------- confirmacion de dos pasos (paridad resolve_pending)


def resolve_pending_wa(texto: str, to: str) -> dict | None:
    """Version WhatsApp de resolve_pending: misma logica determinista, otro transporte.

    El codigo de confirmacion de una accion irreversible lo verifica y ejecuta
    ESTE proceso (via asesor-action.py); jamas pasa por el modelo.
    """
    c = core()
    aa = c.action_mod()
    pending = aa.load_pending()
    if not pending:
        return None

    if aa.pending_is_expired(pending):
        aa.clear_pending()
        if aa.confirmation_matches(texto, pending):
            wa_send_text(to, 'Ese codigo ya vencio (pasaron mas de '
                             f'{aa.EXPIRY_MINUTES} minutos). Si todavia quieres '
                             'hacerlo, pidemelo otra vez y te doy uno nuevo.')
            return {'handled': True}
        return {'handled': False, 'prefix': ''}

    if aa.confirmation_matches(texto, pending):
        outcome = aa.execute_pending(texto)
        wa_send_text(to, outcome.get('reply', 'Listo.'))
        audit({'event': 'pending_executed', 'action': pending.get('action'),
               'ok': bool(outcome.get('ok'))})
        return {'handled': True}

    aa.clear_pending()
    audit({'event': 'pending_cancelled', 'action': pending.get('action'),
           'reason': 'no_match'})
    return {'handled': False,
            'prefix': 'Cancele la accion pendiente (no recibi el codigo exacto).\n\n'}


# ---------------------------------------------------------------- procesamiento de turnos

COLA: 'queue.Queue[dict]' = queue.Queue()


def process_turn(mensajes: list[dict]) -> None:
    """Procesa 1..N mensajes acumulados como UN turno del nucleo (paridad process_group)."""
    c = core()
    to = mensajes[-1]['from']
    t0 = time.time()

    items, voice_total = [], 0
    for m in mensajes:
        tipo = m.get('type')
        if tipo == 'text':
            items.append((False, (m.get('text') or {}).get('body', '').strip()))
        elif tipo == 'audio':
            audio = m.get('audio') or {}
            try:
                spoken = transcribe_wa_voice(audio['id'])
                voice_total += 1
            except Exception as exc:  # noqa: BLE001
                log(f'stt whatsapp fallo: {exc}')
                spoken = ''
            items.append((True, spoken))
        elif tipo in ('image', 'document', 'video', 'sticker'):
            items.append((False, '(por ahora en WhatsApp manejo texto y notas de voz; '
                                 'las imagenes vienen en la proxima fase - describemela '
                                 'o mandala por otro canal)'))
        else:
            items.append((False, f'(mensaje {tipo} no procesable)'))

    had_voice = voice_total > 0
    text_items = [(v, t) for (v, t) in items if t]
    if not text_items:
        wa_send_text(to, 'No distingui voz en la nota. ¿La repites o me escribes?')
        audit({'event': 'voice_empty', 'msgs': len(mensajes)})
        return

    if len(text_items) == 1:
        es_voz, contenido = text_items[0]
        base = (f'[Nota de voz transcrita — tolera errores foneticos en '
                f'nombres] {contenido}') if es_voz else contenido
    else:
        lineas = [f'{i}.{" (nota de voz)" if v else ""} {t}'
                  for i, (v, t) in enumerate(text_items, 1)]
        base = ('Enviaste estos mensajes seguidos mientras yo procesaba — '
                'respondeles al CONJUNTO en una sola respuesta coherente; el '
                'mas reciente manda y tolera errores foneticos en las notas '
                'de voz:\n' + '\n'.join(lineas))

    # Accion irreversible pendiente: resolucion determinista ANTES del nucleo.
    pending_outcome = resolve_pending_wa(base, to)
    if pending_outcome and pending_outcome.get('handled'):
        return
    cancel_prefix = (pending_outcome or {}).get('prefix', '')

    wa_mark_read_typing(mensajes[-1]['id'])

    state = c.load_state()
    try:
        reply, meta = c.handle_text(base, state)
    except Exception as exc:  # noqa: BLE001
        log(f'nucleo fallo: {exc}')
        wa_send_text(to, 'No pude procesar eso. Detalle en journalctl -u jarvis-whatsapp.')
        audit({'event': 'core_failed', 'in': base[:200], 'error': str(exc)[:300]})
        return

    if cancel_prefix:
        reply = cancel_prefix + reply

    # Regla espejo (opcional, JARVIS_WA_VOICE_OUT=1): nota de voz -> respuesta hablada.
    tts_backend, sent_text = None, False
    if had_voice and VOICE_OUT:
        try:
            voice_path, tts_backend = c.make_voice_reply(reply)
            if voice_path:
                wa_send_voice(to, voice_path)
                voice_path.unlink(missing_ok=True)
        except Exception as exc:  # noqa: BLE001
            log(f'voz saliente fallo (sigue texto): {exc}')
            tts_backend = None
    if not sent_text:
        wa_send_text(to, reply)

    audit({'event': 'exchange', 'msgs': len(mensajes), 'in': base[:500],
           'out_len': len(reply), 'duration_s': round(time.time() - t0, 1),
           'voice_msgs': voice_total or None, 'tts_backend': tts_backend,
           **(meta or {})})


def worker() -> None:
    while True:
        primero = COLA.get()
        lote = [primero]
        fin = time.time() + GROUP_DRAIN_SECONDS
        while time.time() < fin:
            try:
                lote.append(COLA.get(timeout=max(0.05, fin - time.time())))
            except queue.Empty:
                break
        try:
            process_turn(lote)
        except Exception as exc:  # noqa: BLE001 — el worker no puede morir
            log(f'process_turn exploto: {exc}')
            audit({'event': 'worker_error', 'error': str(exc)[:300]})


# ---------------------------------------------------------------- webhook HTTP


class Handler(BaseHTTPRequestHandler):
    server_version = 'jarvis-whatsapp/1.0'

    def _plain(self, code: int, body: str) -> None:
        data = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):  # journald ya tiene timestamp
        log(f'http {self.address_string()} {fmt % args}')

    def do_GET(self):  # noqa: N802
        url = urlparse(self.path)
        if url.path == '/salud':
            estado = {'ok': True, 'servicio': 'jarvis-whatsapp',
                      'config': {'access_token': bool(ACCESS_TOKEN),
                                 'phone_id': bool(PHONE_ID),
                                 'app_secret': bool(APP_SECRET),
                                 'verify_token': bool(VERIFY_TOKEN),
                                 'allowed_wa_id': bool(ALLOWED_WA_ID),
                                 'voice_out': VOICE_OUT}}
            self._plain(200, json.dumps(estado, ensure_ascii=False))
            return
        if url.path == '/webhook':
            q = parse_qs(url.query)
            modo = q.get('hub.mode', [''])[0]
            token = q.get('hub.verify_token', [''])[0]
            challenge = q.get('hub.challenge', [''])[0]
            if modo == 'subscribe' and VERIFY_TOKEN and hmac.compare_digest(token, VERIFY_TOKEN):
                log('webhook verificado por Meta (GET subscribe)')
                self._plain(200, challenge)
            else:
                log('webhook GET rechazado (verify_token no coincide)')
                self._plain(403, 'forbidden')
            return
        self._plain(404, 'not found')

    def do_POST(self):  # noqa: N802
        if urlparse(self.path).path != '/webhook':
            self._plain(404, 'not found')
            return
        largo = int(self.headers.get('Content-Length', 0))
        cuerpo = self.rfile.read(largo) if largo else b''

        if not APP_SECRET:
            log('POST rechazado: WHATSAPP_APP_SECRET no configurado (fail-closed)')
            self._plain(403, 'forbidden')
            return
        firma = self.headers.get('X-Hub-Signature-256', '')
        esperada = 'sha256=' + hmac.new(APP_SECRET.encode(), cuerpo, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(firma, esperada):
            log('POST rechazado: firma X-Hub-Signature-256 invalida')
            self._plain(403, 'forbidden')
            return

        # ACK inmediato: Meta reintenta si no ve 200 rapido.
        self._plain(200, 'ok')

        try:
            payload = json.loads(cuerpo.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            log('payload no-JSON ignorado')
            return

        st = wa_state_load()
        for entry in payload.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                for m in value.get('messages', []):
                    wa_id = m.get('from', '')
                    if not ALLOWED_WA_ID:
                        log(f'WHATSAPP_ALLOWED_WA_ID no configurado — ignorando '
                            f'mensaje de {wa_id}. Agrega esa variable a .secrets '
                            f'con este valor si eres tu.')
                        audit({'event': 'sin_allowlist', 'from': wa_id})
                        continue
                    if wa_id != ALLOWED_WA_ID:
                        log(f'mensaje de wa_id NO autorizado ignorado: {wa_id}')
                        audit({'event': 'rechazado', 'from': wa_id})
                        continue
                    if already_seen(m.get('id', ''), st):
                        continue
                    COLA.put(m)


# ---------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--salud', action='store_true',
                        help='muestra el estado de configuracion y sale')
    args = parser.parse_args()

    if args.salud:
        print(json.dumps({
            'listener_nucleo': LISTENER.exists(),
            'access_token': bool(ACCESS_TOKEN), 'phone_id': bool(PHONE_ID),
            'app_secret': bool(APP_SECRET), 'verify_token': bool(VERIFY_TOKEN),
            'allowed_wa_id': bool(ALLOWED_WA_ID), 'voice_out': VOICE_OUT,
            'bind': f'{BIND_HOST}:{BIND_PORT}',
        }, indent=2, ensure_ascii=False))
        return 0

    if not LISTENER.exists():
        log(f'FATAL: no encuentro el nucleo en {LISTENER}')
        return 1
    core()  # carga temprana: si el nucleo no importa, mejor morir ahora
    faltan = [n for n, v in [('WHATSAPP_ACCESS_TOKEN', ACCESS_TOKEN),
                             ('WHATSAPP_PHONE_NUMBER_ID', PHONE_ID),
                             ('WHATSAPP_APP_SECRET', APP_SECRET),
                             ('WHATSAPP_ALLOWED_WA_ID', ALLOWED_WA_ID)] if not v]
    if faltan:
        log(f'AVISO: faltan en .secrets: {", ".join(faltan)} — el webhook '
            f'verifica (GET) pero no procesara mensajes hasta completarlas.')

    threading.Thread(target=worker, daemon=True, name='worker').start()
    srv = ThreadingHTTPServer((BIND_HOST, BIND_PORT), Handler)
    log(f'jarvis-whatsapp escuchando en {BIND_HOST}:{BIND_PORT} '
        f'(graph {GRAPH_VER}, voz saliente {"ON" if VOICE_OUT else "off"})')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
