# -*- coding: utf-8 -*-
"""
DOCX watermark controllers for contract_draft_status.
Handles two DOCX download routes:
  - /contract/docx/download/   (from contract_pdf_preview)
  - /draft_archive/docx/download/  (from draft_archive_model)
Both inject an OOXML watermark when draft_status == 'draft'.
"""
import io
import re
import zipfile
import logging
from markupsafe import Markup
from odoo import http
from odoo.http import request, Response
from odoo.addons.contract_pdf_preview.controllers.preview import (
    ContractPdfPreviewController, _get_archive, _get_content,
)
from odoo.addons.draft_archive_model.controllers.docx_download import DraftDocxDownloadController
from .watermark_utils import show_watermark

_logger = logging.getLogger(__name__)

# ── OOXML watermark fragments ─────────────────────────────────────────────────

_WM_SHAPETYPE = (
    '<v:shapetype id="_x0000_t136" coordsize="21600,21600" o:spt="136" adj="10800"'
    ' path="m@7,0l@8,0m@5,21600l@6,21600&amp;e">'
    '<v:formulas>'
    '<v:f eqn="sum #0 0 10800"/><v:f eqn="prod #0 2 1"/>'
    '<v:f eqn="sum 21600 0 @1"/><v:f eqn="sum 0 0 @2"/>'
    '<v:f eqn="sum 21600 0 @3"/><v:f eqn="if @0 @3 0"/>'
    '<v:f eqn="if @0 21600 @1"/><v:f eqn="if @0 0 @2"/>'
    '<v:f eqn="if @0 @4 21600"/><v:f eqn="mid @5 @6"/>'
    '<v:f eqn="mid @8 @5"/><v:f eqn="mid @7 @8"/>'
    '<v:f eqn="mid @6 @7"/><v:f eqn="sum @6 0 @5"/>'
    '</v:formulas>'
    '<v:path textpathok="t" o:connecttype="custom"'
    ' o:connectlocs="@9,0;@10,10800;@11,21600;@12,10800"'
    ' o:connectangles="270,180,90,0"/>'
    '<v:textpath on="t" fitshape="t"/>'
    '<v:handles><v:h position="#0,bottomRight" xrange="6629,14971"/></v:handles>'
    '<o:lock v:ext="edit" text="t" shapetype="t"/>'
    '</v:shapetype>'
)

_WM_SHAPE = (
    '<v:shape id="WaterMark" type="#_x0000_t136"'
    ' style="position:absolute;margin-left:0;margin-top:0;'
    'width:527.85pt;height:131.95pt;'
    'z-index:-251654144;'
    'mso-position-horizontal:center;'
    'mso-position-horizontal-relative:margin;'
    'mso-position-vertical:center;'
    'mso-position-vertical-relative:margin;'
    'rotation:315"'
    ' fillcolor="#C0C0C0" stroked="f">'
    '<v:fill on="t" focussize="0,0"/>'
    '<v:path textpathok="t"/>'
    '<v:textpath on="t" string="DRAFT CONTRACT"'
    ' style=\'font-family:"Arial";font-size:1pt;font-weight:bold\'/>'
    '<o:lock v:ext="edit" shapetype="t"/>'
    '</v:shape>'
)


def _build_wm_header(show):
    """Build OOXML header XML with or without watermark."""
    wm_para = (
        '<w:p><w:r><w:rPr><w:noProof/></w:rPr>'
        '<w:pict>' + _WM_SHAPE + '</w:pict>'
        '</w:r></w:p>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:hdr'
        ' xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
        ' xmlns:v="urn:schemas-microsoft-com:vml"'
        ' xmlns:o="urn:schemas-microsoft-com:office:office"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        + (_WM_SHAPETYPE if show else '') +
        '<w:p><w:pPr><w:jc w:val="left"/></w:pPr></w:p>'
        + (wm_para if show else '') +
        '</w:hdr>'
    )


def _build_docx_zip(html_str, header_xml):
    """Assemble a .docx ZIP from HTML content and a header XML string."""
    docx_io = io.BytesIO()
    with zipfile.ZipFile(docx_io, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr('[Content_Types].xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="htm" ContentType="text/html"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
            '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
            '</Types>')
        zipf.writestr('_rels/.rels',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
        zipf.writestr('word/_rels/document.xml.rels',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="htmlChunk" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/aFChunk" Target="chunk.htm"/>'
            '<Relationship Id="rIdHeader" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>'
            '<Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
            '</Relationships>')
        zipf.writestr('word/header1.xml', header_xml)
        zipf.writestr('word/footer1.xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:p><w:pPr>'
            '<w:pBdr><w:top w:val="single" w:sz="6" w:space="1" w:color="auto"/></w:pBdr>'
            '<w:jc w:val="right"/>'
            '</w:pPr>'
            '<w:r><w:t>Page </w:t></w:r>'
            '<w:fldSimple w:instr=" PAGE "/>'
            '<w:r><w:t> / </w:t></w:r>'
            '<w:fldSimple w:instr=" NUMPAGES "/>'
            '</w:p></w:ftr>')
        zipf.writestr('word/document.xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
            ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<w:body>'
            '<w:altChunk r:id="htmlChunk"/>'
            '<w:sectPr>'
            '<w:headerReference w:type="default" r:id="rIdHeader"/>'
            '<w:footerReference w:type="default" r:id="rIdFooter"/>'
            '<w:pgNumType w:start="1"/>'
            '</w:sectPr>'
            '</w:body></w:document>')
        zipf.writestr('word/chunk.htm', html_str.encode('utf-8'))
    return docx_io.getvalue()


# ── Route 1: /contract/docx/download/ (contract_pdf_preview) ─────────────────

class ContractDocxWatermarkController(ContractPdfPreviewController):

    @http.route("/contract/docx/download/<int:sale_id>", type="http", auth="user", website=False)
    def download_docx(self, sale_id, **kwargs):
        sale = request.env["property.sale"].browse(sale_id)
        if not sale.exists():
            return Response("Sale not found", status=404)

        archive = _get_archive(request.env, sale)
        if not archive:
            return Response("No contract archive found", status=404)

        content = _get_content(sale, archive)
        show = show_watermark(sale)

        try:
            clean = re.sub(
                r'(<p[^>]*>)?\s*(&nbsp;)*\s*(/pagebreak|\[PAGEBREAK\])\s*(&nbsp;)*\s*(/p>)?',
                '<div style="page-break-before: always; clear:both;"></div>',
                content, flags=re.IGNORECASE
            )
            datas = {
                "full_content": Markup(clean) if clean else Markup(""),
                "customer_name": sale.get_full_name() if hasattr(sale, 'get_full_name') else "",
            }
            report = request.env['ir.actions.report'].sudo()
            html_bytes, _ = report._render_qweb_html(
                'contract_managment.action_report_contract', sale.ids, data=datas
            )
            html_str = html_bytes.decode('utf-8')
            if '<head>' in html_str and '<meta charset="utf-8"' not in html_str.lower():
                html_str = html_str.replace('<head>', '<head><meta charset="utf-8">')

            docx_data = _build_docx_zip(html_str, _build_wm_header(show))
            filename = 'Contract_{}.docx'.format((sale.name or str(sale_id)).replace('/', '_'))
            return request.make_response(docx_data, headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
                ('Content-Disposition', 'attachment; filename="{}"'.format(filename)),
            ])
        except Exception as e:
            _logger.exception("DOCX export failed for sale=%s", sale_id)
            return Response("DOCX export failed: " + str(e), status=500)


# ── Route 2: /draft_archive/docx/download/ (draft_archive_model) ─────────────

class DraftDocxWatermarkController(DraftDocxDownloadController):

    @http.route(
        "/draft_archive/docx/download/<int:sale_id>",
        type="http", auth="user", website=False
    )
    def download_docx(self, sale_id, **kwargs):
        sale = request.env["property.sale"].browse(sale_id)
        self._show_watermark = show_watermark(sale)
        return super().download_docx(sale_id, **kwargs)

    def _build_docx_header(self):
        return _build_wm_header(getattr(self, "_show_watermark", False))
