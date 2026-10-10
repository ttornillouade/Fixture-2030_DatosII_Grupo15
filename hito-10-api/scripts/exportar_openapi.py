"""Genera openapi/openapi.yaml desde el código de la API (el contrato sale de las rutas reales)."""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.main import app  # noqa: E402

destino = Path(__file__).resolve().parent.parent / "openapi" / "openapi.yaml"
texto = yaml.safe_dump(app.openapi(), allow_unicode=True, sort_keys=False)
if "--verificar" in sys.argv:
    actual = destino.read_text(encoding="utf-8") if destino.exists() else ""
    if actual != texto:
        print("DIFERENTE: openapi/openapi.yaml no coincide con el código. Ejecutar scripts/exportar_openapi.py")
        sys.exit(1)
    print("OK: openapi/openapi.yaml coincide con las rutas implementadas")
else:
    destino.write_text(texto, encoding="utf-8")
    print(f"Contrato escrito en {destino.relative_to(destino.parent.parent)}")
