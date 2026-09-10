from odoo import models, fields, api, _
from odoo.exceptions import UserError
import io
import base64
import xlsxwriter

class TemerCommissionReportWizard(models.TransientModel):
    _name = 'temer.commission.report.wizard'
    _description = 'Commission Report Wizard'

    date_from = fields.Date(string='Date From', required=True, default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(string='Date To', required=True, default=fields.Date.context_today)
    tax_percentage = fields.Float(string="Income Tax %", default=35.0, help="Percentage to deduct from Total Commission")
    
    excel_file = fields.Binary('Excel Report')
    file_name = fields.Char('File Name')

    def action_generate_xlsx(self):
        self.ensure_one()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("Commission Report")

        # --- Formats ---
        header_format = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FFFFFF', 'text_wrap': True
        })
        color_map = {
            'salesperson': '#C6EFCE',    # Green
            'supervisor': '#E2EFDA',     # Light Green
            'sales_manager': '#D9D9D9',  # Grey
            'wing_manager': '#BDD7EE',   # Blue
            'other': '#F8CBAD',          # Orange
        }
        total_row_format = workbook.add_format({
            'bold': True, 'bg_color': '#BF8F00', 'border': 1, 'num_format': '#,##0.00'
        })
        
        # Number Formats
        num_fmt = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        pct_fmt = workbook.add_format({'border': 1, 'num_format': '0.00%'})
        
        # --- Headers ---
        headers = [
            "NO", "SALES NAME", "AGR.NO", "PURCHASE AMOUNT", "BEFORE VAT", 
            "COMMISSION %", "TOTAL COMMISSION", "INCOME TAX", "NET PAYMENT", 
            "PAID %", "PAYMENT"
        ]
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
        
        sheet.set_column(0, 0, 5)   # NO
        sheet.set_column(1, 1, 25)  # Name
        sheet.set_column(2, 2, 15)  # AGR
        sheet.set_column(3, 8, 15)  # Amounts
        sheet.set_column(9, 10, 10) # Status

        # --- Data Fetching ---
        domain = [
            ('create_date', '>=', self.date_from),
            ('create_date', '<=', self.date_to),
            ('state', '!=', 'cancelled')
        ]

        commission_sheets = self.env['temer.commission.sheet'].search(domain, order='sale_id, id')

        row = 1
        serial_no = 1
        
        # track payment sequence per sale
        sale_sheet_counts = {} 

        for comm_sheet in commission_sheets:
            sale = comm_sheet.sale_id

            all_sheets_for_sale = self.env['temer.commission.sheet'].search([
                ('sale_id', '=', sale.id),
                ('state', '!=', 'cancelled')
            ], order='id asc')
            
            sheet_ids = all_sheets_for_sale.ids
            try:
                current_index = sheet_ids.index(comm_sheet.id) + 1
            except ValueError:
                current_index = 1
            
            total_sheets = len(sheet_ids)
            
            if total_sheets == 1:
                payment_label = "FULL"
            elif current_index == total_sheets:
                payment_label = "LAST"
            elif current_index == 1:
                payment_label = "1ST"
            elif current_index == 2:
                payment_label = "2ND"
            else:
                payment_label = f"{current_index}TH"

            payout_percentage = comm_sheet.collected_percentage if comm_sheet.collected_percentage else (100.0 / total_sheets if total_sheets else 100.0)

            agr_no = getattr(sale, 'contract_number', sale.name) 
            
            purchase_amount = comm_sheet.sale_amount
            before_vat = purchase_amount / 1.15 if purchase_amount else 0.0

            # Group Totals
            group_comm = 0.0
            group_tax = 0.0
            group_net = 0.0
            
            start_row = row

            for line in comm_sheet.line_ids:
                bg_color = color_map.get(line.role, '#FFFFFF')
                cell_fmt = workbook.add_format({'border': 1, 'bg_color': bg_color})
                num_fmt_c = workbook.add_format({'border': 1, 'bg_color': bg_color, 'num_format': '#,##0.00'})
                pct_fmt_c = workbook.add_format({'border': 1, 'bg_color': bg_color, 'num_format': '0.00%'})
                
                # --- Formulas ---
                comm_pct = line.percentage / 100.0

                calculated_comm = before_vat * comm_pct * (payout_percentage / 100.0)
                
                # Income Tax
                income_tax = calculated_comm * (self.tax_percentage / 100.0)
                
                # Net Payment 
                net_payment = calculated_comm - income_tax
                
                # Accumulate
                group_comm += calculated_comm
                group_tax += income_tax
                group_net += net_payment

                # Write Columns
                sheet.write(row, 0, serial_no, cell_fmt)
                sheet.write(row, 1, line.partner_id.name, cell_fmt)
                sheet.write(row, 2, agr_no, cell_fmt)
                sheet.write(row, 3, purchase_amount, num_fmt_c)
                sheet.write(row, 4, before_vat, num_fmt_c)
                sheet.write(row, 5, comm_pct, pct_fmt_c)
                sheet.write(row, 6, calculated_comm, num_fmt_c)
                sheet.write(row, 7, income_tax, num_fmt_c)
                sheet.write(row, 8, net_payment, num_fmt_c)
                sheet.write(row, 9, payout_percentage / 100.0, pct_fmt_c)
                sheet.write(row, 10, payment_label, cell_fmt)
                
                row += 1

            # --- Total Row ---
            sheet.write(row, 1, "TOTAL", total_row_format)
            sheet.write(row, 6, group_comm, total_row_format)
            sheet.write(row, 7, group_tax, total_row_format)
            sheet.write(row, 8, group_net, total_row_format)
            
            for c in [0, 2, 3, 4, 5, 9, 10]:
                sheet.write(row, c, "", total_row_format)

            row += 1
            serial_no += 1

        workbook.close()
        output.seek(0)
        
        self.excel_file = base64.b64encode(output.read())
        self.file_name = f"Commission_Report_{self.date_from}_{self.date_to}.xlsx"

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model={self._name}&id={self.id}&field=excel_file&download=true&filename={self.file_name}',
            'target': 'self',
        }