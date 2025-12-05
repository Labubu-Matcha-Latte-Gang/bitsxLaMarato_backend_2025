import html
import json
import re
from typing import Any

from flask import Response, current_app, request
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from helpers.debugger.logger import AbstractLogger
from schemas import SwaggerDocQuerySchema


blp = Blueprint(
    "documentation",
    __name__,
    description="Descàrrega de la documentació OpenAPI en formats HTML o PDF.",
)


@blp.route("")
class SwaggerDocResource(MethodView):
    """
    Endpoint públic per obtenir la documentació de Swagger/OpenAPI en format descarregable.
    """

    logger = AbstractLogger.get_instance()

    @staticmethod
    def _slugify_filename(name: str) -> str:
        clean = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower()
        return clean or "swagger-doc"

    def _get_openapi_spec(self) -> dict[str, Any]:
        labubu_ext = current_app.extensions.get("labubu", {})
        if isinstance(labubu_ext, dict):
            api_obj = labubu_ext.get("api")
            if api_obj and getattr(api_obj, "spec", None):
                spec_obj = api_obj.spec
                return spec_obj.to_dict() if hasattr(spec_obj, "to_dict") else spec_obj  # type: ignore[arg-type]

        smorest_ext = current_app.extensions.get("smorest")
        spec_candidate = None
        if isinstance(smorest_ext, dict):
            spec_candidate = smorest_ext.get("spec") or smorest_ext.get("apispec")
        else:
            spec_candidate = getattr(smorest_ext, "spec", None)

        if spec_candidate and hasattr(spec_candidate, "to_dict"):
            return spec_candidate.to_dict()

        prefix = current_app.config.get("OPENAPI_URL_PREFIX", "/") or "/"
        openapi_endpoint = f"{'' if prefix == '/' else prefix.rstrip('/')}/openapi.json"
        response = current_app.test_client().get(openapi_endpoint)
        if response.status_code == 200:
            payload = response.get_json(silent=True)
            if isinstance(payload, dict):
                return payload
        raise RuntimeError("No s'ha pogut recuperar l'especificació OpenAPI.")

    @staticmethod
    def _schema_block(schema: dict[str, Any] | None) -> str:
        if not schema:
            return ""
        try:
            schema_text = json.dumps(schema, indent=2, ensure_ascii=False)
        except Exception:
            schema_text = str(schema)
        escaped = html.escape(schema_text)
        return f"<pre class=\"schema\">{escaped}</pre>"

    def _render_parameters(self, parameters: list[dict[str, Any]]) -> str:
        if not parameters:
            return "<p class=\"muted\">Sense paràmetres.</p>"

        items: list[str] = []
        for param in parameters:
            if not isinstance(param, dict):
                continue
            name = html.escape(str(param.get("name", "")))
            location = html.escape(str(param.get("in", "")))
            required = bool(param.get("required", False))
            description = html.escape(str(param.get("description", "") or ""))
            schema = param.get("schema") or {}
            schema_label = ""
            ref = schema.get("$ref") if isinstance(schema, dict) else None
            if ref:
                schema_label = f" → {html.escape(str(ref))}"
            elif isinstance(schema, dict):
                schema_type = schema.get("type")
                schema_format = schema.get("format")
                if schema_type:
                    schema_label = f" ({html.escape(str(schema_type))}"
                    if schema_format:
                        schema_label += f", {html.escape(str(schema_format))}"
                    schema_label += ")"

            items.append(
                (
                    f"<li><span class=\"param-name\">{name}</span>"
                    f"<span class=\"badge badge-ghost\">{location}{' · obligatori' if required else ''}</span>"
                    f"{schema_label}"
                    f"{f'<div class=\"muted\">{description}</div>' if description else ''}</li>"
                )
            )
        return f"<ul class=\"param-list\">{''.join(items)}</ul>"

    def _render_request_body(self, request_body: dict[str, Any] | None) -> str:
        if not isinstance(request_body, dict):
            return ""

        description = html.escape(str(request_body.get("description", "") or ""))
        content = request_body.get("content") or {}
        entries: list[str] = []
        if isinstance(content, dict):
            for media_type, payload in content.items():
                schema_block = self._schema_block(payload.get("schema") if isinstance(payload, dict) else None)
                entries.append(f"<li><code>{html.escape(str(media_type))}</code>{schema_block}</li>")

        content_html = (
            f"<ul class=\"detail-list\">{''.join(entries)}</ul>"
            if entries
            else "<p class=\"muted\">Sense cos de petició definit.</p>"
        )

        return (
            "<div class=\"section\">"
            "<h4>Cos de la petició</h4>"
            f"{f'<p class=\"muted\">{description}</p>' if description else ''}"
            f"{content_html}"
            "</div>"
        )

    def _render_responses(self, responses: dict[str, Any]) -> str:
        if not isinstance(responses, dict) or not responses:
            return "<p class=\"muted\">Sense respostes documentades.</p>"

        rows: list[str] = []
        for status, payload in sorted(responses.items(), key=lambda item: str(item[0])):
            payload = payload or {}
            description = html.escape(str(payload.get("description", "") or ""))
            content = payload.get("content") or {}
            content_segments: list[str] = []
            if isinstance(content, dict):
                for media_type, media_payload in content.items():
                    schema_block = self._schema_block(
                        media_payload.get("schema") if isinstance(media_payload, dict) else None
                    )
                    content_segments.append(
                        f"<div class=\"muted\"><code>{html.escape(str(media_type))}</code></div>{schema_block}"
                    )

            rows.append(
                "<li>"
                f"<span class=\"badge badge-ghost\">{html.escape(str(status))}</span> {description}"
                f"{''.join(content_segments)}"
                "</li>"
            )

        return f"<ul class=\"detail-list\">{''.join(rows)}</ul>"

    def _render_schemas(self, components: dict[str, Any]) -> str:
        schemas = components.get("schemas") if isinstance(components, dict) else None
        if not isinstance(schemas, dict) or not schemas:
            return "<p class=\"muted\">Sense esquemes definits.</p>"

        cards: list[str] = []
        for name, schema in sorted(schemas.items(), key=lambda item: item[0]):
            schema_dict = schema if isinstance(schema, dict) else {"value": schema}
            description = ""
            if isinstance(schema_dict, dict) and schema_dict.get("description"):
                description = f"<p class=\"muted\">{html.escape(str(schema_dict.get('description')))}</p>"

            cards.append(
                "<div class=\"schema-card\">"
                f"<div class=\"schema-title\">{html.escape(str(name))}</div>"
                f"{description}"
                f"{self._schema_block(schema_dict)}"
                "</div>"
            )

        return "".join(cards)

    def _render_operation(
        self,
        path: str,
        method: str,
        operation: dict[str, Any],
        parameters: list[dict[str, Any]],
    ) -> str:
        summary = html.escape(str(operation.get("summary", "") or ""))
        description = html.escape(str(operation.get("description", "") or ""))
        tags = operation.get("tags") or []
        tag_html = "".join(f"<span class=\"tag\">{html.escape(str(tag))}</span>" for tag in tags if tag)

        request_body_html = self._render_request_body(operation.get("requestBody"))
        responses_html = self._render_responses(operation.get("responses") or {})

        return (
            f"<div class=\"operation method-{method.lower()}\">"
            "<div class=\"op-header\">"
            f"<span class=\"badge\">{method}</span>"
            f"<span class=\"op-path\">{html.escape(path)}</span>"
            f"{tag_html}"
            "</div>"
            f"{f'<div class=\"summary\">{summary}</div>' if summary else ''}"
            f"{f'<p class=\"description\">{description}</p>' if description else ''}"
            "<div class=\"section\">"
            "<h4>Paràmetres</h4>"
            f"{self._render_parameters(parameters)}"
            "</div>"
            f"{request_body_html}"
            "<div class=\"section\">"
            "<h4>Respostes</h4>"
            f"{responses_html}"
            "</div>"
            "</div>"
        )

    def _build_paths_html(self, paths: dict[str, Any]) -> str:
        if not paths:
            return "<p class=\"muted\">No hi ha cap endpoint documentat.</p>"

        allowed_methods = {"get", "post", "put", "patch", "delete", "options", "head"}
        segments: list[str] = []

        for path, path_item in sorted(paths.items(), key=lambda item: item[0]):
            if not isinstance(path_item, dict):
                continue

            path_parameters = path_item.get("parameters", [])
            if not isinstance(path_parameters, list):
                path_parameters = []
            operations: list[str] = []

            for method, operation in path_item.items():
                if method.lower() not in allowed_methods:
                    continue

                op_data = operation if isinstance(operation, dict) else {}
                op_params = op_data.get("parameters", [])
                if not isinstance(op_params, list):
                    op_params = []
                merged_params = list(op_params) + list(path_parameters)
                operations.append(self._render_operation(path, method.upper(), op_data, merged_params))

            if operations:
                segments.append(
                    f"<div class=\"path-block\"><div class=\"path-title\">{html.escape(path)}</div>{''.join(operations)}</div>"
                )

        return "".join(segments) or "<p class=\"muted\">No hi ha cap endpoint documentat.</p>"

    def _build_html(self, spec: dict[str, Any]) -> str:
        info = spec.get("info") or {}
        title = html.escape(str(info.get("title") or current_app.config.get("API_TITLE", "API")))
        version = html.escape(str(info.get("version") or current_app.config.get("API_VERSION", "")))
        description = html.escape(str(info.get("description", "") or ""))
        servers = spec.get("servers") or []
        components = spec.get("components") or {}

        server_items = []
        if isinstance(servers, list):
            for server in servers:
                if not isinstance(server, dict):
                    continue
                url = html.escape(str(server.get("url", "")))
                desc = html.escape(str(server.get("description", "") or ""))
                server_items.append(f"<li><code>{url}</code>{f'<div class=\"muted\">{desc}</div>' if desc else ''}</li>")

        server_html = (
            f"<ul class=\"server-list\">{''.join(server_items)}</ul>"
            if server_items
            else "<p class=\"muted\">Sense servidors declarats.</p>"
        )

        paths_html = self._build_paths_html(spec.get("paths") or {})
        schemas_html = self._render_schemas(components)

        return f"""<!DOCTYPE html>
<html lang="ca">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} · Documentació</title>
  <style>
    :root {{
      --bg: #f8fafc;
      --card: #ffffff;
      --text: #1f2937;
      --muted: #6b7280;
      --border: #e5e7eb;
      --accent: #2563eb;
      --accent-soft: #eff6ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 24px;
      font-family: "Segoe UI", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    .page {{ max-width: 1080px; margin: 0 auto 48px; }}
    .hero {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 20px 24px;
      background: linear-gradient(120deg, #ebf8ff, #eef2ff);
      border: 1px solid var(--border);
      border-radius: 12px;
      margin-bottom: 18px;
    }}
    .eyebrow {{
      color: var(--muted);
      letter-spacing: 0.04em;
      font-size: 13px;
      text-transform: uppercase;
      margin: 0 0 4px 0;
    }}
    h1 {{ margin: 0; font-size: 28px; }}
    .muted {{ color: var(--muted); font-size: 14px; }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px 18px;
      margin-bottom: 16px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.02);
    }}
    .card h3 {{ margin-top: 0; }}
    .server-list, .detail-list, .param-list {{ list-style: none; padding: 0; margin: 0; }}
    .server-list li, .detail-list li, .param-list li {{ margin-bottom: 10px; }}
    code {{
      background: var(--accent-soft);
      color: var(--accent);
      padding: 2px 6px;
      border-radius: 6px;
      font-size: 13px;
    }}
    .path-block {{
      border-top: 1px solid var(--border);
      padding-top: 14px;
      margin-top: 14px;
    }}
    .path-title {{
      font-weight: 600;
      margin-bottom: 8px;
      display: inline-block;
    }}
    .operation {{
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px 14px;
      margin-bottom: 12px;
      background: #fff;
    }}
    .method-get {{ border-left: 5px solid #0ea5e9; }}
    .method-post {{ border-left: 5px solid #16a34a; }}
    .method-put {{ border-left: 5px solid #f59e0b; }}
    .method-patch {{ border-left: 5px solid #a855f7; }}
    .method-delete {{ border-left: 5px solid #ef4444; }}
    .op-header {{
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
      margin-bottom: 6px;
    }}
    .badge {{
      background: var(--accent);
      color: white;
      padding: 4px 10px;
      border-radius: 20px;
      font-weight: 600;
      font-size: 12px;
      letter-spacing: 0.02em;
    }}
    .badge-ghost {{
      background: #f1f5f9;
      color: var(--text);
      padding: 2px 8px;
      border-radius: 12px;
      font-weight: 600;
      font-size: 12px;
    }}
    .op-path {{ font-weight: 600; }}
    .tag {{
      background: #eef2ff;
      color: #4338ca;
      padding: 2px 8px;
      border-radius: 12px;
      font-weight: 600;
      font-size: 12px;
    }}
    .summary {{ font-weight: 600; margin: 4px 0; }}
    .description {{ margin: 4px 0 10px 0; }}
    .section h4 {{ margin: 8px 0; }}
    .schema {{
      background: #0f172a;
      color: #e2e8f0;
      padding: 12px;
      border-radius: 10px;
      overflow-x: auto;
      font-size: 13px;
      line-height: 1.4;
    }}
    .schema-card {{
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px;
      margin-bottom: 12px;
    }}
    .schema-title {{
      font-weight: 700;
      margin-bottom: 6px;
    }}
    footer {{ margin-top: 18px; }}
  </style>
</head>
<body>
  <div class="page">
    <div class="hero">
      <div>
        <p class="eyebrow">Documentació OpenAPI</p>
        <h1>{title}</h1>
        <p class="muted">Versió {version}</p>
      </div>
      <div class="badge-ghost">/api-docs</div>
    </div>
    <div class="card">
      <h3>Descripció</h3>
      <p>{description or "Sense descripció disponible."}</p>
    </div>
    <div class="card">
      <h3>Servidors</h3>
      {server_html}
    </div>
    <div class="card">
      <h3>Esquemes</h3>
      {schemas_html}
    </div>
    <div class="card">
      <h3>Endpoints</h3>
      {paths_html}
    </div>
    <footer class="muted">Generat automàticament a partir de l'especificació OpenAPI.</footer>
  </div>
</body>
</html>"""

    @staticmethod
    def _build_pdf(html_content: str) -> bytes:
        try:
            from weasyprint import HTML
        except Exception as exc:  # pragma: no cover - import guard
            raise RuntimeError("WeasyPrint no està disponible per generar PDF.") from exc
        return HTML(string=html_content, base_url=request.url_root).write_pdf()

    @blp.arguments(SwaggerDocQuerySchema, location="query")
    @blp.doc(
        security=[],
        summary="Descarregar Swagger/OpenAPI",
        description="Recupera la documentació vigent d'/api-docs com a fitxer HTML (per defecte) o PDF.",
    )
    @blp.response(200, description="Documentació generada correctament.")
    def get(self, query_args: dict[str, Any]):
        """
        Descarrega la documentació actual de la API.

        Paràmetres:
        - format: 'html' (per defecte) o 'pdf'.
        """
        doc_format = (query_args.get("format") or "html").lower()
        try:
            spec = self._get_openapi_spec()
            html_content = self._build_html(spec)
            filename_base = self._slugify_filename(
                spec.get("info", {}).get("title") or current_app.config.get("API_TITLE", "api")
            )
            if doc_format == "pdf":
                pdf_bytes = self._build_pdf(html_content)
                self.logger.info("Documentació Swagger generada en PDF", module="SwaggerDocResource")
                return Response(
                    pdf_bytes,
                    mimetype="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename_base}.pdf"'},
                )

            self.logger.info("Documentació Swagger generada en HTML", module="SwaggerDocResource")
            return Response(
                html_content,
                mimetype="text/html",
                headers={"Content-Disposition": f'attachment; filename="{filename_base}.html"'},
            )
        except Exception as exc:
            self.logger.error("Error en generar la documentació Swagger", module="SwaggerDocResource", error=exc)
            abort(500, message="No s'ha pogut generar la documentació en aquest moment.")
