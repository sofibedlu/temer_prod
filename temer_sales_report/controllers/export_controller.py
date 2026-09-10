# -*- coding: utf-8 -*-
import io
import json
import xlsxwriter
from odoo import http, _
from odoo.exceptions import AccessError
from odoo.http import request, content_disposition

from odoo.addons.temer_sales_report.models.temer_report_export import (
    EXPORT_TOKEN_PARAM_PREFIX,
    SALES_DEAL_CLOSED_DOMAIN,
)

REPORT_USER_GROUP = 'temer_sales_report.group_temer_sales_report_user'

# Header color matching the Excel template (dark teal)
HEADER_BG = '#1F6B75'
HEADER_FG = '#FFFFFF'
ROW_ALT_BG = '#E8F4F5'   # light teal for alternating rows
ROW_BG = '#FFFFFF'


def _make_workbook(sheet_configs):
    """
    sheet_configs: list of dicts:
        {
            'name': sheet tab name,
            'headers': [list of column header strings],
            'rows': [list of lists (row data)],
        }
    Returns bytes of the xlsx file.
    """
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    header_fmt = workbook.add_format({
        'bold': True,
        'font_color': HEADER_FG,
        'bg_color': HEADER_BG,
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 11,
    })
    row_fmt = workbook.add_format({
        'bg_color': ROW_BG,
        'border': 1,
        'valign': 'vcenter',
    })
    row_alt_fmt = workbook.add_format({
        'bg_color': ROW_ALT_BG,
        'border': 1,
        'valign': 'vcenter',
    })
    money_fmt = workbook.add_format({
        'bg_color': ROW_BG,
        'border': 1,
        'num_format': '#,##0.00',
        'valign': 'vcenter',
    })
    money_alt_fmt = workbook.add_format({
        'bg_color': ROW_ALT_BG,
        'border': 1,
        'num_format': '#,##0.00',
        'valign': 'vcenter',
    })

    for cfg in sheet_configs:
        ws = workbook.add_worksheet(cfg['name'])
        headers = cfg['headers']
        rows = cfg['rows']

        for col, h in enumerate(headers):
            ws.write(0, col, h, header_fmt)
            ws.set_column(col, col, max(15, len(str(h)) + 4))

        for row_idx, row_data in enumerate(rows):
            excel_row = row_idx + 1
            fmt = row_alt_fmt if row_idx % 2 == 1 else row_fmt
            mfmt = money_alt_fmt if row_idx % 2 == 1 else money_fmt
            for col, val in enumerate(row_data):
                if isinstance(val, float) and val != int(val):
                    ws.write_number(excel_row, col, val, mfmt)
                else:
                    ws.write(excel_row, col, val if val is not None else '', fmt)

        ws.set_row(0, 20)

    workbook.close()
    output.seek(0)
    return output.read()


class TemerSalesReportExport(http.Controller):

    def _check_report_user(self):
        if not request.env.user.has_group(REPORT_USER_GROUP):
            raise AccessError(_('You are not allowed to export sales reports.'))

    def _records_from_request(self, model_name, base_domain):
        """Load records selected for export without putting long ID lists in the URL."""
        token = request.params.get('token')
        if token:
            id_list = self._ids_from_export_token(token, model_name)
        else:
            id_list = self._ids_from_legacy_param()

        records = request.env[model_name].browse(id_list).exists()
        if base_domain:
            records = records.filtered_domain(base_domain)
        return records

    def _ids_from_export_token(self, token, model_name):
        key = '%s%s.%s' % (EXPORT_TOKEN_PARAM_PREFIX, request.env.uid, token)
        param_model = request.env['ir.config_parameter'].sudo()
        token_record = param_model.search([('key', '=', key)], limit=1)
        if not token_record:
            return []
        try:
            payload = json.loads(token_record.value or '{}')
        finally:
            token_record.unlink()
        if payload.get('model') != model_name:
            return []
        return payload.get('ids') or []

    def _ids_from_legacy_param(self):
        ids_param = request.params.get('ids', '')
        if not ids_param:
            return []
        id_list = []
        for part in ids_param.split(','):
            part = part.strip()
            if part.isdigit():
                id_list.append(int(part))
        return id_list

    def _xlsx_response(self, filename, sheet_name, headers, rows):
        data = _make_workbook([{'name': sheet_name, 'headers': headers, 'rows': rows}])
        return request.make_response(data, headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', content_disposition(filename)),
        ])

    @http.route('/temer_sales_report/export/sales_deal_closed', type='http', auth='user')
    def export_sales_deal_closed(self, **kwargs):
        self._check_report_user()
        records = self._records_from_request('property.sale', SALES_DEAL_CLOSED_DOMAIN)
        state_labels = dict(request.env['property.sale']._fields['state'].selection)
        headers = [
            'Wing Name', 'Sales Supervisor', 'Sales Consultant', 'Site',
            'Property Name', 'Property Type', 'Unit Type',
            'Gross Area', 'Net Area', 'Fiscal Year', 'Period', 'Date',
            'Property Value', 'Cash Collection', 'Is Legacy', 'State',
        ]
        rows = []
        for r in records:
            rows.append([
                r.report_wing_id.name or '',
                r.report_supervisor_id.name.name if r.report_supervisor_id and r.report_supervisor_id.name else '',
                r.sales_person.name if r.sales_person else '',
                r.site_id.name or '',
                r.property_id.name or '',
                r.report_property_type or '',
                r.report_unit_type or '',
                r.report_gross_area or 0.0,
                r.report_net_area or 0.0,
                r.report_fiscal_year or '',
                r.report_period or '',
                r.report_date_display or '',
                r.sale_price or 0.0,
                r.report_cash_collection or 0.0,
                'Yes' if r.report_property_is_legacy else 'No',
                state_labels.get(r.state, r.state or ''),
            ])
        return self._xlsx_response('Sales_Deal_Closed.xlsx', 'Sales Deal Closed', headers, rows)

    @http.route('/temer_sales_report/export/lead_generated', type='http', auth='user')
    def export_lead_generated(self, **kwargs):
        self._check_report_user()
        records = self._records_from_request('temer.lead', [])
        headers = ['Wing Name', 'Sales Supervisor', 'Sales Consultant', 'Fiscal Year', 'Period', 'Date', 'Lead Source', 'Lead']
        rows = []
        for r in records:
            sup, wing = self._resolve_lead_hierarchy(r)
            rows.append([
                wing.name if wing else '',
                sup.name.name if sup and sup.name else '',
                r.user_id.name or '',
                r.report_fiscal_year or '',
                r.report_period or '',
                r.report_date_display or '',
                ', '.join(r.source_ids.mapped('name')) if r.source_ids else '',
                r.name or '',
            ])
        return self._xlsx_response('Lead_Generated.xlsx', 'Lead Generated', headers, rows)

    @http.route('/temer_sales_report/export/follow_up', type='http', auth='user')
    def export_follow_up(self, **kwargs):
        self._check_report_user()
        records = self._records_from_request('temer.lead', [('state', '=', 'follow_up')])
        headers = ['Wing Name', 'Sales Supervisor', 'Sales Consultant', 'Fiscal Year', 'Period', 'Date', 'Lead Source', 'Lead']
        rows = []
        for r in records:
            sup, wing = self._resolve_lead_hierarchy(r)
            rows.append([
                wing.name if wing else '',
                sup.name.name if sup and sup.name else '',
                r.user_id.name or '',
                r.report_fiscal_year or '',
                r.report_period or '',
                r.report_date_display or '',
                ', '.join(r.source_ids.mapped('name')) if r.source_ids else '',
                r.name or '',
            ])
        return self._xlsx_response('Follow_Up.xlsx', 'Follow Up', headers, rows)

    @http.route('/temer_sales_report/export/office_visit', type='http', auth='user')
    def export_office_visit(self, **kwargs):
        self._check_report_user()
        records = self._records_from_request(
            'temer.lead.followup',
            [('activity_type', '=', 'office_visit')],
        )
        headers = ['Wing Name', 'Sales Supervisor', 'Sales Consultant', 'Date', 'Activity Type', 'Lead']
        return self._xlsx_response(
            'Office_Visit.xlsx',
            'Office Visit',
            headers,
            self._followup_rows(records),
        )

    @http.route('/temer_sales_report/export/site_visit', type='http', auth='user')
    def export_site_visit(self, **kwargs):
        self._check_report_user()
        records = self._records_from_request(
            'temer.lead.followup',
            [('activity_type', '=', 'site_visit')],
        )
        headers = ['Wing Name', 'Sales Supervisor', 'Sales Consultant', 'Date', 'Activity Type', 'Lead']
        return self._xlsx_response(
            'Site_Visit.xlsx',
            'Site Visit',
            headers,
            self._followup_rows(records),
        )

    @http.route('/temer_sales_report/export/reservation_history', type='http', auth='user')
    def export_reservation_history(self, **kwargs):
        self._check_report_user()
        records = self._records_from_request('property.reservation', [])
        status_labels = dict(request.env['property.reservation']._fields['status'].selection)
        headers = [
            'Property Name', 'Property Type', 'Unit Type',
            'Salesperson', 'Customer', 'Reservation Type', 'Requested',
            'End Date', 'Canceled Time', 'Reserved By', 'Status',
            'Reservation Payment',
        ]
        rows = []
        for r in records:
            rows.append([
                r.property_id.name or '',
                r.report_property_type or '',
                r.report_unit_type or '',
                r.salesperson_ids.name or '',
                r.partner_id.name or '',
                r.reservation_type_id.name or '',
                str(r.create_date) if r.create_date else '',
                str(r.expire_date) if r.expire_date else '',
                str(r.canceled_time) if r.canceled_time else '',
                r.create_uid.name or '',
                status_labels.get(r.status, r.status or ''),
                r.report_total_payment or 0.0,
            ])
        return self._xlsx_response(
            'Reservation_Report.xlsx',
            'Reservation Report',
            headers,
            rows,
        )

    def _followup_rows(self, records):
        rows = []
        for r in records:
            wing = r.report_wing_id
            sup = r.report_supervisor_id
            rows.append([
                wing.name if wing else '',
                sup.name.name if sup and sup.name else '',
                r.user_id.name or '',
                r.report_date_display or '',
                dict(r._fields['activity_type'].selection).get(r.activity_type, r.activity_type or ''),
                r.lead_id.name or '',
            ])
        return rows

    def _resolve_lead_hierarchy(self, lead):
        """Return (supervisor, wing) for a lead record."""
        sup = lead.supervisor_id
        wing = lead.wing_id
        if not sup or not wing:
            user_id = lead.user_id.id if lead.user_id else False
            if user_id:
                mapping = lead.env['property.salesperson.mapping'].search(
                    [('user_id', '=', user_id)], limit=1
                )
                if mapping and mapping.supervisor_id:
                    if not sup:
                        sup = mapping.supervisor_id
                    if not wing:
                        team = lead.env['property.sales.team'].search(
                            [('supervisor_ids', 'in', mapping.supervisor_id.id)], limit=1
                        )
                        if team:
                            wing = lead.env['property.sales.wing'].search(
                                [('team_ids', 'in', team.id)], limit=1
                            )
        return sup, wing
