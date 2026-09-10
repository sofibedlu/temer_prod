# -*- coding: utf-8 -*-
"""
PDF watermark controller for contract_draft_status.
Injects a CSS-based watermark into the HTML before generating the PDF
when draft_status == 'draft'.
"""
import logging
from markupsafe import Markup
from odoo import http
from odoo.http import request, Response

from odoo.addons.contract_pdf_preview.controllers.preview import (
    ContractPdfPreviewController, _get_archive, _get_content,
)
from .watermark_utils import show_watermark

def _inject_pdf_watermark(html_content):
    """Inject a <style> block targeting .page::after so wkhtmltopdf repeats it on every page."""
    if not html_content:
        return html_content
        
    watermark_style = """
    <style>
        .page::after {
            content: "DRAFT CONTRACT";
            position: fixed;
            top: 500px;
            left: -50%;
            width: 200%;
            text-align: center;
            transform: rotate(-45deg);
            font-size: 80pt;
            color: rgba(192, 192, 192, 0.25);
            font-weight: bold;
            z-index: 9999;
            pointer-events: none;
            white-space: nowrap;
            font-family: Arial, sans-serif;
            display: block;
        }
    </style>
    """
    return watermark_style + html_content

class ContractPdfWatermarkController(ContractPdfPreviewController):

    @http.route("/contract/pdf/download/<int:sale_id>", type="http", auth="user", website=False)
    def download_pdf(self, sale_id, **kwargs):
        sale = request.env["property.sale"].browse(sale_id)
        if not sale.exists():
            return Response("Sale not found", status=404)

        archive = _get_archive(request.env, sale)
        if not archive:
            return Response("No contract archive found", status=404)

        content = _get_content(sale, archive)
        
        # Inject watermark if draft_status is 'draft'
        if show_watermark(sale):
            content = _inject_pdf_watermark(content)

        datas = {
            "full_content": Markup(content) if content else Markup(""),
            "stamp": "",
            "customer_name": "",
        }

        report = request.env.ref("contract_managment.action_report_contract").sudo()
        pdf_content, _ = report._render_qweb_pdf(
            "contract_managment.report_printed_contract_document",
            [sale.id],
            data=datas,
        )

        filename = "Contract_{}.pdf".format((sale.name or str(sale_id)).replace("/", "_"))
        return request.make_response(
            pdf_content,
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Disposition", 'attachment; filename="{}"'.format(filename)),
            ],
        )

    @http.route("/contract/pdf/preview/<int:sale_id>", type="http", auth="user", website=False)
    def preview(self, sale_id, **kwargs):
        response = super().preview(sale_id, **kwargs)
        sale = request.env["property.sale"].browse(sale_id)
        if show_watermark(sale) and response.status_code == 200:
            html_str = response.get_data(as_text=True)
            # Inject a CSS class or div for the preview
            watermark_div = """
            <div style="
                position: fixed;
                top: 500px;
                left: 0;
                width: 100%;
                text-align: center;
                transform: translateY(-50%) rotate(-45deg);
                font-size: 90pt;
                color: rgba(192, 192, 192, 0.2);
                font-weight: bold;
                z-index: 1000;
                pointer-events: none;
                white-space: nowrap;
                font-family: Arial, sans-serif;
            ">DRAFT CONTRACT</div>
            """
            # Insert just after <body>
            if '<body>' in html_str:
                html_str = html_str.replace('<body>', '<body>' + watermark_div, 1)
                response.set_data(html_str)
        return response
