import base64
import io
import zipfile
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PropertyContractPrintLetterWizard(models.TransientModel):
    _inherit = 'property.print.letter.wizard'

    export_format = fields.Selection([
        ('pdf', 'PDF'),
        ('docx', 'Word Document (.docx)'),
    ], string='Export Format', default='pdf', required=True)

    def action_print_letter(self):
        self.ensure_one()

        if self.export_format == 'pdf':
            return super(PropertyContractPrintLetterWizard, self).action_print_letter()

        if not self.letterhead_id:
            raise UserError(_("Please select a Letterhead."))
        
        if self.letter_type == 'custom' and not self.custom_template_id:
            raise UserError(_("Please select a Custom Template."))

        ctx = dict(
            self.env.context,
            letterhead_id=self.letterhead_id.id,
            letter_date=self.letter_date,
            letter_number=self.letter_number,
        )
        if self.letter_type == 'custom':
            ctx['custom_template_id'] = self.custom_template_id.id

        # Determine Report Action
        report_ref = 'collection_management.action_report_collection_letter'
        if self.letter_type == 'warning':
            report_ref = 'collection_management.action_report_warning_letter'
        elif self.letter_type == 'termination':
            report_ref = 'collection_management.action_report_termination_letter'
        elif self.letter_type == 'custom':
            report_ref = 'collection_letter_template.action_report_dynamic_collection_letter'

        # Render HTML
        report = self.env['ir.actions.report'].with_context(ctx).sudo()
        html_bytes, _ = report._render_qweb_html(report_ref, self.installment_id.ids)
        html_str = html_bytes.decode('utf-8')
        
        html_str = html_str.replace(
            'style="max-height:100px;"', 
            'width="150" height="80" style="width:150px; height:80px;"'
        )
        
        html_str = html_str.replace(
            'style="max-height: 140px; width: auto;"', 
            'width="180" height="140" style="width:180px; height:140px;"'
        )

        font_style = """
        <style>
            body { font-family: 'Arial Unicode MS', 'Noto Sans Ethiopic', sans-serif; font-size: 11pt; }
            .page { width: 100% !important; margin: 0 !important; padding: 0 !important; }
            table { border-collapse: collapse; width: 100%; }
        </style>
        """
        if '</head>' in html_str:
            html_str = html_str.replace('</head>', font_style + '</head>')
        else:
            html_str = font_style + html_str

        # UTF-8 meta tag for Amharic
        if '<head>' in html_str and '<meta charset="utf-8"' not in html_str.lower():
            html_str = html_str.replace('<head>', '<head><meta charset="utf-8">')
            
        # Remove inline Footer
        html_str = re.sub(r'<div class="footer">.*?</div>\s*</div>', '', html_str, flags=re.DOTALL)
            
        # ZIP & EXPORT (WITH NATIVE WORD FOOTER)
        docx_io = io.BytesIO()
        with zipfile.ZipFile(docx_io, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8"?>
                <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
                <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
                <Default Extension="xml" ContentType="application/xml"/>
                <Default Extension="htm" ContentType="text/html"/>
                <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
                <Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
                </Types>''')

            zipf.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8"?>
                <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
                </Relationships>''')

            zipf.writestr('word/_rels/document.xml.rels', '''<?xml version="1.0" encoding="UTF-8"?>
                <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                <Relationship Id="htmlChunk" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/aFChunk" Target="chunk.htm"/>
                <Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
                </Relationships>''')

            zipf.writestr('word/document.xml', '''<?xml version="1.0" encoding="UTF-8"?>
                <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
                <w:body>
                    <w:altChunk r:id="htmlChunk"/>
                    <w:sectPr>
                    <w:footerReference w:type="default" r:id="rIdFooter"/>
                    </w:sectPr>
                </w:body>
                </w:document>''')

            zipf.writestr('word/footer1.xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                <w:p>
                    <w:pPr>
                    <w:pBdr>
                        <w:top w:val="single" w:sz="6" w:space="1" w:color="CCCCCC"/>
                    </w:pBdr>
                    <w:jc w:val="center"/>
                    </w:pPr>
                    <w:r>
                    <w:rPr>
                        <w:sz w:val="18"/>
                        <w:color w:val="555555"/>
                    </w:rPr>
                    <w:t>temerrealestate@gmail.com / 0118547115 , 0118722424 , 0909667733</w:t>
                    </w:r>
                </w:p>
                <w:p>
                    <w:pPr><w:jc w:val="center"/></w:pPr>
                    <w:r>
                    <w:rPr>
                        <w:sz w:val="18"/>
                        <w:color w:val="555555"/>
                    </w:rPr>
                    <w:t>Address: Sarbet on the road to Kera next to Salvatore Woldemariam Building</w:t>
                    </w:r>
                </w:p>
                </w:ftr>''')

            zipf.writestr('word/chunk.htm', html_str.encode('utf-8'))
            
        # Create Attachment
        installment_name = self.installment_id.name or 'Installment'
        file_name = f"{installment_name.replace('/', '_')}.docx"
        
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': base64.b64encode(docx_io.getvalue()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }