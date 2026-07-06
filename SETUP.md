# SETUP — Instalación y Configuración (macOS)

Guía completa para instalar Nuvaus Automation en tu Mac.

## Requisitos

- **macOS 12+** (Monterey o posterior)
- **Python 3.8+** — viene con las Command Line Tools de Apple. Si al correr
  `python3 --version` te pide instalar algo, acepta o ejecuta:
  ```bash
  xcode-select --install
  ```
- **git** — incluido en las mismas Command Line Tools.

## Paso 1: Clonar el repositorio

```bash
cd ~
git clone -b claude/washing-machine-price-comparison-Jpfol https://github.com/Nuvaus/nuvaus-automation.git
cd nuvaus-automation
```

> El `-b ...` descarga directamente la rama que contiene la versión macOS.
> Cuando esa rama se fusione a `main` (vía Pull Request), bastará el clone normal.

> Si git te pide usuario/contraseña: GitHub ya no acepta contraseñas por
> terminal. Lo más simple es instalar [GitHub Desktop](https://desktop.github.com)
> y clonar desde ahí, o crear un *Personal Access Token* en
> github.com → Settings → Developer settings → Tokens y usarlo como contraseña.

Si ya está clonado, actualizar:
```bash
cd ~/nuvaus-automation
git fetch origin
git checkout claude/washing-machine-price-comparison-Jpfol
git pull
```

## Paso 2: Ejecutar el setup automático

```bash
bash scripts/setup-mac.sh
```

Esto hace todo por ti:
1. Crea la estructura de carpetas en `~/Desktop/Nuvaus`
2. Verifica tus secrets (`~/.claude/.secrets`)
3. Corre un **DRY RUN** de prueba del File Manager

## Paso 3: Configurar secrets (opcional)

El archivo `~/.claude/.secrets` guarda las API keys (formato `CLAVE=valor`, una por línea):

```bash
mkdir -p ~/.claude && touch ~/.claude/.secrets
open -e ~/.claude/.secrets   # lo abre en TextEdit
```

Contenido según lo que uses:
```
NOTION_API_KEY=ntn_xxxxxxxx        # sincronización con Notion
SCRAPER_API_KEY=xxxxxxxxxxxx       # fallback anti-bot del monitor de precios
ML_ACCESS_TOKEN=APP_USR-xxxx       # opcional, API MercadoLibre
```

Sin secrets, todo funciona igual — solo se desactivan Notion y el fallback de precios.

## Paso 4: Probar a mano

```bash
cd ~/nuvaus-automation

# Ver qué haría, sin mover nada:
python3 scripts/file-manager.py --dry-run

# Ejecutar de verdad:
python3 scripts/file-manager.py

# Correr la suite de tests (no toca tus archivos):
python3 scripts/run-tests.py

# Monitor de precios:
python3 scripts/price-fetcher.py --dry-run
```

Ver logs:
```bash
tail -20 logs/file-manager.log
```

## Paso 5: Automatizar con launchd

`launchd` es el equivalente en macOS del Task Scheduler de Windows.
Un solo comando instala los dos agentes:

```bash
bash scripts/setup-mac.sh --install-agents
```

Esto programa:
| Agente | Frecuencia |
|--------|-----------|
| `com.nuvaus.file-manager` | Cada 15 minutos (y al iniciar sesión) |
| `com.nuvaus.price-watch` | Todos los días a las 9:00 |

Verificar que están corriendo:
```bash
launchctl list | grep nuvaus
```

> **Permiso de macOS:** la primera vez, macOS puede preguntar si Python puede
> acceder a las carpetas Descargas/Escritorio. Acepta, o ve a
> **Ajustes del Sistema → Privacidad y seguridad → Archivos y carpetas** y
> habilita Terminal/python3 ahí.

Desinstalar la automatización:
```bash
bash scripts/setup-mac.sh --uninstall-agents
```

## Paso 6: Prueba end-to-end

```bash
# Crear un archivo de prueba en Descargas
echo "test" > ~/Downloads/NV-PROP-CECA-test.pdf

# Esperar 60s (guard de archivos recientes) y ejecutar
sleep 61 && python3 scripts/file-manager.py

# Verificar que se movió y renombró
ls ~/Desktop/Nuvaus/propuestas
```

Deberías ver `NV-PROP-CECA-<fecha>.pdf`.

## Troubleshooting

### "python3: command not found"
```bash
xcode-select --install
```

### El agente launchd no corre
```bash
# Ver estado (el segundo número es el último código de salida; 0 = OK)
launchctl list | grep nuvaus

# Ver errores
cat logs/launchd-file-manager.log

# Recargar
bash scripts/setup-mac.sh --uninstall-agents
bash scripts/setup-mac.sh --install-agents
```

### Los archivos no se mueven
1. Ejecuta con `--dry-run` para ver qué detecta
2. ¿El nombre coincide con algún patrón de `config/rules.json`?
3. Los archivos con menos de 60 segundos se saltan (evita agarrar descargas
   a medias) — espera un minuto y reintenta
4. Revisa `logs/file-manager.log`

### "NOTION_API_KEY no encontrada"
```bash
grep NOTION_API_KEY ~/.claude/.secrets || echo "falta agregarla"
```

### Rutas personalizadas
Si tu carpeta Nuvaus no está en `~/Desktop/Nuvaus`, crea
`config/paths.local.json` (git lo ignora) con tus rutas:
```json
{
  "nuvaus_base": "~/Documents/Nuvaus",
  "monitored_downloads": "~/Downloads"
}
```

## Desinstalación completa

```bash
bash scripts/setup-mac.sh --uninstall-agents
rm -rf ~/nuvaus-automation
# Las carpetas de ~/Desktop/Nuvaus con tus archivos NO se tocan
```

## Siguiente paso

Ver `RULES.md` para personalizar reglas de clasificación y
`PRICE-WATCH.md` para el monitor de precios.

---

**¿Problemas?** Ver README.md o contactar ariel@nuvaus.com
