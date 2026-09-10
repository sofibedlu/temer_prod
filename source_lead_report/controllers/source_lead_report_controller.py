# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo import fields
from datetime import datetime
import logging
import xlsxwriter
import io

_logger = logging.getLogger(__name__)


class SourceLeadReportController(http.Controller):

    def _get_source_ids(self):
        """Get source IDs for '6033', 'Walk In', and 'Website' sources (case-insensitive)"""
        env = request.env
        
        # Find sources by name (case-insensitive) - includes 6033, Walk In, and Website
        env.cr.execute("""
            SELECT id, name 
            FROM utm_source 
            WHERE LOWER(TRIM(name)) IN ('6033', 'walk in', 'walking', 'website')
               OR name ILIKE 'walk in%'
               OR name ILIKE '%walk in%'
               OR name ILIKE 'website%'
               OR name ILIKE '%website%'
        """)
        sources = env.cr.fetchall()
        
        # If found by name, return IDs
        if sources:
            source_ids = [s[0] for s in sources]
            _logger.info(f"Found sources by name: {sources}")
            return source_ids
        
        # If not found by name, try to find by ID (in case 6033 is an ID) or partial match
        env.cr.execute("""
            SELECT id FROM utm_source 
            WHERE id = 6033 
               OR name ILIKE '%walk in%'
               OR name ILIKE '%walking%'
               OR name ILIKE '%website%'
        """)
        sources = env.cr.fetchall()
        source_ids = [s[0] for s in sources] if sources else []
        
        if source_ids:
            _logger.info(f"Found sources by ID/search: {source_ids}")
        else:
            # If still not found, log available sources for debugging
            env.cr.execute("SELECT id, name FROM utm_source LIMIT 20")
            available_sources = env.cr.fetchall()
            _logger.warning(f"Sources '6033', 'Walk In', or 'Website' not found. Available sources: {available_sources}")
        
        return source_ids

    def _get_lead_data(self, date_from=None, date_to=None, source_id=None):
        """Get lead data filtered by source and date range"""
        env = request.env
        
        # Get allowed source IDs
        if source_id:
            allowed_source_ids = [source_id]
        else:
            allowed_source_ids = self._get_source_ids()
        
        if not allowed_source_ids:
            return []
        
        # Build domain
        domain = [('source_ids', 'in', allowed_source_ids)]
        
        # Add date filter if provided
        if date_from:
            date_from_obj = fields.Date.from_string(date_from)
            domain.append(('create_date', '>=', date_from_obj))
        
        if date_to:
            date_to_obj = fields.Date.from_string(date_to)
            # Add end of day
            date_to_datetime = datetime.combine(date_to_obj, datetime.max.time())
            domain.append(('create_date', '<=', date_to_datetime))
        
        # Search leads
        leads = request.env['temer.lead'].sudo().search(domain, order='create_date desc')
        
        # Build result data
        result_data = []
        for lead in leads:
            # Get lead name (computed from customer_name and site_ids)
            lead_name = lead.name or ''
            
            # Get phone numbers from phone_ids (One2many)
            phone_numbers = ', '.join([phone.phone for phone in lead.phone_ids if phone.phone]) if lead.phone_ids else ''
            
            # Get salesperson name
            salesperson_name = lead.user_id.partner_id.name if lead.user_id and lead.user_id.partner_id else ''
            
            # Get status
            status = lead.state or ''
            
            # Get created date
            created_date = lead.create_date.strftime('%Y-%m-%d %H:%M:%S') if lead.create_date else ''
            
            # Get created by
            created_by = lead.create_uid.partner_id.name if lead.create_uid and lead.create_uid.partner_id else ''
            
            result_data.append({
                'id': lead.id,
                'name': lead_name,
                'phone_numbers': phone_numbers,
                'salesperson_name': salesperson_name,
                'status': status,
                'created_date': created_date,
                'created_by': created_by,
            })
        
        return result_data

    @http.route('/source_lead_report/api/get_sources', type='json', auth='user')
    def api_get_sources(self, **kwargs):
        """API endpoint to get available sources (6033, Walk In, and Website only)"""
        try:
            env = request.env
            sources = []
            
            # Get allowed source IDs
            allowed_source_ids = self._get_source_ids()
            
            if allowed_source_ids:
                env.cr.execute("""
                    SELECT id, name 
                    FROM utm_source 
                    WHERE id IN %s
                    ORDER BY name
                """, (tuple(allowed_source_ids),))
                results = env.cr.fetchall()
                sources = [{'id': r[0], 'name': r[1]} for r in results]
            
            return {
                'success': True,
                'sources': sources,
            }
        except Exception as e:
            _logger.error(f"Error getting sources: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'sources': [],
            }

    @http.route('/source_lead_report/api/get_data', type='json', auth='user')
    def api_get_data(self, date_from=None, date_to=None, source_id=None, **kwargs):
        """API endpoint to get lead data"""
        try:
            source_id_int = int(source_id) if source_id else None
            data = self._get_lead_data(date_from, date_to, source_id_int)
            
            # Get count
            count = len(data) if data else 0
            
            return {
                'success': True,
                'data': data,
                'count': count,
            }
        except Exception as e:
            _logger.error(f"Error getting lead data: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
            }

    def _filter_data_by_search(self, data, search_text):
        """Filter data by search text"""
        if not search_text or not search_text.strip():
            return data
        
        search_lower = search_text.lower().strip()
        filtered_data = []
        
        for lead in data:
            name = (lead.get('name', '') or '').lower()
            phone_numbers = (lead.get('phone_numbers', '') or '').lower()
            salesperson = (lead.get('salesperson_name', '') or '').lower()
            created_by = (lead.get('created_by', '') or '').lower()
            status = (lead.get('status', '') or '').lower()
            
            if (search_lower in name or 
                search_lower in phone_numbers or 
                search_lower in salesperson or 
                search_lower in created_by or 
                search_lower in status):
                filtered_data.append(lead)
        
        return filtered_data

    @http.route('/source_lead_report/api/export_excel', type='http', auth='user', methods=['POST'], csrf=False)
    def api_export_excel(self, date_from=None, date_to=None, source_id=None, search_text=None, **kwargs):
        """Export lead report to Excel"""
        try:
            source_id_int = int(source_id) if source_id else None
            data = self._get_lead_data(date_from, date_to, source_id_int)
            
            # Filter by search text if provided
            if search_text:
                data = self._filter_data_by_search(data, search_text)
            
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Source Lead Report')
            
            # Header format
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#366092',
                'font_color': 'white',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
            })
            
            # Data format
            data_format = workbook.add_format({
                'border': 1,
                'align': 'left',
            })
            
            date_format = workbook.add_format({
                'border': 1,
                'align': 'left',
                'num_format': 'yyyy-mm-dd hh:mm:ss',
            })
            
            row = 0
            
            # Write title
            title_format = workbook.add_format({
                'bold': True,
                'font_size': 14,
                'align': 'center',
            })
            worksheet.merge_range(row, 0, row, 6, 'Source Lead Report', title_format)
            row += 1
            
            # Write date range info
            info_format = workbook.add_format({
                'align': 'center',
            })
            date_range_text = f"Date From: {date_from or 'All'} | Date To: {date_to or 'All'}"
            worksheet.merge_range(row, 0, row, 6, date_range_text, info_format)
            row += 2
            
            # Write headers
            headers = ['Name', 'Phone Numbers', 'Salesperson', 'Created on', 'Status', 'Created By']
            col = 0
            for header in headers:
                worksheet.write(row, col, header, header_format)
                col += 1
            row += 1
            
            # Write data
            for lead in data:
                col = 0
                worksheet.write(row, col, lead.get('name', ''), data_format)
                col += 1
                worksheet.write(row, col, lead.get('phone_numbers', ''), data_format)
                col += 1
                worksheet.write(row, col, lead.get('salesperson_name', ''), data_format)
                col += 1
                worksheet.write(row, col, lead.get('created_date', ''), date_format)
                col += 1
                worksheet.write(row, col, lead.get('status', ''), data_format)
                col += 1
                worksheet.write(row, col, lead.get('created_by', ''), data_format)
                row += 1
            
            # Set column widths
            worksheet.set_column(0, 0, 40)  # Name
            worksheet.set_column(1, 1, 25)  # Phone Numbers
            worksheet.set_column(2, 2, 20)  # Salesperson
            worksheet.set_column(3, 3, 20)  # Created on
            worksheet.set_column(4, 4, 15)  # Status
            worksheet.set_column(5, 5, 20)  # Created By
            
            workbook.close()
            output.seek(0)
            
            filename = f'Source_Lead_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            
            return request.make_response(
                output.read(),
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                ],
            )
        except Exception as e:
            _logger.error(f"Error exporting Excel: {str(e)}", exc_info=True)
            return request.make_response(f"Error: {str(e)}", status=500)

    @http.route('/source_lead_report/api/export_pdf', type='http', auth='user', methods=['POST'], csrf=False)
    def api_export_pdf(self, date_from=None, date_to=None, source_id=None, search_text=None, **kwargs):
        """Export lead report to PDF"""
        try:
            source_id_int = int(source_id) if source_id else None
            data = self._get_lead_data(date_from, date_to, source_id_int)
            
            # Filter by search text if provided
            if search_text:
                data = self._filter_data_by_search(data, search_text)
            
            # Build HTML content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Source Lead Report</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 20px;
                    }}
                    h1 {{
                        text-align: center;
                        color: #366092;
                    }}
                    .date-range {{
                        text-align: center;
                        margin-bottom: 20px;
                        font-weight: bold;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 20px;
                    }}
                    th {{
                        background-color: #366092;
                        color: white;
                        padding: 10px;
                        text-align: left;
                        border: 1px solid #ddd;
                    }}
                    td {{
                        padding: 8px;
                        border: 1px solid #ddd;
                    }}
                    tr:nth-child(even) {{
                        background-color: #f2f2f2;
                    }}
                    .no-data {{
                        text-align: center;
                        padding: 20px;
                        color: #999;
                    }}
                </style>
            </head>
            <body>
                <h1>Source Lead Report</h1>
                <div class="date-range">
                    Date From: {date_from or 'All'} | Date To: {date_to or 'All'}
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Phone Numbers</th>
                            <th>Salesperson</th>
                            <th>Created on</th>
                            <th>Status</th>
                            <th>Created By</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            if not data:
                html_content += '<tr><td colspan="6" class="no-data">No data available</td></tr>'
            else:
                for lead in data:
                    html_content += f"""
                        <tr>
                            <td>{lead.get('name', '')}</td>
                            <td>{lead.get('phone_numbers', '')}</td>
                            <td>{lead.get('salesperson_name', '')}</td>
                            <td>{lead.get('created_date', '')}</td>
                            <td>{lead.get('status', '')}</td>
                            <td>{lead.get('created_by', '')}</td>
                        </tr>
                    """
            
            html_content += """
                    </tbody>
                </table>
                <script>
                    window.onload = function() {
                        window.print();
                    };
                    window.onafterprint = function() {
                        window.close();
                    };
                </script>
            </body>
            </html>
            """
            
            return request.make_response(
                html_content,
                headers=[
                    ('Content-Type', 'text/html'),
                ],
            )
        except Exception as e:
            _logger.error(f"Error exporting PDF: {str(e)}", exc_info=True)
            return request.make_response(f"Error: {str(e)}", status=500)

