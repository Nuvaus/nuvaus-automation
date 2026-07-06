#!/usr/bin/env python3
# ===================================================================
# TESTS — Nuvaus File Manager (Python)
# ===================================================================
# Suite de verificación con carpetas temporales: no toca tus archivos
# reales ni requiere red. Ejecutar:
#   python3 scripts/run-tests.py
# ===================================================================

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
import unicodedata
import unittest
from unittest import mock

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Importar file-manager.py (nombre con guion → importlib)
spec = importlib.util.spec_from_file_location("fm", os.path.join(SCRIPT_DIR, "file-manager.py"))
fm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fm)


def make_cfg(tmp, min_age=0):
    """Config de prueba apuntando a carpetas temporales."""
    return {
        "base": os.path.join(tmp, "Nuvaus"),
        "downloads": os.path.join(tmp, "Downloads"),
        "rules": [
            {
                "id": "propuestas",
                "name": "Propuestas (PDF)",
                "patterns": ["NV-PROP-*", "NV-QUOT-*"],
                "extensions": [".pdf"],
                "destination": "propuestas",
                "rename_pattern": "NV-PROP-{CLIENT}-{DD-MM-YYYY}",
                "notify_notion": False,
            },
            {
                "id": "invoices",
                "name": "Facturas",
                "patterns": ["factura*", "invoice*"],
                "extensions": [".pdf", ".xlsx"],
                "destination": "clientes/{CLIENT}/invoices",
                "rename_pattern": "{CLIENT}-{YYYY-MM-DD}-{FILENAME}",
                "notify_notion": False,
            },
            {
                "id": "articulos",
                "name": "Artículos",
                "patterns": ["artículo*"],
                "extensions": [".pdf"],
                "destination": "descargas-ordenadas/artículos",
                "rename_pattern": "{YYYY-MM-DD}-{FILENAME}",
                "notify_notion": False,
            },
            {
                "id": "reportes",
                "name": "Reportes",
                "patterns": ["reporte*"],
                "extensions": [".json"],
                "destination": "temp/reportes",
                "rename_pattern": "{YYYY-MM-DD}-{FILENAME}",
                "notify_notion": False,
                "auto_delete_days": 30,
            },
        ],
        "clients": [
            {"code": "CECA", "name": "CECA Salud", "folder": "ceca", "country": "CL"},
            {"code": "AJJ", "name": "AJJ Remodelaciones", "folder": "ajj", "country": "US"},
        ],
        "gs": {
            "archive_propuestas_after_days": 180,
            "min_file_age_seconds": min_age,
            "skip_existing_files": False,
        },
    }


def touch(path, content="x", mtime=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    if mtime is not None:
        os.utime(path, (mtime, mtime))


class TestMatching(unittest.TestCase):
    def setUp(self):
        self.cfg = make_cfg("/tmp/x")

    def test_rule_match_basic(self):
        rule = self.cfg["rules"][0]
        self.assertTrue(fm.rule_matches("NV-PROP-CECA-v2.pdf", rule))
        self.assertFalse(fm.rule_matches("NV-PROP-CECA.docx", rule))  # ext incorrecta
        self.assertFalse(fm.rule_matches("otro-archivo.pdf", rule))

    def test_rule_match_case_insensitive(self):
        rule = self.cfg["rules"][1]
        self.assertTrue(fm.rule_matches("Factura-CECA.pdf", rule))
        self.assertTrue(fm.rule_matches("INVOICE-final.xlsx", rule))

    def test_rule_match_exact_no_wildcard(self):
        rule = {"patterns": ["reporte"], "extensions": [".pdf"]}
        self.assertTrue(fm.rule_matches("reporte.pdf", rule))
        # Documentado en RULES.md: sin '*' la coincidencia es exacta
        self.assertFalse(fm.rule_matches("reporte-2026.pdf", rule))

    def test_rule_match_nfd_unicode(self):
        # macOS entrega nombres en NFD: 'artículo' descompuesto
        rule = self.cfg["rules"][2]
        nfd_name = unicodedata.normalize("NFD", "artículo-ml.pdf")
        self.assertTrue(fm.rule_matches(nfd_name, rule))

    def test_resolve_client(self):
        clients = self.cfg["clients"]
        self.assertEqual(fm.resolve_client("NV-PROP-CECA-x.pdf", clients)["code"], "CECA")
        self.assertEqual(fm.resolve_client("propuesta ceca salud.pdf", clients)["code"], "CECA")
        self.assertEqual(fm.resolve_client("factura-ajj.pdf", clients)["code"], "AJJ")
        self.assertIsNone(fm.resolve_client("nada-que-ver.pdf", clients))

    def test_render_pattern(self):
        from datetime import datetime
        client = {"code": "CECA"}
        out = fm.render_pattern("NV-PROP-{CLIENT}-{DD-MM-YYYY}", client, "base")
        self.assertIn("CECA", out)
        self.assertIn(datetime.now().strftime("%d-%m-%Y"), out)
        out2 = fm.render_pattern("clientes/{CLIENT}/invoices", None, "")
        self.assertEqual(out2, "clientes/UNKNOWN/invoices")


class TestProcessing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nuvaus-test-")
        self.cfg = make_cfg(self.tmp)
        os.makedirs(self.cfg["downloads"], exist_ok=True)
        fm.DRY_RUN = False
        fm.VERBOSE = False
        fm.LOG_DIR = os.path.join(self.tmp, "logs")
        fm.LOG_FILE = os.path.join(fm.LOG_DIR, "test.log")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def dl(self, name, **kw):
        touch(os.path.join(self.cfg["downloads"], name), **kw)

    def test_move_and_rename(self):
        self.dl("NV-PROP-CECA-borrador.pdf")
        moved = fm.process_downloads(self.cfg)
        self.assertEqual(len(moved), 1)
        dest = os.path.join(self.cfg["base"], "propuestas")
        files = os.listdir(dest)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].startswith("NV-PROP-CECA-"))
        self.assertTrue(files[0].endswith(".pdf"))

    def test_client_folder_destination(self):
        # {CLIENT} en destination (documentado en RULES.md, no implementado en el .ps1)
        self.dl("factura-AJJ-junio.pdf")
        fm.process_downloads(self.cfg)
        dest = os.path.join(self.cfg["base"], "clientes", "AJJ", "invoices")
        self.assertTrue(os.path.isdir(dest))
        self.assertEqual(len(os.listdir(dest)), 1)

    def test_unmatched_stays(self):
        self.dl("cualquier-cosa.txt")
        moved = fm.process_downloads(self.cfg)
        self.assertEqual(len(moved), 0)
        self.assertTrue(os.path.exists(os.path.join(self.cfg["downloads"], "cualquier-cosa.txt")))

    def test_system_files_ignored(self):
        self.dl(".DS_Store")
        self.dl("descarga.pdf.crdownload")
        moved = fm.process_downloads(self.cfg)
        self.assertEqual(len(moved), 0)

    def test_fresh_file_age_guard(self):
        cfg = make_cfg(self.tmp, min_age=3600)  # exige 1h de antigüedad
        os.makedirs(cfg["downloads"], exist_ok=True)
        self.dl("NV-PROP-CECA-x.pdf")  # recién creado
        moved = fm.process_downloads(cfg)
        self.assertEqual(len(moved), 0)  # se salta por reciente

    def test_collision_gets_timestamp(self):
        dest = os.path.join(self.cfg["base"], "propuestas")
        self.dl("NV-PROP-CECA-a.pdf")
        fm.process_downloads(self.cfg)
        self.dl("NV-PROP-CECA-b.pdf")  # mismo rename → colisión
        fm.process_downloads(self.cfg)
        self.assertEqual(len(os.listdir(dest)), 2)  # ninguno sobrescrito

    def test_dry_run_moves_nothing(self):
        fm.DRY_RUN = True
        self.dl("NV-PROP-CECA-x.pdf")
        moved = fm.process_downloads(self.cfg)
        self.assertEqual(len(moved), 1)  # reporta qué haría
        self.assertTrue(os.path.exists(os.path.join(self.cfg["downloads"], "NV-PROP-CECA-x.pdf")))
        self.assertFalse(os.path.isdir(os.path.join(self.cfg["base"], "propuestas")))

    @staticmethod
    def _stat_with_old_ctime(suffixes):
        """os.stat parcheado: para archivos cuyo nombre termina en `suffixes`,
        simula que el ctime es igual de antiguo que el mtime (como un archivo
        que lleva meses en la carpeta). Los tests no pueden fijar ctime real."""
        real_stat = os.stat

        def fake_stat(path, *a, **kw):
            st = real_stat(path, *a, **kw)
            if isinstance(path, str) and path.endswith(suffixes):
                return os.stat_result((st.st_mode, st.st_ino, st.st_dev, st.st_nlink,
                                       st.st_uid, st.st_gid, st.st_size,
                                       st.st_atime, st.st_mtime, st.st_mtime))
            return st
        return fake_stat

    def test_archive_old_proposals(self):
        old = time.time() - 200 * 86400  # 200 días
        year = time.strftime("%Y", time.localtime(old))
        touch(os.path.join(self.cfg["base"], "propuestas", "vieja.pdf"), mtime=old)
        touch(os.path.join(self.cfg["base"], "propuestas", "nueva.pdf"))
        with mock.patch.object(fm.os, "stat", side_effect=self._stat_with_old_ctime(("vieja.pdf",))):
            fm.archive_old_proposals(self.cfg)
        archived = os.path.join(self.cfg["base"], "propuestas-archivo", year, "vieja.pdf")
        self.assertTrue(os.path.exists(archived))
        self.assertTrue(os.path.exists(os.path.join(self.cfg["base"], "propuestas", "nueva.pdf")))

    def test_archive_protects_freshly_arrived_file(self):
        # mtime viejo pero ctime reciente (zip/AirDrop recién llegado) → NO se archiva
        old = time.time() - 200 * 86400
        touch(os.path.join(self.cfg["base"], "propuestas", "recien-llegada.pdf"), mtime=old)
        fm.archive_old_proposals(self.cfg)
        self.assertTrue(os.path.exists(os.path.join(self.cfg["base"], "propuestas", "recien-llegada.pdf")))

    def test_auto_delete_old_reports(self):
        target = os.path.join(self.cfg["base"], "temp", "reportes")
        old = time.time() - 40 * 86400  # 40 días > 30
        touch(os.path.join(target, "viejo.json"), mtime=old)
        touch(os.path.join(target, "reciente.json"))
        with mock.patch.object(fm.os, "stat", side_effect=self._stat_with_old_ctime(("viejo.json",))):
            fm.cleanup_auto_delete(self.cfg)
        self.assertFalse(os.path.exists(os.path.join(target, "viejo.json")))
        self.assertTrue(os.path.exists(os.path.join(target, "reciente.json")))

    def test_auto_delete_protects_freshly_arrived_file(self):
        # mtime viejo pero ctime reciente → NO se borra (protección anti-pérdida)
        target = os.path.join(self.cfg["base"], "temp", "reportes")
        old = time.time() - 40 * 86400
        touch(os.path.join(target, "recien-movido.json"), mtime=old)
        fm.cleanup_auto_delete(self.cfg)
        self.assertTrue(os.path.exists(os.path.join(target, "recien-movido.json")))

    def test_load_config_discards_malformed_rule(self):
        cfgdir = os.path.join(self.tmp, "config2")
        os.makedirs(cfgdir)
        with open(os.path.join(cfgdir, "paths.json"), "w") as f:
            json.dump({"nuvaus_base": "~/Desktop/Nuvaus", "monitored_downloads": "~/Downloads"}, f)
        with open(os.path.join(cfgdir, "rules.json"), "w") as f:
            json.dump({
                "rules": [
                    {"id": "rota", "name": "sin patterns ni destino"},
                    {"id": "ok", "name": "Válida", "patterns": ["x*"], "extensions": [".pdf"],
                     "destination": "d", "rename_pattern": "{FILENAME}"},
                ],
                "clients": [{"code": "CECA", "name": "CECA Salud"}, {"code": "", "name": ""}],
                "global_settings": {},
            }, f)
        cfg = fm.load_config(cfgdir)
        self.assertEqual([r["id"] for r in cfg["rules"]], ["ok"])
        self.assertEqual(len(cfg["clients"]), 1)

    def test_load_config_missing_paths_key_exits(self):
        cfgdir = os.path.join(self.tmp, "config3")
        os.makedirs(cfgdir)
        with open(os.path.join(cfgdir, "paths.json"), "w") as f:
            json.dump({"nuvaus_base": "~/Desktop/Nuvaus"}, f)  # falta monitored_downloads
        with open(os.path.join(cfgdir, "rules.json"), "w") as f:
            json.dump({"rules": [], "clients": [], "global_settings": {}}, f)
        with self.assertRaises(SystemExit):
            fm.load_config(cfgdir)

    def test_load_config_expands_home(self):
        cfgdir = os.path.join(self.tmp, "config")
        os.makedirs(cfgdir)
        with open(os.path.join(cfgdir, "paths.json"), "w") as f:
            json.dump({"nuvaus_base": "~/Desktop/Nuvaus", "monitored_downloads": "~/Downloads"}, f)
        with open(os.path.join(cfgdir, "rules.json"), "w") as f:
            json.dump({"rules": [], "clients": [], "global_settings": {}}, f)
        cfg = fm.load_config(cfgdir)
        self.assertFalse(cfg["base"].startswith("~"))
        self.assertTrue(os.path.isabs(cfg["base"]))


if __name__ == "__main__":
    print("=" * 60)
    print("NUVAUS — Tests del File Manager")
    print("=" * 60)
    unittest.main(verbosity=2)
