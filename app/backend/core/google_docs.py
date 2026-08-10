"""
Import de materiais de leitura a partir de um Google Doc.

Fluxo: o profissional escreve o material no Google Docs, compartilha o
documento com a service account da clínica (client_email dentro do JSON em
GOOGLE_SERVICE_ACCOUNT_JSON, ver core/config.py) e cola o link no formulário
de import. Este módulo:

1. Extrai o ID do documento a partir da URL.
2. Exporta o doc como HTML via Drive API (chamada síncrona da lib do Google
   -- roda em thread separada pra não bloquear o event loop, ver
   `import_material_html`).
3. Sanitiza o HTML (`bleach`) -- o conteúdo vem de uma fonte externa e volta
   a ser renderizado pro paciente depois, então isso é proteção contra XSS,
   não só limpeza estética.
4. Reidrata qualquer `<img src="https://...">` como `data:` URI em base64,
   pra não depender de uma URL do Google continuar acessível depois do
   import (é uma foto do momento, não um link vivo).
"""

from __future__ import annotations

import asyncio
import base64
import json
import re

import bleach
import httpx
from bleach.css_sanitizer import CSSSanitizer
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.backend.core.config import settings

_DOC_ID_RE = re.compile(r"/document/d/([a-zA-Z0-9_-]+)")

_ALLOWED_TAGS = [
    "p",
    "br",
    "h1",
    "h2",
    "h3",
    "h4",
    "ul",
    "ol",
    "li",
    "strong",
    "em",
    "b",
    "i",
    "u",
    "a",
    "img",
    "table",
    "thead",
    "tbody",
    "tr",
    "td",
    "th",
    "span",
]
_ALLOWED_ATTRS = {
    "a": ["href"],
    "img": ["src", "alt"],
    "span": ["style"],
}
# O Docs costuma exportar negrito/itálico como <span style="font-weight:700">
# em vez de <strong>/<em> -- por isso liberamos essas 3 propriedades de CSS
# em vez de derrubar o atributo style inteiro (o que apagaria a formatação).
_ALLOWED_CSS_PROPERTIES = ["font-weight", "font-style", "text-decoration"]


def extract_doc_id(url: str) -> str:
    """Extrai o ID do documento de uma URL do Google Docs. Levanta ValueError
    se a URL não tiver o formato esperado (.../document/d/<id>/...)."""
    match = _DOC_ID_RE.search(url)
    if not match:
        raise ValueError(
            "URL não parece ser um link válido de Google Docs (esperado algo como "
            "https://docs.google.com/document/d/<id>/edit)"
        )
    return match.group(1)


def _build_drive_service():
    if not settings.GOOGLE_SERVICE_ACCOUNT_JSON:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON não configurado -- crie uma service account no "
            "Google Cloud, habilite a Drive API, e configure o JSON da credencial."
        )
    info = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def export_doc_html(doc_id: str) -> str:
    """Busca o Google Doc como HTML bruto (ainda não sanitizado). O documento
    precisa estar compartilhado com o e-mail da service account -- senão a
    API retorna 404, não 403 (o Google não revela se o doc existe pra quem
    não tem acesso)."""
    service = _build_drive_service()
    raw = service.files().export(fileId=doc_id, mimeType="text/html").execute()
    return raw.decode("utf-8") if isinstance(raw, bytes) else raw


def sanitize_material_html(html: str) -> str:
    # bleach.clean(strip=True) só remove a TAG de algo fora da allowlist --
    # o texto de dentro fica (é pensado pra tags de formatação, tipo tirar um
    # <span> mantendo a palavra). Isso é errado pra <script>/<style>: o
    # conteudo em si tem que sumir junto, senão "alert(1)" vira texto visível
    # na página. Derruba essas duas por completo antes de passar pro bleach.
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    css_sanitizer = CSSSanitizer(allowed_css_properties=_ALLOWED_CSS_PROPERTIES)
    return bleach.clean(
        str(soup),
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        css_sanitizer=css_sanitizer,
        strip=True,
    )


async def _inline_images(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    images = [img for img in soup.find_all("img") if str(img.get("src", "")).startswith("http")]
    if not images:
        return str(soup)

    async with httpx.AsyncClient(timeout=15.0) as client:
        for img in images:
            try:
                response = await client.get(img["src"])
                response.raise_for_status()
                content_type = response.headers.get("content-type", "image/png").split(";")[0]
                encoded = base64.b64encode(response.content).decode("ascii")
                img["src"] = f"data:{content_type};base64,{encoded}"
            except httpx.HTTPError:
                # Imagem que não pôde ser baixada sai do material em vez de
                # deixar um link quebrado pro paciente ver.
                img.decompose()
    return str(soup)


def _fetch_and_sanitize(doc_id: str) -> str:
    raw_html = export_doc_html(doc_id)
    return sanitize_material_html(raw_html)


async def import_material_html(url: str) -> tuple[str, str]:
    """Ponto de entrada usado pelo MaterialService. Retorna (doc_id, html
    pronto pra salvar). A chamada à API do Google é síncrona (lib oficial),
    então roda em thread separada pra não travar o event loop."""
    doc_id = extract_doc_id(url)
    clean_html = await asyncio.to_thread(_fetch_and_sanitize, doc_id)
    final_html = await _inline_images(clean_html)
    return doc_id, final_html
