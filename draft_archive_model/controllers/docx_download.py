import io
import zipfile
import re
from odoo import http
from odoo.http import request, Response


class DraftDocxDownloadController(http.Controller):

    @http.route(
        "/draft_archive/docx/download/<int:sale_id>",
        type="http", auth="user", website=False
    )
    def download_docx(self, sale_id, **kwargs):
        sale = request.env["property.sale"].browse(sale_id)
        if not sale.exists():
            return Response("Sale not found", status=404)

        # Get latest HTML — check system param first (set by wizard at download time)
        param_key = 'draft_docx_html_{}'.format(sale_id)
        html_str = request.env['ir.config_parameter'].sudo().get_param(param_key, '')
        if html_str:
            request.env['ir.config_parameter'].sudo().set_param(param_key, '')
        else:
            draft = (
                request.env["draft.contract.archive"].search(
                    [("sale_id", "=", sale.id), ("status", "!=", "void")], limit=1
                )
                or request.env["draft.contract.archive"].search(
                    [("source_archive_id.sale_id", "=", sale.id), ("status", "!=", "void")], limit=1
                )
            )
            if draft and draft.rendered_html:
                html_str = str(draft.rendered_html)
            else:
                archive = (
                    request.env["contract.archive"].search(
                        [("sale_id", "=", sale.id), ("status", "!=", "void")], limit=1
                    )
                    or request.env["contract.archive"].search(
                        [("sales_no", "=", sale.name), ("status", "!=", "void")], limit=1
                    )
                )
                if not archive:
                    return Response("No contract archive found", status=404)
                html_str = str(archive.rendered_html or "")

        # Inject CSS and ensure proper HTML structure
        css = (
            'body,p,div,span,td,th,li{'
            'font-family:"Noto Sans Ethiopic","Nyala","Abyssinica SIL",Arial,sans-serif;'
            'font-size:12pt;line-height:1.6;color:#111;}'
            'p{margin-bottom:8pt;text-align:justify;}'
            'h1{text-align:center;text-decoration:underline;font-size:14pt;font-weight:bold;}'
            'h2{text-align:center;font-size:13pt;font-weight:bold;}'
            'h3,h4{font-size:12pt;font-weight:bold;}'
            'table{width:100%;border-collapse:collapse;margin:10pt 0;}'
            'td,th{border:1pt solid black;padding:6pt;font-size:10pt;vertical-align:top;}'
            'th{background-color:#f2f2f2;font-weight:bold;text-align:center;}'
            'b,strong{font-weight:bold;}i,em{font-style:italic;}u{text-decoration:underline;}'
        )
        style_tag = '<style>' + css + '</style>'
        if '<head>' in html_str:
            if '<meta charset="utf-8"' not in html_str.lower():
                html_str = html_str.replace('<head>', '<head><meta charset="utf-8"/>' + style_tag)
            else:
                html_str = html_str.replace('</head>', style_tag + '</head>')
        else:
            html_str = (
                '<html><head><meta charset="utf-8"/>' + style_tag + '</head>'
                '<body>' + html_str + '</body></html>'
            )

        # Clean page breaks
        clean = re.sub(
            r'(<p[^>]*>)?\s*(&nbsp;)*\s*(/pagebreak|\[PAGEBREAK\])\s*(&nbsp;)*\s*(/p>)?',
            '<div style="page-break-before:always;clear:both;"></div>',
            html_str, flags=re.IGNORECASE
        )

        header_xml = self._build_docx_header()
        docx_io = io.BytesIO()
        with zipfile.ZipFile(docx_io, 'w', zipfile.ZIP_DEFLATED) as zipf:

            zipf.writestr('[Content_Types].xml',
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Default Extension="htm" ContentType="text/html"/>'
                '<Override PartName="/word/document.xml"'
                ' ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                '<Override PartName="/word/header1.xml"'
                ' ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
                '<Override PartName="/word/footer1.xml"'
                ' ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
                '</Types>')

            zipf.writestr('_rels/.rels',
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1"'
                ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"'
                ' Target="word/document.xml"/>'
                '</Relationships>')

            zipf.writestr('word/_rels/document.xml.rels',
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="htmlChunk"'
                ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/aFChunk"'
                ' Target="chunk.htm"/>'
                '<Relationship Id="rIdHeader"'
                ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header"'
                ' Target="header1.xml"/>'
                '<Relationship Id="rIdFooter"'
                ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer"'
                ' Target="footer1.xml"/>'
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
                '<w:document'
                ' xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
                ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<w:body>'
                '<w:altChunk r:id="htmlChunk"/>'
                '<w:sectPr>'
                '<w:headerReference w:type="default" r:id="rIdHeader"/>'
                '<w:footerReference w:type="default" r:id="rIdFooter"/>'
                '<w:pgNumType w:start="1"/>'
                '</w:sectPr>'
                '</w:body></w:document>')

            zipf.writestr('word/chunk.htm', clean.encode('utf-8'))

        docx_data = docx_io.getvalue()
        filename = 'Contract_{}.docx'.format((sale.name or str(sale_id)).replace('/', '_'))
        return request.make_response(docx_data, headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
            ('Content-Disposition', 'attachment; filename="{}"'.format(filename)),
        ])

    def _build_docx_header(self):
        """Build the DOCX header XML (no watermark, no company name)."""
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:hdr'
            ' xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
            ' xmlns:v="urn:schemas-microsoft-com:vml"'
            ' xmlns:o="urn:schemas-microsoft-com:office:office"'
            ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<w:p><w:pPr><w:jc w:val="left"/></w:pPr></w:p>'
            '</w:hdr>'
        )


