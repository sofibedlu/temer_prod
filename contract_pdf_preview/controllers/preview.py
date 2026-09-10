import io
import zipfile
import re
import base64
from odoo import http
from odoo.http import request, Response
from markupsafe import Markup


def _get_archive(env, sale):
    return (
        env["contract.archive"].search(
            [("sale_id", "=", sale.id), ("status", "!=", "void")], limit=1
        )
        or env["contract.archive"].search(
            [("sales_no", "=", sale.name), ("status", "!=", "void")], limit=1
        )
    )



def _get_content(sale, archive):
    raw = (
        archive.rendered_html
        if archive.rendered_html
        else sale.contract_section_template_id.render_full_contract(
            sale.contract_id, archive
        )
    )
    content = str(raw)
    # Remove signature footer only
    content = re.sub(
        r'<div[^>]*class=["\'][^"\']*sig-footer[^"\']*["\'][^>]*>.*?</div>',
        "", content, flags=re.DOTALL
    )
    # Remove any company header box (header-box, header-main, header-mini)
    content = re.sub(
        r'<div[^>]*class=["\'][^"\']*(?:header-box|header-main|header-mini)[^"\']*["\'][^>]*>.*?</div>',
        "", content, flags=re.DOTALL
    )
    return content


# JS is a plain string — no f-string, no brace escaping issues
_PAGINATOR_JS = """
(function() {
    var raw    = document.getElementById('raw-html');
    var target = document.getElementById('render-target');
    if (!raw || !target) return;

    var elements = Array.from(raw.children);
    var itemsPerPage = 7;
    var totalPages = Math.ceil(elements.length / itemsPerPage) || 1;

    for (var i = 0; i < Math.max(elements.length, 1); i += itemsPerPage) {
        var currentPage = Math.floor(i / itemsPerPage) + 1;
        var pageDiv = document.createElement('div');
        pageDiv.className = 'page';

        if (currentPage === 1) {
            pageDiv.innerHTML =
                ''; // header removed
                // '<div class="header-main">' +
                // '<span class="co-et">\\u1274\\u121d\\u122d \\u1206\\u120d\\u12f2\\u1295\\u130d \\u12ab\\u121d\\u1353\\u1292</span>' +
                // '<span class="co-en">TEMER HOLDING COMPANY</span>' +
                // '</div>';
        } else {
            pageDiv.innerHTML =
                ''; // header removed
                // '<div class="header-mini">' +
                // '<span>\\u1274\\u121d\\u122d \\u1206\\u120d\\u12f2\\u1295\\u130d \\u12ab\\u121d\\u1353\\u1292</span>' +
                // '<span>TEMER HOLDING COMPANY</span>' +
                // '</div>';
        }

        var contentDiv = document.createElement('div');
        contentDiv.className = 'content-area';
        var slice = elements.slice(i, i + itemsPerPage);
        if (slice.length === 0 && i === 0) {
            contentDiv.innerHTML = raw.innerHTML;
        } else {
            slice.forEach(function(el) { contentDiv.appendChild(el.cloneNode(true)); });
        }
        pageDiv.appendChild(contentDiv);

        var footer = document.createElement('div');
        footer.className = 'footer-page-num';
        footer.innerText = currentPage + ' / ' + totalPages;
        if (currentPage > 1) {
            pageDiv.appendChild(footer);
        }

        target.appendChild(pageDiv);
    }
})();
"""


_NUMBERING_JS = """
(function() {
    // Match patterns like: 17.1, 17.1.2, 1., 1.1., (1), (a) at start of text
    var NUM_RE = /^(\\(?\\d+(?:\\.\\d+)*\\.?\\)?|\\([a-z]\\))\\s+/;

    function processNode(el) {
        // Only process block-level text nodes
        var tag = el.tagName ? el.tagName.toLowerCase() : '';
        if (!tag || ['table','thead','tbody','tr','td','th','ul','ol','script','style'].indexOf(tag) !== -1) return;

        // If it's a container, recurse into children
        if (['div','section','article'].indexOf(tag) !== -1) {
            Array.from(el.children).forEach(processNode);
            return;
        }

        // For p, li, span — check text content
        var text = el.innerText || el.textContent || '';
        var match = text.match(NUM_RE);
        if (!match) return;

        // Already wrapped?
        if (el.classList && el.classList.contains('numbered-item')) return;
        if (el.parentNode && el.parentNode.classList && el.parentNode.classList.contains('numbered-item')) return;

        var numPart  = match[1];
        var restText = text.slice(match[0].length);

        // Preserve existing inline HTML after the number
        var innerHTML = el.innerHTML || '';
        // Strip the leading number from innerHTML
        var numEscaped = numPart.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
        var innerRest  = innerHTML.replace(new RegExp('^\\\\s*' + numEscaped + '\\\\s*'), '');

        var wrapper = document.createElement(tag === 'li' ? 'li' : 'p');
        wrapper.className = 'numbered-item';
        // Copy existing inline style
        if (el.getAttribute('style')) wrapper.setAttribute('style', el.getAttribute('style'));

        var numSpan  = document.createElement('span');
        numSpan.className = 'num';
        numSpan.textContent = numPart;

        var textSpan = document.createElement('span');
        textSpan.className = 'num-text';
        textSpan.innerHTML = innerRest;

        wrapper.appendChild(numSpan);
        wrapper.appendChild(textSpan);

        el.parentNode.replaceChild(wrapper, el);
    }

    // Run after paginator has built the pages
    document.querySelectorAll('.content-area').forEach(function(area) {
        Array.from(area.children).forEach(processNode);
    });
})();
"""


_ETHIOPIC_JS = """
(function() {
    // Ethiopic Unicode block: U+1200–U+137F, U+1380–U+139F, U+2D80–U+2DDF, U+AB01–U+AB2F
    var ETH_RE = /[\u1200-\u137F\u1380-\u139F\u2D80-\u2DDF\uAB01-\uAB2F]/;
    var SCALE  = 1.20;  // Ethiopic needs ~20% larger to match Latin visual size

    function scaleEthiopic(el) {
        if (!el || el.nodeType !== 1) return;
        var tag = el.tagName ? el.tagName.toLowerCase() : '';
        if (['script','style','head'].indexOf(tag) !== -1) return;

        var text = el.innerText || el.textContent || '';
        if (ETH_RE.test(text)) {
            var cs   = window.getComputedStyle(el);
            var cur  = parseFloat(cs.fontSize);
            if (cur && !el.dataset.ethScaled) {
                el.style.fontSize = (cur * SCALE) + 'px';
                el.dataset.ethScaled = '1';
            }
        }
        Array.from(el.children).forEach(scaleEthiopic);
    }

    document.querySelectorAll('.content-area').forEach(scaleEthiopic);
})();
"""


class ContractPdfPreviewController(http.Controller):

    @http.route("/contract/pdf/preview/<int:sale_id>", type="http", auth="user", website=False)
    def preview(self, sale_id, **kwargs):
        sale = request.env["property.sale"].browse(sale_id)
        if not sale.exists():
            return Response("Sale not found", status=404)

        archive = _get_archive(request.env, sale)
        if not archive:
            return Response("No contract archive found", status=404)

        content = _get_content(sale, archive)
        sale_name = sale.name or str(sale_id)

        css = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Ethiopic:wght@400;500;700&family=Roboto:wght@400;500;700&display=swap');

:root { --temer-green: #66853f; }
* { margin: 0; padding: 0; box-sizing: border-box; }

/* Ethiopic script needs ~120% size relative to Latin to appear the same visual weight */
:lang(am), [lang="am"],
.content-area *:not(table):not(td):not(th) {
    font-size-adjust: none;
}
/* Any span/p that contains Ethiopic characters gets a slight size boost via JS — see below */

body {
    background: #d0d0d0;
    font-family: 'Noto Sans Ethiopic', 'Roboto', Arial, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: 60px;
}

/* ── Toolbar ── */
.toolbar {
    position: fixed; top: 0; left: 0; right: 0; height: 50px;
    background: #2c3e50; color: white;
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 25px; z-index: 9999;
    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
    font-family: Arial, sans-serif;
}
.btn {
    padding: 7px 15px; background: var(--temer-green); color: white;
    text-decoration: none; border-radius: 4px; font-size: 13px;
    font-weight: bold; border: none; cursor: pointer;
}
.btn:hover { opacity: 0.88; }

/* ── A4 Page ── */
.page {
    background: #ffffff;
    width: 210mm;
    min-height: 297mm;
    padding: 15mm 15mm 20mm 15mm;
    margin-bottom: 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.28);
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

/* ── Company header — page 1 (main) ── */
.header-main {
    text-align: center;
    border-bottom: 2px solid #000;
    padding-bottom: 12px;
    margin-bottom: 35px;
}
.header-main .co-et {
    display: block;
    font-size: 20pt;
    font-weight: bold;
    color: var(--temer-green);
    font-family: 'Noto Sans Ethiopic', sans-serif;
    line-height: 1.3;
}
.header-main .co-en {
    display: block;
    font-size: 14pt;
    font-weight: bold;
    color: var(--temer-green);
    font-family: Arial, sans-serif;
    letter-spacing: 0.5px;
}

/* ── Company header — subsequent pages (mini) ── */
.header-mini {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1.5px solid #000;
    margin-bottom: 20px;
    padding-bottom: 5px;
    font-size: 10pt;
    font-weight: bold;
    color: var(--temer-green);
    font-family: 'Noto Sans Ethiopic', Arial, sans-serif;
}

/* ── Content area — base font ── */
.content-area {
    flex-grow: 1;
    font-family: 'Noto Sans Ethiopic', 'Roboto', Arial, sans-serif;
    font-size: 14pt;        /* bumped up — Ethiopic renders smaller than Latin */
    line-height: 1.8;       /* more breathing room for Ethiopic glyphs */
    color: #111;
    text-align: justify;
    background: #ffffff;
}

/* All elements inside content inherit and wrap properly */
.content-area * {
    max-width: 100%;
    word-wrap: break-word;
    overflow-wrap: break-word;
}

.content-area p {
    display: block;
    width: 100%;
    margin-bottom: 10px;
    line-height: 1.6;
}

.content-area h1, .content-area h2 {
    text-align: center;
    font-weight: bold;
    margin: 18px 0 10px;
    line-height: 1.4;
    color: #000 !important;
}
.content-area h1 { font-size: 16pt; text-decoration: underline; }
.content-area h2 { font-size: 14pt; }
.content-area h3, .content-area h4 {
    font-size: 12pt;
    font-weight: bold;
    margin: 12px 0 6px;
    color: #000 !important;
}

/* ── Tables — match wizard exactly ── */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
    table-layout: fixed;
    font-family: 'Nyala', 'Abyssinica SIL', 'Noto Sans Ethiopic', sans-serif;
}
td, th {
    border: 1px solid black;
    padding: 8px;
    font-size: 10pt;
    word-wrap: break-word;
    overflow-wrap: break-word;
    vertical-align: top;
    background-color: #ffffff !important;
    color: #111 !important;
}
th {
    background-color: #f2f2f2 !important;
    font-weight: bold;
    text-align: center;
}

/* ── Signature footer ── */
.sig-footer {
    display: flex;
    justify-content: space-between;
    border-top: 1px solid #000;
    padding-top: 8px;
    margin-top: 20px;
    font-size: 10pt;
    color: #333;
}

/* ── Page footer: horizontal line + page number bottom-left ── */
.footer-page-num {
    position: absolute;
    bottom: 10mm;
    left: 15mm;
    right: 15mm;
    border-top: 1px solid #000;
    padding-top: 4px;
    text-align: left;
    font-size: 10pt;
    color: #444;
    font-family: Arial, sans-serif;
}

/* ── Odoo editor class name mappings ── */
.display-4-fs { font-size: 28pt !important; }
.h1-fs        { font-size: 16pt !important; }
.h2-fs        { font-size: 14pt !important; }
.h3-fs        { font-size: 13pt !important; }
/* Scale down huge inline px sizes to fit A4 — 1px ≈ 0.56pt at A4 scale */
.content-area [style*="font-size:56px"],
.content-area [style*="font-size: 56px"] { font-size: 28pt !important; }
.content-area [style*="font-size:48px"],
.content-area [style*="font-size: 48px"] { font-size: 24pt !important; }
.content-area [style*="font-size:36px"],
.content-area [style*="font-size: 36px"] { font-size: 18pt !important; }
.content-area [style*="font-size:28px"],
.content-area [style*="font-size: 28px"] { font-size: 14pt !important; }
.content-area [style*="font-size:21px"],
.content-area [style*="font-size: 21px"] { font-size: 12pt !important; }
/* oe-tabs: collapse to a normal space */
.oe-tabs { display: inline !important; width: auto !important;
           max-width: none !important; tab-size: 4 !important; }

/* ── Numbered paragraphs like 17.1, 17.2, 1.1.1 etc. ── */
.content-area p,
.content-area div {
    /* detect via JS — see script below */
}
.numbered-item {
    display: flex;
    gap: 8px;
    margin-bottom: 6px;
    line-height: 1.6;
}
.numbered-item .num {
    flex-shrink: 0;
    font-weight: bold;
    min-width: 40px;
}
.numbered-item .num-text {
    flex: 1;
    text-align: justify;
}
@media print {
    body { background: none; padding: 0; }
    .toolbar { display: none; }
    .page {
        margin: 0;
        box-shadow: none;
        page-break-after: always;
        width: 210mm;
        min-height: 297mm;
        padding: 15mm;
    }
    .page:last-child { page-break-after: avoid; }
    .footer-page-num { position: absolute; }
}
"""

        html = (
            "<!DOCTYPE html>\n<html>\n<head>\n"
            '<meta charset="utf-8"/>\n'
            "<title>Contract Preview - " + sale_name + "</title>\n"
            "<style>" + css + "</style>\n"
            "</head>\n<body>\n"
            '<div class="toolbar">\n'
            '  <div style="font-size:14px;"><strong>PREVIEW:</strong> ' + sale_name + "</div>\n"
            '  <div style="display:flex;gap:10px;">\n'
            '    <a href="/contract/pdf/download/' + str(sale_id) + '" class="btn">&#8595; Download PDF</a>\n'
            '    <a href="/contract/docx/download/' + str(sale_id) + '" class="btn" style="background:#1565c0;">&#8595; Download DOCX</a>\n'
            '    <button onclick="window.print()" class="btn" style="background:#555;">Print</button>\n'
            "  </div>\n</div>\n"
            '<div id="render-target"></div>\n'
            '<div id="raw-html" style="display:none;">' + content + "</div>\n"
            "<script>" + _PAGINATOR_JS + "</script>\n"
            "<script>" + _NUMBERING_JS + "</script>\n"
            "<script>" + _ETHIOPIC_JS + "</script>\n"
            "</body>\n</html>"
        )

        return Response(html, content_type="text/html; charset=utf-8")

    @http.route("/contract/pdf/download/<int:sale_id>", type="http", auth="user", website=False)
    def download_pdf(self, sale_id, **kwargs):
        sale = request.env["property.sale"].browse(sale_id)
        if not sale.exists():
            return Response("Sale not found", status=404)

        archive = _get_archive(request.env, sale)
        if not archive:
            return Response("No contract archive found", status=404)

        content = _get_content(sale, archive)

        datas = {
            "full_content": Markup(content) if content else Markup(""),
            "stamp": "",
            "customer_name": "",
        }

        report = request.env.ref("contract_managment.action_report_contract")
        pdf_content, _ = report._render_qweb_pdf(
            "contract_managment.report_printed_contract_document",
            [sale.id],
            data=datas,
        )

        filename = "Contract_" + (sale.name or str(sale_id)) + ".pdf"
        return Response(
            pdf_content,
            content_type="application/pdf",
            headers=[("Content-Disposition", 'attachment; filename="' + filename + '"')],
        )
    @http.route("/contract/docx/download/<int:sale_id>", type="http", auth="user", website=False)
    def download_docx(self, sale_id, **kwargs):
        """
        Generates a native .docx file using the AltChunk method.
        Includes a Bold Green Header (Left/Right) and Page X/Y Footer (Bottom Right).
        """
        sale = request.env["property.sale"].browse(sale_id)
        if not sale.exists():
            return Response("Sale not found", status=404)

        # Assuming your helper methods exist to get the specific contract content
        # If they don't, replace these with: content = sale.compiled_content or ""
        archive = _get_archive(request.env, sale) if '_get_archive' in globals() else False
        content = _get_content(sale, archive) if '_get_content' in globals() else (sale.compiled_content or "")

        try:
            # 1. HTML Preparation & Cleaning
            # Replaces custom pagebreak tags with Word-compatible CSS
            clean = re.sub(
                r'(<p[^>]*>)?\s*(&nbsp;)*\s*(/pagebreak|\[PAGEBREAK\])\s*(&nbsp;)*\s*(/p>)?',
                '<div style="page-break-before: always; clear:both;"></div>',
                content, flags=re.IGNORECASE
            )

            datas = {
                "full_content": Markup(clean) if clean else Markup(""),
                "customer_name": sale.get_full_name() if hasattr(sale, 'get_full_name') else "Customer",
            }

            # Render the QWeb template to HTML
            report = request.env['ir.actions.report'].sudo()
            html_bytes, _ = report._render_qweb_html(
                'contract_managment.action_report_contract', 
                sale.ids, 
                data=datas
            )
            html_str = html_bytes.decode('utf-8')

            # Inject UTF-8 meta tag to ensure special characters (Amharic) render correctly
            if '<head>' in html_str and '<meta charset="utf-8"' not in html_str.lower():
                html_str = html_str.replace('<head>', '<head><meta charset="utf-8">')

            # Strip any company header box from the HTML content
            html_str = re.sub(
                r'<div[^>]*class=["\'][^"\']*(?:header-box|header-main|header-mini|cp-header-box)[^"\']*["\'][^>]*>.*?</div>',
                "", html_str, flags=re.DOTALL
            )

            # 2. Build the .docx (ZIP Container)
            docx_io = io.BytesIO()
            with zipfile.ZipFile(docx_io, 'w', zipfile.ZIP_DEFLATED) as zipf:
                
                # Define Content Types (tells Word which files are XML vs HTML)
                zipf.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="htm" ContentType="text/html"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
</Types>''')

                # Global Relationships
                zipf.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')

                # Document-specific Relationships (Mapping IDs to files)
                zipf.writestr('word/_rels/document.xml.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="htmlChunk" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/aFChunk" Target="chunk.htm"/>
  <Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
</Relationships>''')

#                 # HEADER: Bold Green Text + Bold Bottom Border
#                 zipf.writestr('word/header1.xml', f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
# <w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
#   <w:p>
#     <w:pPr>
#       <w:pBdr><w:bottom w:val="single" w:sz="12" w:space="1" w:color="70AD47"/></w:pBdr>
#       <w:tabs><w:tab w:val="right" w:pos="9072"/></w:tabs>
#     </w:pPr>
#     <w:r>
#       <w:rPr><w:b/><w:color w:val="70AD47"/></w:rPr>
#       <w:t>ቴምር ሆልዲንግ ካምፓኒ</w:t>
#     </w:r>
#     <w:r><w:tab/></w:r>
#     <w:r>
#       <w:rPr><w:b/><w:color w:val="70AD47"/></w:rPr>
#       <w:t>TEMER HOLDING COMPANY</w:t>
#     </w:r>
#   </w:p>
# </w:hdr>''')

#                 # FOOTER: Horizontal Line + "Page X / Y" Aligned Right
#                 zipf.writestr('word/footer1.xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
# <w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
#   <w:p>
#     <w:pPr>
#       <w:pBdr><w:top w:val="single" w:sz="6" w:space="1" w:color="auto"/></w:pBdr>
#       <w:jc w:val="right"/>
#     </w:pPr>
#     <w:r><w:t>Page </w:t></w:r>
#     <w:fldSimple w:instr=" PAGE "/>
#     <w:r><w:t> / </w:t></w:r>
#     <w:fldSimple w:instr=" NUMPAGES "/>
#   </w:p>
# </w:ftr>''')

                # DOCUMENT XML: The skeleton that links everything
                zipf.writestr('word/document.xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    <w:altChunk r:id="htmlChunk" />
    <w:sectPr>
      <w:footerReference w:type="default" r:id="rIdFooter"/>
      <w:pgNumType w:start="1"/>
    </w:sectPr>
  </w:body>
</w:document>''')

                # The actual HTML payload from Odoo
                zipf.writestr('word/chunk.htm', html_str.encode('utf-8'))

            # 3. Final Response Construction
            docx_data = docx_io.getvalue()
            filename = f"Contract_{(sale.name or str(sale_id)).replace('/', '_')}.docx"
            
            return request.make_response(docx_data, headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ])

        except Exception as e:
            return Response("DOCX export failed: " + str(e), status=500)