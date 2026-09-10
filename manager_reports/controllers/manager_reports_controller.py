# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo import fields
from odoo.exceptions import AccessError
from datetime import datetime, timedelta
import logging
import io
import base64

_logger = logging.getLogger(__name__)


class ManagerReportsController(http.Controller):

    def _check_weekly_reports_access(self):
        """Raise AccessError if current user does not have Weekly Reports privilege."""
        if not request.env.user.has_group('manager_reports.group_weekly_reports'):
            raise AccessError('You do not have access to Weekly Reports (Weekly Sales By Wing / Weekly Report).')

    @http.route('/manager_reports/api/get_wings', type='json', auth='user', methods=['POST'])
    def api_get_wings(self, **kwargs):
        """Get all wings for filter dropdown"""
        try:
            env = request.env
            wings = []
            # Prefer the same wing model used by working modules (sales_plan_report/supervisor_sales_report)
            if 'property.sales.wing' in env:
                wing_records = env['property.sales.wing'].sudo().search([])
                wings = [{'id': w.id, 'name': w.name or f'Wing {w.id}'} for w in wing_records]
            else:
                # Fallback to direct SQL if ORM model is not loaded in this DB
                try:
                    env.cr.execute("SELECT id, name FROM property_sales_wing ORDER BY name")
                    wings = [{'id': r[0], 'name': r[1] or f'Wing {r[0]}'} for r in env.cr.fetchall()]
                except Exception:
                    # Last fallback: old config model if exists
                    if 'property.wing.config' in env:
                        wing_records = env['property.wing.config'].sudo().search([])
                        wings = [{'id': w.id, 'name': getattr(w, 'display_name', None) or getattr(w, 'wing_name', None) or f'Wing {w.id}'} for w in wing_records]
            return {
                'success': True,
                'wings': wings
            }
        except Exception as e:
            _logger.error(f"Error getting wings: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'wings': []
            }

    def _get_date_range(self, date_from=None, date_to=None):
        """Get date range from parameters"""
        from datetime import date
        today = fields.Date.today()
        
        if date_from:
            try:
                if isinstance(date_from, str):
                    date_from = fields.Date.from_string(date_from)
                elif isinstance(date_from, date):
                    date_from = date_from
                else:
                    date_from = today
            except:
                date_from = today
        else:
            date_from = today
            
        if date_to:
            try:
                if isinstance(date_to, str):
                    date_to = fields.Date.from_string(date_to)
                elif isinstance(date_to, date):
                    date_to = date_to
                else:
                    date_to = today
            except:
                date_to = today
        else:
            date_to = today
            
        return date_from, date_to

    # ============================================
    # Weekly Sales Report By Wing (exact Excel layout)
    # ============================================

    @http.route('/manager_reports/api/weekly_sales_by_wing_data', type='json', auth='user', methods=['POST'])
    def api_weekly_sales_by_wing_data(self, **kwargs):
        """Exact Weekly Sales Report By Wing: main table by site×wing, summary by wing, opening stock. Uses property.site if available."""
        self._check_weekly_reports_access()
        try:
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            date_from_obj, date_to_obj = self._get_date_range(date_from, date_to)
            from datetime import time
            env = request.env
            date_from_dt = datetime.combine(date_from_obj, time.min)
            date_to_dt = datetime.combine(date_to_obj, time.max)
            date_from_str = date_from_obj.strftime('%Y-%m-%d')
            date_to_str = date_to_obj.strftime('%Y-%m-%d')

            wings = []
            wing_names = {}
            if 'property.sales.wing' in env:
                for w in env['property.sales.wing'].sudo().search([], order='name'):
                    wings.append({'id': w.id, 'name': w.name or f'Wing {w.id}'})
                    wing_names[w.id] = w.name or f'Wing {w.id}'
            else:
                try:
                    env.cr.execute("SELECT id, name FROM property_sales_wing ORDER BY name")
                    for r in env.cr.fetchall():
                        wings.append({'id': r[0], 'name': r[1] or f'Wing {r[0]}'})
                        wing_names[r[0]] = r[1] or f'Wing {r[0]}'
                except Exception:
                    pass
            other_wing_id = None
            for w in wings:
                if (w.get('name') or '').upper().strip() in ('OTHER', 'OTHER DEP.', 'OTHER DEP'):
                    other_wing_id = w['id']
                    break
            if other_wing_id is None:
                wings.append({'id': 0, 'name': 'OTHER DEP.'})
                wing_names[0] = 'OTHER DEP.'
                other_wing_id = 0

            sites_rows = []
            summary_by_wing = {w['id']: {'sold': 0, 'total': 0.0, 'paid': 0.0, 'reserved': 0} for w in wings}
            opening_stock_by_type = {'residence': {'qty': 0, 'value': 0.0}, 'shops': {'qty': 0, 'value': 0.0}, 'total': {'qty': 0, 'value': 0.0}}

            has_site = False
            try:
                env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'property_property' AND column_name IN ('site', 'site_id')")
                if env.cr.fetchone():
                    has_site = True
            except Exception:
                pass

            if has_site and wings:
                site_col = 'site_id'  # Odoo default for Many2one
                try:
                    env.cr.execute("SELECT 1 FROM property_property LIMIT 1")
                    env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'property_property' AND column_name = 'site'")
                    if env.cr.fetchone():
                        site_col = 'site'
                except Exception:
                    pass

                env.cr.execute("SELECT id, name FROM property_site ORDER BY name")
                site_list = env.cr.fetchall()
                for site_id, site_name in site_list:
                    opening = 0
                    available = 0
                    env.cr.execute("""
                        SELECT COUNT(*) FROM property_property p
                        WHERE p.""" + site_col + """ = %s AND p.sale_rent = 'for_sale'
                        AND p.create_date::date <= %s
                        AND NOT EXISTS (
                            SELECT 1 FROM property_sale ps
                            WHERE ps.property_id = p.id AND ps.state = 'confirm' AND ps.create_date::date < %s
                        )
                    """, (site_id, date_from_str, date_from_str))
                    row = env.cr.fetchone()
                    opening = (row[0] or 0) if row else 0
                    env.cr.execute("""
                        SELECT COUNT(*) FROM property_property p
                        WHERE p.""" + site_col + """ = %s AND p.sale_rent = 'for_sale'
                        AND p.create_date::date <= %s
                        AND NOT EXISTS (
                            SELECT 1 FROM property_sale ps
                            WHERE ps.property_id = p.id AND ps.state = 'confirm' AND ps.create_date::date <= %s
                        )
                    """, (site_id, date_to_str, date_to_str))
                    row = env.cr.fetchone()
                    available = (row[0] or 0) if row else 0

                    per_wing = {}
                    total_sold_site = 0
                    total_reserved_site = 0
                    for w in wings:
                        wid = w['id']
                        wing_cond = "pr.wing_id IS NULL" if wid == 0 else "pr.wing_id = %s"
                        params_sold = [site_id, date_from_dt, date_to_dt]
                        if wid != 0:
                            params_sold.append(wid)
                        env.cr.execute("""
                            SELECT COUNT(*), COALESCE(SUM(ps.sale_price), 0)
                            FROM property_sale ps
                            JOIN property_property p ON p.id = ps.property_id
                            LEFT JOIN property_reservation pr ON pr.id = ps.reservation_id
                            WHERE p.""" + site_col + """ = %s AND ps.state = 'confirm'
                            AND ps.create_date >= %s AND ps.create_date <= %s
                            AND """ + wing_cond + """
                        """, tuple(params_sold))
                        row = env.cr.fetchone()
                        sold_c, sold_v = (row[0] or 0, float(row[1] or 0)) if row else (0, 0.0)
                        wing_cond_r = "pr.wing_id IS NULL" if wid == 0 else "pr.wing_id = %s"
                        params_res = [site_id, date_from_dt, date_to_dt]
                        if wid != 0:
                            params_res.insert(1, wid)
                        env.cr.execute("""
                            SELECT COUNT(*)
                            FROM property_reservation pr
                            JOIN property_property p ON p.id = pr.property_id
                            WHERE p.""" + site_col + """ = %s AND """ + wing_cond_r + """
                            AND pr.status IN ('reserved', 'requested', 'pending_sales')
                            AND pr.create_date >= %s AND pr.create_date <= %s
                        """, tuple(params_res))
                        row = env.cr.fetchone()
                        res_c = (row[0] or 0) if row else 0
                        per_wing[wid] = {'sold': int(sold_c), 'reserved': int(res_c)}
                        total_sold_site += int(sold_c)
                        total_reserved_site += int(res_c)
                        summary_by_wing[wid]['sold'] += int(sold_c)
                        summary_by_wing[wid]['total'] += sold_v
                        summary_by_wing[wid]['reserved'] += int(res_c)

                    paid_site = 0.0
                    if 'property.reservation.payment' in env:
                        env.cr.execute("""
                            SELECT COALESCE(pr.wing_id, 0), COALESCE(SUM(prp.amount), 0)
                            FROM property_reservation_payment prp
                            JOIN property_reservation pr ON pr.id = prp.reservation_id
                            JOIN property_property p ON p.id = pr.property_id
                            WHERE p.""" + site_col + """ = %s AND prp.payment_status = 'approved'
                            AND pr.status NOT IN ('canceled', 'expired')
                            AND prp.transaction_date >= %s AND prp.transaction_date <= %s
                            GROUP BY pr.wing_id
                        """, (site_id, date_from_str, date_to_str))
                        for row in env.cr.fetchall():
                            wid = row[0] or 0
                            if wid in summary_by_wing:
                                summary_by_wing[wid]['paid'] += float(row[1] or 0)
                            paid_site += float(row[1] or 0)

                    sites_rows.append({
                        'site_id': site_id,
                        'site_name': site_name or f'Site {site_id}',
                        'opening_stock': opening,
                        'available_stock': available,
                        'total_reservation': total_reserved_site,
                        'total_deals_closed': total_sold_site,
                        'wings': per_wing,
                    })

            summary_list = [{'wing_name': wing_names.get(w['id'], w['name']), 'sold': summary_by_wing[w['id']]['sold'], 'total': summary_by_wing[w['id']]['total'], 'paid': summary_by_wing[w['id']]['paid'], 'reserved': summary_by_wing[w['id']]['reserved']} for w in wings]

            if 'property.property' in env:
                try:
                    q = """
                        SELECT COALESCE(p.property_type, '') as pt, COUNT(*), COALESCE(SUM(p.unit_price), 0)
                        FROM property_property p
                        WHERE p.sale_rent = 'for_sale' AND p.create_date::date <= %s
                        AND NOT EXISTS (SELECT 1 FROM property_sale ps WHERE ps.property_id = p.id AND ps.state = 'confirm' AND ps.create_date::date <= %s)
                        GROUP BY COALESCE(p.property_type, '')
                    """
                    env.cr.execute(q, [date_to_str, date_to_str])
                    for pt, qty, val in env.cr.fetchall():
                        pt = (pt or '').lower()
                        qty = int(qty or 0)
                        val = float(val or 0)
                        if pt in ('residential', 'residence'):
                            opening_stock_by_type['residence']['qty'] += qty
                            opening_stock_by_type['residence']['value'] += val
                        elif pt in ('commercial', 'shop', 'shops'):
                            opening_stock_by_type['shops']['qty'] += qty
                            opening_stock_by_type['shops']['value'] += val
                    opening_stock_by_type['total']['qty'] = opening_stock_by_type['residence']['qty'] + opening_stock_by_type['shops']['qty']
                    opening_stock_by_type['total']['value'] = opening_stock_by_type['residence']['value'] + opening_stock_by_type['shops']['value']
                except Exception as e:
                    _logger.warning("Opening stock by type: %s", e)

            return {
                'success': True,
                'date_from': date_from_str,
                'date_to': date_to_str,
                'wings': wings,
                'sites': sites_rows,
                'summary_by_wing': summary_list,
                'opening_stock': opening_stock_by_type,
            }
        except Exception as e:
            _logger.error("api_weekly_sales_by_wing_data: %s", e, exc_info=True)
            return {'success': False, 'error': str(e), 'wings': [], 'sites': [], 'summary_by_wing': [], 'opening_stock': {'residence': {'qty': 0, 'value': 0}, 'shops': {'qty': 0, 'value': 0}, 'total': {'qty': 0, 'value': 0}}}

    # ============================================
    # Weekly Report (transaction list + summary by team/wing)
    # ============================================

    def _get_weekly_report_wings(self, env):
        """Return list of wings for Weekly Report team dropdown (all teams)."""
        wings = []
        if 'property.sales.wing' in env:
            for w in env['property.sales.wing'].sudo().search([], order='name'):
                wings.append({'id': w.id, 'name': w.name or 'Wing %s' % w.id})
        else:
            try:
                env.cr.execute("SELECT id, name FROM property_sales_wing ORDER BY name")
                for r in env.cr.fetchall():
                    wings.append({'id': r[0], 'name': r[1] or 'Wing %s' % r[0]})
            except Exception:
                pass
        return wings

    @http.route('/manager_reports/api/weekly_report_data', type='json', auth='user', methods=['POST'])
    def api_weekly_report_data(self, **kwargs):
        """WEEKLY REPORT: transaction list (NAME, SITE, AGGREMENT NO., TYPE, TEAM, DATE, TOTAL PRICE, PAID IN AMAUNT, PAID IN %), TOTAL SOLD UNIT by team, IN BIRR (TOTAL & PAID) by team. Optional wing_id filter."""
        self._check_weekly_reports_access()
        try:
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            wing_id = kwargs.get('wing_id')
            date_from_obj, date_to_obj = self._get_date_range(date_from, date_to)
            date_from_str = date_from_obj.strftime('%Y-%m-%d')
            date_to_str = date_to_obj.strftime('%Y-%m-%d')
            env = request.env

            transactions = []
            team_units = {}   # team_name -> count
            team_birr = {}    # team_name -> {total_price, paid_amount}

            if 'property.sale' not in env:
                wings = self._get_weekly_report_wings(env)
                return {'success': True, 'date_from': date_from_str, 'date_to': date_to_str, 'wings': wings, 'transactions': [], 'total_sold_unit': [], 'birr_by_team': [], 'grand_total_price': 0, 'grand_total_paid': 0}

            domain = [
                ('state', '=', 'confirm'),
                ('create_date', '>=', date_from_str),
                ('create_date', '<=', date_to_str),
            ]
            wing_id_int = None
            if wing_id and str(wing_id) != 'all':
                try:
                    wing_id_int = int(wing_id)
                except (TypeError, ValueError):
                    pass

            sales = env['property.sale'].sudo().search(domain, order='order_date, create_date, id')
            for idx, sale in enumerate(sales, 1):
                if wing_id_int is not None:
                    res_wing_id = None
                    if getattr(sale, 'reservation_id', None) and sale.reservation_id and sale.reservation_id.wing_id:
                        res_wing_id = sale.reservation_id.wing_id.id
                    if res_wing_id != wing_id_int:
                        continue
                order_date = sale.order_date or sale.create_date
                if order_date:
                    order_date = order_date if hasattr(order_date, 'strftime') else fields.Date.from_string(str(order_date)[:10])
                else:
                    order_date = sale.create_date.date() if sale.create_date else date_from_obj
                if not (date_from_obj <= order_date <= date_to_obj):
                    continue
                total_price = float(sale.sale_price or 0)
                total_paid = float(getattr(sale, 'total_paid', 0) or 0)
                paid_pct = round(100.0 * total_paid / total_price, 2) if total_price else 0
                site_name = ''
                if sale.property_id and sale.property_id.site:
                    site_name = sale.property_id.site.name or ''
                elif getattr(sale, 'site_id', None) and sale.site_id:
                    site_name = sale.site_id.name or ''
                team_name = ''
                if getattr(sale, 'reservation_id', None) and sale.reservation_id and sale.reservation_id.wing_id:
                    team_name = sale.reservation_id.wing_id.name or ''
                agreement_no = sale.name or ''
                prop_name = (sale.property_id and sale.property_id.name) or ''
                customer_name = (sale.partner_id and sale.partner_id.name) or ''
                date_display = order_date.strftime('%d/%m/%y') if hasattr(order_date, 'strftime') else str(order_date)[:10]

                transactions.append({
                    'no': idx,
                    'name': customer_name,
                    'site': site_name,
                    'agreement_no': agreement_no,
                    'type': prop_name,
                    'team': team_name,
                    'date': date_display,
                    'total_price': total_price,
                    'paid_amount': total_paid,
                    'paid_pct': paid_pct,
                })
                if team_name:
                    team_units[team_name] = team_units.get(team_name, 0) + 1
                    if team_name not in team_birr:
                        team_birr[team_name] = {'total_price': 0.0, 'paid_amount': 0.0}
                    team_birr[team_name]['total_price'] += total_price
                    team_birr[team_name]['paid_amount'] += total_paid

            total_sold_unit = [{'team_name': k, 'units': v} for k, v in sorted(team_units.items())]
            total_units = sum(team_units.values())
            birr_by_team = [{'team_name': k, 'total_price': v['total_price'], 'paid_amount': v['paid_amount']} for k, v in sorted(team_birr.items())]
            grand_total_price = sum(t['total_price'] for t in transactions)
            grand_total_paid = sum(t['paid_amount'] for t in transactions)
            wings = self._get_weekly_report_wings(env)

            return {
                'success': True,
                'date_from': date_from_str,
                'date_to': date_to_str,
                'wings': wings,
                'transactions': transactions,
                'total_sold_unit': total_sold_unit,
                'total_units': total_units,
                'birr_by_team': birr_by_team,
                'grand_total_price': grand_total_price,
                'grand_total_paid': grand_total_paid,
            }
        except Exception as e:
            _logger.error("api_weekly_report_data: %s", e, exc_info=True)
            return {'success': False, 'error': str(e), 'wings': [], 'transactions': [], 'total_sold_unit': [], 'birr_by_team': [], 'grand_total_price': 0, 'grand_total_paid': 0}

    @http.route('/manager_reports/api/weekly_report_timeseries', type='json', auth='user', methods=['POST'])
    def api_weekly_report_timeseries(self, **kwargs):
        """Timeline data for Weekly Report: per-day (or per-period) sales count, total price, paid amount. Optional wing_id."""
        self._check_weekly_reports_access()
        try:
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            wing_id = kwargs.get('wing_id')
            date_from_obj, date_to_obj = self._get_date_range(date_from, date_to)
            date_from_str = date_from_obj.strftime('%Y-%m-%d')
            date_to_str = date_to_obj.strftime('%Y-%m-%d')
            env = request.env

            labels = []
            sales_count = []
            total_price_series = []
            paid_amount_series = []

            if 'property.sale' not in env:
                return {'success': True, 'labels': [], 'sales_count': [], 'total_price': [], 'paid_amount': []}

            domain = [
                ('state', '=', 'confirm'),
                ('create_date', '>=', date_from_str),
                ('create_date', '<=', date_to_str),
            ]
            wing_id_int = None
            if wing_id and str(wing_id) != 'all':
                try:
                    wing_id_int = int(wing_id)
                except (TypeError, ValueError):
                    pass

            sales = env['property.sale'].sudo().search(domain, order='create_date')
            by_date = {}  # date_str -> {count, total_price, paid_amount}
            current = date_from_obj
            while current <= date_to_obj:
                by_date[current.strftime('%Y-%m-%d')] = {'count': 0, 'total_price': 0.0, 'paid_amount': 0.0}
                current = current + timedelta(days=1)
            for sale in sales:
                if wing_id_int is not None:
                    res_wing_id = None
                    if getattr(sale, 'reservation_id', None) and sale.reservation_id and sale.reservation_id.wing_id:
                        res_wing_id = sale.reservation_id.wing_id.id
                    if res_wing_id != wing_id_int:
                        continue
                order_date = sale.order_date or sale.create_date
                if order_date:
                    dt = order_date if hasattr(order_date, 'strftime') else fields.Date.from_string(str(order_date)[:10])
                else:
                    dt = sale.create_date.date() if sale.create_date else date_from_obj
                if not (date_from_obj <= dt <= date_to_obj):
                    continue
                key = dt.strftime('%Y-%m-%d') if hasattr(dt, 'strftime') else str(dt)[:10]
                if key not in by_date:
                    by_date[key] = {'count': 0, 'total_price': 0.0, 'paid_amount': 0.0}
                by_date[key]['count'] += 1
                by_date[key]['total_price'] += float(sale.sale_price or 0)
                by_date[key]['paid_amount'] += float(getattr(sale, 'total_paid', 0) or 0)
            for d in sorted(by_date.keys()):
                labels.append(d)
                sales_count.append(by_date[d]['count'])
                total_price_series.append(by_date[d]['total_price'])
                paid_amount_series.append(by_date[d]['paid_amount'])

            return {
                'success': True,
                'labels': labels,
                'sales_count': sales_count,
                'total_price': total_price_series,
                'paid_amount': paid_amount_series,
            }
        except Exception as e:
            _logger.error("api_weekly_report_timeseries: %s", e, exc_info=True)
            return {'success': False, 'labels': [], 'sales_count': [], 'total_price': [], 'paid_amount': []}

    def _get_weekly_sales_by_wing_export_data(self, date_from, date_to):
        """Get Weekly Sales By Wing data for export (reuses API)."""
        result = self.api_weekly_sales_by_wing_data(date_from=date_from, date_to=date_to)
        if not result.get('success'):
            return None
        return result

    @http.route('/manager_reports/api/export_weekly_sales_by_wing_excel', type='http', auth='user', methods=['POST'], csrf=False)
    def api_export_weekly_sales_by_wing_excel(self, date_from=None, date_to=None, **kwargs):
        self._check_weekly_reports_access()
        """Export Weekly Sales By Wing to Excel (multi-sheet: By Site, Summary, Opening Stock)."""
        try:
            import xlsxwriter
            date_from_obj, date_to_obj = self._get_date_range(date_from, date_to)
            date_from_str = date_from_obj.strftime('%Y-%m-%d')
            date_to_str = date_to_obj.strftime('%Y-%m-%d')
            data = self._get_weekly_sales_by_wing_export_data(date_from_str, date_to_str)
            if not data:
                return request.make_response("No data for selected period", status=400)
            wings = data.get('wings', [])
            sites = data.get('sites', [])
            summary_list = data.get('summary_by_wing', [])
            opening_stock = data.get('opening_stock', {})

            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#E5E7EB', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
            cell_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})
            num_fmt = workbook.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter'})
            money_fmt = workbook.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter', 'num_format': '#,##0.00'})

            # Sheet 1: By Site (main table)
            ws1 = workbook.add_worksheet('By Site')
            row = 0
            ws1.merge_range(row, 0, row, 4 + len(wings) * 2, f'Weekly Sales Report By Wing as of {date_to_str}', title_fmt)
            row += 2
            col = 0
            ws1.write(row, col, 'SITE', header_fmt)
            col += 1
            ws1.write(row, col, f'OPENING STOCK ON {date_from_str}', header_fmt)
            col += 1
            for w in wings:
                ws1.merge_range(row, col, row, col + 1, w.get('name', ''), header_fmt)
                col += 2
            ws1.write(row, col, f'TOTAL RESERVATION {date_to_str}', header_fmt)
            col += 1
            ws1.write(row, col, 'Total Deals Closed', header_fmt)
            col += 1
            ws1.write(row, col, f'AVAILABLE STOCK ON {date_to_str}', header_fmt)
            row += 1
            col = 0
            ws1.write(row, col, '', header_fmt)
            col += 1
            ws1.write(row, col, '', header_fmt)
            col += 1
            for w in wings:
                ws1.write(row, col, 'SOLD', header_fmt)
                ws1.write(row, col + 1, 'RESERVED', header_fmt)
                col += 2
            ws1.write(row, col, '', header_fmt)
            col += 1
            ws1.write(row, col, '', header_fmt)
            col += 1
            ws1.write(row, col, '', header_fmt)
            row += 1
            for site in sites:
                col = 0
                ws1.write(row, col, site.get('site_name', ''), cell_fmt)
                col += 1
                ws1.write(row, col, site.get('opening_stock', 0), num_fmt)
                col += 1
                wings_data = site.get('wings', {})
                for w in wings:
                    wid = w['id']
                    d = wings_data.get(wid, {})
                    ws1.write(row, col, d.get('sold', 0), num_fmt)
                    ws1.write(row, col + 1, d.get('reserved', 0), num_fmt)
                    col += 2
                ws1.write(row, col, site.get('total_reservation', 0), num_fmt)
                col += 1
                ws1.write(row, col, site.get('total_deals_closed', 0), num_fmt)
                col += 1
                ws1.write(row, col, site.get('available_stock', 0), num_fmt)
                row += 1
            if sites:
                col = 0
                t_open = sum(s.get('opening_stock', 0) for s in sites)
                t_avail = sum(s.get('available_stock', 0) for s in sites)
                t_res = sum(s.get('total_reservation', 0) for s in sites)
                t_deals = sum(s.get('total_deals_closed', 0) for s in sites)
                ws1.write(row, col, 'TOTAL', header_fmt)
                col += 1
                ws1.write(row, col, t_open, num_fmt)
                col += 1
                for w in wings:
                    wid = w['id']
                    sold_t = sum((s.get('wings') or {}).get(wid, {}).get('sold', 0) for s in sites)
                    res_t = sum((s.get('wings') or {}).get(wid, {}).get('reserved', 0) for s in sites)
                    ws1.write(row, col, sold_t, num_fmt)
                    ws1.write(row, col + 1, res_t, num_fmt)
                    col += 2
                ws1.write(row, col, t_res, num_fmt)
                col += 1
                ws1.write(row, col, t_deals, num_fmt)
                col += 1
                ws1.write(row, col, t_avail, num_fmt)
            ws1.set_column(0, 0, 22)
            ws1.set_column(1, 1, 14)

            # Sheet 2: Summary
            ws2 = workbook.add_worksheet('Summary')
            row = 0
            ws2.merge_range(row, 0, row, 4, 'SUMMERY', title_fmt)
            row += 1
            ws2.write_row(row, 0, ['WING', 'SOLD', 'TOTAL', 'PAID', 'RESERVED'], header_fmt)
            row += 1
            for r in summary_list:
                ws2.write(row, 0, r.get('wing_name', ''), cell_fmt)
                ws2.write(row, 1, r.get('sold', 0), num_fmt)
                ws2.write(row, 2, r.get('total', 0), money_fmt)
                ws2.write(row, 3, r.get('paid', 0), money_fmt)
                ws2.write(row, 4, r.get('reserved', 0), num_fmt)
                row += 1
            if summary_list:
                ws2.write(row, 0, 'Total', header_fmt)
                ws2.write(row, 1, sum(r.get('sold', 0) for r in summary_list), num_fmt)
                ws2.write(row, 2, sum(r.get('total', 0) for r in summary_list), money_fmt)
                ws2.write(row, 3, sum(r.get('paid', 0) for r in summary_list), money_fmt)
                ws2.write(row, 4, sum(r.get('reserved', 0) for r in summary_list), num_fmt)
            ws2.set_column(0, 0, 18)
            ws2.set_column(1, 4, 14)

            # Sheet 3: Opening Stock
            ws3 = workbook.add_worksheet('Opening Stock')
            row = 0
            ws3.merge_range(row, 0, row, 2, 'Opening Stock', title_fmt)
            row += 1
            ws3.write_row(row, 0, ['Type', 'QTY', 'Estimated Value(Birr)'], header_fmt)
            row += 1
            for label, key in [('Residence', 'residence'), ('Shops', 'shops'), ('Total', 'total')]:
                rec = (opening_stock or {}).get(key, {}) or {}
                ws3.write(row, 0, label, cell_fmt)
                ws3.write(row, 1, rec.get('qty', 0), num_fmt)
                ws3.write(row, 2, rec.get('value', 0), money_fmt)
                row += 1
            ws3.set_column(0, 0, 16)
            ws3.set_column(1, 2, 18)

            workbook.close()
            output.seek(0)
            filename = f'Weekly_Sales_Report_By_Wing_{date_from_str}_{date_to_str}.xlsx'
            return request.make_response(
                output.read(),
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                ],
            )
        except Exception as e:
            _logger.error("Export weekly sales by wing Excel: %s", e, exc_info=True)
            return request.make_response("Error: " + str(e), status=500)

    @http.route('/manager_reports/api/export_weekly_sales_by_wing_pdf', type='http', auth='user', methods=['POST'], csrf=False)
    def api_export_weekly_sales_by_wing_pdf(self, date_from=None, date_to=None, **kwargs):
        self._check_weekly_reports_access()
        """Export Weekly Sales By Wing to PDF (HTML for print)."""
        try:
            date_from_obj, date_to_obj = self._get_date_range(date_from, date_to)
            date_from_str = date_from_obj.strftime('%Y-%m-%d')
            date_to_str = date_to_obj.strftime('%Y-%m-%d')
            data = self._get_weekly_sales_by_wing_export_data(date_from_str, date_to_str)
            if not data:
                return request.make_response("No data for selected period", status=400)
            wings = data.get('wings', [])
            sites = data.get('sites', [])
            summary_list = data.get('summary_by_wing', [])
            opening_stock = data.get('opening_stock', {})

            def fmt_num(n):
                return '{:,.0f}'.format(n) if n is not None else '0'
            def fmt_money(n):
                return '{:,.2f}'.format(float(n)) if n is not None else '0.00'

            html_parts = []
            html_parts.append(f'<h2 style="text-align:center">Weekly Sales Report By Wing as of {date_to_str}</h2>')
            html_parts.append('<p style="text-align:center">Period: {} to {}</p>'.format(date_from_str, date_to_str))
            html_parts.append('<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse; width:100%; margin-bottom:20px">')
            html_parts.append('<thead><tr><th>SITE</th><th>OPENING STOCK<br/>' + date_from_str + '</th>')
            for w in wings:
                html_parts.append('<th colspan="2">{}</th>'.format(w.get('name', '')))
            html_parts.append('<th>TOTAL RESERVATION</th><th>Total Deals Closed</th><th>AVAILABLE STOCK<br/>' + date_to_str + '</th></tr><tr><th></th><th></th>')
            for w in wings:
                html_parts.append('<th>SOLD</th><th>RESERVED</th>')
            html_parts.append('<th></th><th></th><th></th></tr></thead><tbody>')
            for site in sites:
                html_parts.append('<tr><td>{}</td><td>{}</td>'.format(site.get('site_name', ''), fmt_num(site.get('opening_stock', 0))))
                wings_data = site.get('wings', {})
                for w in wings:
                    d = wings_data.get(w['id'], {})
                    html_parts.append('<td>{}</td><td>{}</td>'.format(fmt_num(d.get('sold')), fmt_num(d.get('reserved'))))
                html_parts.append('<td>{}</td><td>{}</td><td>{}</td></tr>'.format(fmt_num(site.get('total_reservation')), fmt_num(site.get('total_deals_closed')), fmt_num(site.get('available_stock'))))
            if sites:
                t_open = sum(s.get('opening_stock', 0) for s in sites)
                t_avail = sum(s.get('available_stock', 0) for s in sites)
                t_res = sum(s.get('total_reservation', 0) for s in sites)
                t_deals = sum(s.get('total_deals_closed', 0) for s in sites)
                html_parts.append('<tr style="font-weight:bold"><td>TOTAL</td><td>{}</td>'.format(fmt_num(t_open)))
                for w in wings:
                    sold_t = sum((s.get('wings') or {}).get(w['id'], {}).get('sold', 0) for s in sites)
                    res_t = sum((s.get('wings') or {}).get(w['id'], {}).get('reserved', 0) for s in sites)
                    html_parts.append('<td>{}</td><td>{}</td>'.format(fmt_num(sold_t), fmt_num(res_t)))
                html_parts.append('<td>{}</td><td>{}</td><td>{}</td></tr>'.format(fmt_num(t_res), fmt_num(t_deals), fmt_num(t_avail)))
            html_parts.append('</tbody></table>')
            html_parts.append('<h3>SUMMERY</h3><table border="1" cellpadding="4" style="border-collapse:collapse; width:100%; margin-bottom:20px">')
            html_parts.append('<tr><th>WING</th><th>SOLD</th><th>TOTAL</th><th>PAID</th><th>RESERVED</th></tr>')
            for r in summary_list:
                html_parts.append('<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(r.get('wing_name', ''), fmt_num(r.get('sold')), fmt_money(r.get('total')), fmt_money(r.get('paid')), fmt_num(r.get('reserved'))))
            if summary_list:
                html_parts.append('<tr style="font-weight:bold"><td>Total</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(
                    fmt_num(sum(r.get('sold', 0) for r in summary_list)), fmt_money(sum(r.get('total', 0) for r in summary_list)),
                    fmt_money(sum(r.get('paid', 0) for r in summary_list)), fmt_num(sum(r.get('reserved', 0) for r in summary_list))))
            html_parts.append('</table>')
            html_parts.append('<h3>Opening Stock</h3><table border="1" cellpadding="4" style="border-collapse:collapse; width:400px">')
            html_parts.append('<tr><th>Type</th><th>QTY</th><th>Estimated Value(Birr)</th></tr>')
            for label, key in [('Residence', 'residence'), ('Shops', 'shops'), ('Total', 'total')]:
                rec = (opening_stock or {}).get(key, {}) or {}
                html_parts.append('<tr><td>{}</td><td>{}</td><td>{}</td></tr>'.format(label, fmt_num(rec.get('qty')), fmt_money(rec.get('value'))))
            html_parts.append('</table>')
            html_parts.append('<script>window.onload=function(){ window.print(); }</script>')
            full_html = '<!DOCTYPE html><html><head><meta charset="UTF-8"/><title>Weekly Sales Report By Wing</title></head><body style="font-family:Segoe UI,Arial; padding:16px">' + ''.join(html_parts) + '</body></html>'
            return request.make_response(
                full_html,
                headers=[('Content-Type', 'text/html; charset=utf-8')],
            )
        except Exception as e:
            _logger.error("Export weekly sales by wing PDF: %s", e, exc_info=True)
            return request.make_response("Error: " + str(e), status=500)

    # ============================================
    # REPORT 1: Stock/Inventory Report
    # ============================================
    
    @http.route('/manager_reports/api/stock_inventory_data', type='json', auth='user', methods=['POST'])
    def api_stock_inventory_data(self, **kwargs):
        """Get Stock/Inventory Report data"""
        try:
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            wing_id = kwargs.get('wing_id', None)
            
            date_from_obj, date_to_obj = self._get_date_range(date_from, date_to)
            date_from_datetime = datetime.combine(date_from_obj, datetime.min.time())
            date_to_datetime = datetime.combine(date_to_obj, datetime.max.time())
            
            env = request.env
            result = {}
            
            wing_id_int = None
            if wing_id and wing_id != 'all':
                try:
                    wing_id_int = int(wing_id)
                except Exception:
                    wing_id_int = None

            # Check legacy column (exclude legacy=true from all property-related metrics)
            has_legacy_col = False
            try:
                env.cr.execute("""
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'property_property' AND column_name = 'legacy'
                """)
                has_legacy_col = env.cr.fetchone() is not None
            except Exception:
                pass

            # Helper: property_type bucket (residence, shops, mixed - no office)
            def _bucket_from_property_type(pt):
                pt = (pt or '').lower()
                if pt in ('residential', 'residence'):
                    return 'residence'
                if pt in ('commercial', 'shop', 'shops'):
                    return 'shops'
                if pt in ('mixed_use', 'mixed'):
                    return 'mixed'
                # fallback keyword match
                if 'resid' in pt:
                    return 'residence'
                if 'shop' in pt or 'comm' in pt:
                    return 'shops'
                if 'mix' in pt or 'off' in pt:
                    return 'mixed'
                return None

            # ------------------------------------------------------------
            # 1) No. of sites handed over = sold & delivered to customer
            # Exclude legacy properties.
            # ------------------------------------------------------------
            sites_handed_over = 0
            if 'property.sale' in env:
                legacy_join = " JOIN property_property pp ON pp.id = ps.property_id AND (pp.legacy IS NULL OR pp.legacy = false)" if has_legacy_col else ""
                query = f"""
                    SELECT COUNT(*)
                    FROM property_sale ps
                    {legacy_join}
                    LEFT JOIN property_reservation pr ON pr.id = ps.reservation_id
                    WHERE ps.state = 'confirm'
                      AND ps.create_date >= %s
                      AND ps.create_date <= %s
                """
                params = [date_from_datetime, date_to_datetime]
                if wing_id_int:
                    query += " AND pr.wing_id = %s"
                    params.append(wing_id_int)
                env.cr.execute(query.strip(), tuple(params))
                sites_handed_over = env.cr.fetchone()[0] or 0
            result['sites_handed_over'] = sites_handed_over
            
            # ------------------------------------------------------------
            # 2a) No. of available properties = only state='available' (matches Property list Available filter)
            # 2b) No. of available sites = DISTINCT sites with available properties (active sites only)
            # ------------------------------------------------------------
            site_col = 'site_id'
            try:
                env.cr.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'property_property'
                    AND column_name = 'site'
                """)
                if env.cr.fetchone():
                    site_col = 'site'
            except Exception:
                pass

            available_properties = 0
            available_sites = 0
            if 'property.property' in env:
                legacy_cond = " AND (p.legacy IS NULL OR p.legacy = false)" if has_legacy_col else ""
                base_where = """
                    COALESCE(p.state, '') = 'available'
                    AND p.sale_rent = 'for_sale'
                    AND p.create_date <= %s
                    AND NOT EXISTS (
                        SELECT 1 FROM property_sale ps
                        WHERE ps.property_id = p.id AND ps.state = 'confirm'
                    )
                    AND p.{site_col} IS NOT NULL
                """.format(site_col=site_col) + legacy_cond
                wing_cond = ""
                params = [date_to_datetime]
                if wing_id_int:
                    wing_cond = """
                      AND EXISTS (
                        SELECT 1 FROM property_reservation pr
                        WHERE pr.property_id = p.id AND pr.wing_id = %s
                      )
                    """
                    params.append(wing_id_int)

                # 2a) Available properties - same logic as Stock Available total
                query_props = f"""
                    SELECT COUNT(*) FROM property_property p
                    WHERE {base_where} {wing_cond}
                """
                env.cr.execute(query_props.strip(), tuple(params))
                available_properties = env.cr.fetchone()[0] or 0

                # 2b) Available sites - distinct sites, active only
                join_site = " JOIN property_site ps ON ps.id = p.{0} ".format(site_col)
                base_where_sites = """
                    COALESCE(p.state, '') = 'available'
                    AND p.sale_rent = 'for_sale'
                    AND p.create_date <= %s
                    AND NOT EXISTS (
                        SELECT 1 FROM property_sale psale
                        WHERE psale.property_id = p.id AND psale.state = 'confirm'
                    )
                    AND COALESCE(ps.state, '') = 'active'
                """ + legacy_cond
                query_sites = f"""
                    SELECT COUNT(DISTINCT p.{site_col})
                    FROM property_property p
                    {join_site}
                    WHERE {base_where_sites} {wing_cond}
                """
                env.cr.execute(query_sites.strip(), tuple(params))
                available_sites = env.cr.fetchone()[0] or 0

            result['available_properties'] = available_properties
            result['available_sites'] = available_sites
            
            # ------------------------------------------------------------
            # 3) Stock Available by Type (TOP table) = stock CREATED in date range and not sold (no confirmed sale)
            # This matches the proven SQL in sales_performance.
            # ------------------------------------------------------------
            stock_available = {
                'residence': {'qty': 0, 'estimated_value': 0.0},
                'shops': {'qty': 0, 'estimated_value': 0.0},
                'mixed': {'qty': 0, 'estimated_value': 0.0},
                'total': {'qty': 0, 'estimated_value': 0.0}
            }

            if 'property.property' in env:
                # Stock Available: use end date (date_to) - count properties created on or before end date; exclude legacy=true
                legacy_cond = " AND (p.legacy IS NULL OR p.legacy = false)" if has_legacy_col else ""
                query = f"""
                    SELECT 
                        COALESCE(p.property_type, '') as property_type,
                        COUNT(*) as qty,
                        COALESCE(SUM(p.unit_price), 0) as total_value
                    FROM property_property p
                    WHERE COALESCE(p.state, '') = 'available'
                      AND p.sale_rent = 'for_sale'
                      AND p.create_date <= %s
                      AND NOT EXISTS (
                          SELECT 1
                          FROM property_sale ps
                          WHERE ps.property_id = p.id
                            AND ps.state = 'confirm'
                      ){legacy_cond}
                """
                params = [date_to_datetime]
                if wing_id_int:
                    # property_property has no wing_id; approximate by reservation activity in this wing
                    query += """
                      AND EXISTS (
                        SELECT 1
                        FROM property_reservation pr
                        WHERE pr.property_id = p.id
                          AND pr.wing_id = %s
                      )
                    """
                    params.append(wing_id_int)
                query += " GROUP BY COALESCE(p.property_type, '')"
                env.cr.execute(query, tuple(params))
                for property_type, qty, total_value in env.cr.fetchall():
                    bucket = _bucket_from_property_type(property_type)
                    if not bucket:
                        continue
                    stock_available[bucket]['qty'] += int(qty or 0)
                    stock_available[bucket]['estimated_value'] += float(total_value or 0.0)
                    stock_available['total']['qty'] += int(qty or 0)
                    stock_available['total']['estimated_value'] += float(total_value or 0.0)
            
            result['stock_available'] = stock_available
            
            # 4) No. of signed contract = confirmed property sales in date range (exclude legacy)
            signed_contracts = 0
            if 'property.sale' in env:
                legacy_join_s = " JOIN property_property pp2 ON pp2.id = ps.property_id AND (pp2.legacy IS NULL OR pp2.legacy = false)" if has_legacy_col else ""
                query = f"""
                    SELECT COUNT(*)
                    FROM property_sale ps
                    {legacy_join_s}
                    LEFT JOIN property_reservation pr ON pr.id = ps.reservation_id
                    WHERE ps.state = 'confirm'
                      AND ps.create_date >= %s
                      AND ps.create_date <= %s
                """
                params = [date_from_datetime, date_to_datetime]
                if wing_id_int:
                    query += " AND pr.wing_id = %s"
                    params.append(wing_id_int)
                env.cr.execute(query, tuple(params))
                signed_contracts = env.cr.fetchone()[0] or 0
            result['signed_contracts'] = signed_contracts
            
            # 5) No. of reservations = properties with state='reserved' (matches Property list Reserved filter)
            reservations = 0
            if 'property.property' in env:
                legacy_cond = " AND (p.legacy IS NULL OR p.legacy = false)" if has_legacy_col else ""
                query = f"""
                    SELECT COUNT(*)
                    FROM property_property p
                    WHERE COALESCE(p.state, '') = 'reserved'{legacy_cond}
                """
                params = []
                if wing_id_int:
                    query += """
                      AND EXISTS (
                        SELECT 1 FROM property_reservation pr
                        WHERE pr.property_id = p.id AND pr.wing_id = %s
                      )
                    """
                    params.append(wing_id_int)
                env.cr.execute(query.strip(), tuple(params) if params else ())
                reservations = env.cr.fetchone()[0] or 0
            result['reservations'] = reservations
            
            # 6) No. of cancelled reservations - all reservation types (match Reservation History Canceled filter)
            cancelled_reservations = 0
            if 'property.reservation' in env:
                legacy_can = " AND (p.legacy IS NULL OR p.legacy = false)" if has_legacy_col else ""
                query = f"""
                    SELECT COUNT(DISTINCT pr.id)
                    FROM property_reservation pr
                    JOIN property_property p ON p.id = pr.property_id
                    WHERE pr.status = 'canceled'
                      AND pr.write_date >= %s
                      AND pr.write_date <= %s{legacy_can}
                """
                params = [date_from_datetime, date_to_datetime]
                if wing_id_int:
                    query += " AND pr.wing_id = %s"
                    params.append(wing_id_int)
                env.cr.execute(query, tuple(params))
                cancelled_reservations = env.cr.fetchone()[0] or 0
            result['cancelled_reservations'] = cancelled_reservations

            # 6b) No. of expired reservations - all reservation types (match Reservation History Expired filter)
            expired_reservations = 0
            if 'property.reservation' in env:
                legacy_exp = " AND (p.legacy IS NULL OR p.legacy = false)" if has_legacy_col else ""
                query = f"""
                    SELECT COUNT(DISTINCT pr.id)
                    FROM property_reservation pr
                    JOIN property_property p ON p.id = pr.property_id
                    WHERE pr.status = 'expired'
                      AND pr.write_date >= %s
                      AND pr.write_date <= %s{legacy_exp}
                """
                params = [date_from_datetime, date_to_datetime]
                if wing_id_int:
                    query += " AND pr.wing_id = %s"
                    params.append(wing_id_int)
                env.cr.execute(query, tuple(params))
                expired_reservations = env.cr.fetchone()[0] or 0
            result['expired_reservations'] = expired_reservations
            
            # 7. Refunds
            # (Not fully defined in this DB schema; keep 0.0 unless your refunds model is provided later)
            refunds_count = 0
            refunds_value = 0.0
            
            result['refunds'] = {
                'count': refunds_count,
                'value': refunds_value
            }
            
            # 8. Sales Table by Type and Team
            # Rows:
            # - Residence, Shops: sold units (quick+regular sold), total price, advanced paid, discount given
            # - Wings: same metrics grouped by wing
            sales_table = []

            # 8.1) Base sold data (confirmed sales) grouped by property_type and wing
            sold_by_type = {'residence': {'unit': 0, 'value': 0.0}, 'shops': {'unit': 0, 'value': 0.0}, 'mixed': {'unit': 0, 'value': 0.0}}
            sold_by_wing = {}  # wing_id -> {unit, value}
            sale_ids = []
            property_ids_sold = []
            if 'property.sale' in env:
                legacy_sold = " AND (p.legacy IS NULL OR p.legacy = false)" if has_legacy_col else ""
                query = f"""
                    SELECT ps.id,
                           ps.property_id,
                           COALESCE(p.property_type, '') as property_type,
                           COALESCE(ps.sale_price, 0) as sale_price,
                           COALESCE(pr.wing_id, 0) as wing_id
                    FROM property_sale ps
                    JOIN property_property p ON p.id = ps.property_id
                    LEFT JOIN property_reservation pr ON pr.id = ps.reservation_id
                    WHERE ps.state = 'confirm'
                      AND ps.create_date >= %s
                      AND ps.create_date <= %s{legacy_sold}
                """
                params = [date_from_datetime, date_to_datetime]
                if wing_id_int:
                    query += " AND pr.wing_id = %s"
                    params.append(wing_id_int)
                env.cr.execute(query, tuple(params))
                for ps_id, prop_id, prop_type, sale_price, w_id in env.cr.fetchall():
                    sale_ids.append(ps_id)
                    property_ids_sold.append(prop_id)
                    bucket = _bucket_from_property_type(prop_type)
                    if bucket in ('residence', 'shops', 'mixed'):
                        sold_by_type[bucket]['unit'] += 1
                        sold_by_type[bucket]['value'] += float(sale_price or 0.0)
                    # IMPORTANT: always bucket by wing_id (including 0 = No wing),
                    # so wing totals match type totals.
                    w_id_int = int(w_id or 0)
                    sold_by_wing.setdefault(w_id_int, {'unit': 0, 'value': 0.0})
                    sold_by_wing[w_id_int]['unit'] += 1
                    sold_by_wing[w_id_int]['value'] += float(sale_price or 0.0)

            # 8.2) Advanced paid (reservation advance) in date range, grouped by property_type and wing
            adv_by_type = {'residence': 0.0, 'shops': 0.0, 'mixed': 0.0}
            adv_by_wing = {}
            if 'property.reservation' in env and 'property.reservation.payment' in env:
                legacy_adv = " AND (p.legacy IS NULL OR p.legacy = false)" if has_legacy_col else ""
                query = f"""
                    SELECT COALESCE(p.property_type, '') as property_type,
                           COALESCE(pr.wing_id, 0) as wing_id,
                           COALESCE(SUM(COALESCE(prp.amount, 0)), 0) as adv_amount
                    FROM property_reservation_payment prp
                    JOIN property_reservation pr ON pr.id = prp.reservation_id
                    JOIN property_reservation_configuration prc ON prc.id = pr.reservation_type_id
                    JOIN property_property p ON p.id = pr.property_id
                    WHERE prp.payment_status = 'approved'
                      AND pr.status NOT IN ('canceled', 'expired')
                      AND prc.reservation_type IN ('quick', 'regular')
                      AND prp.transaction_date >= %s
                      AND prp.transaction_date <= %s{legacy_adv}
                """
                params = [date_from_datetime, date_to_datetime]
                if wing_id_int:
                    query += " AND pr.wing_id = %s"
                    params.append(wing_id_int)
                query += " GROUP BY COALESCE(p.property_type, ''), COALESCE(pr.wing_id, 0)"
                env.cr.execute(query, tuple(params))
                for prop_type, w_id, adv_amount in env.cr.fetchall():
                    bucket = _bucket_from_property_type(prop_type)
                    if bucket in ('residence', 'shops', 'mixed'):
                        adv_by_type[bucket] += float(adv_amount or 0.0)
                    w_id_int = int(w_id or 0)
                    adv_by_wing[w_id_int] = adv_by_wing.get(w_id_int, 0.0) + float(adv_amount or 0.0)

            # 8.3) Discount given in date range - REMOVED per user request
            disc_by_type = {'residence': 0.0, 'shops': 0.0, 'mixed': 0.0}
            disc_by_wing = {}
            if 'collection.installment' in env and sale_ids:
                placeholders = ','.join(['%s'] * len(sale_ids))
                legacy_disc = " AND (p.legacy IS NULL OR p.legacy = false)" if has_legacy_col else ""
                query = f"""
                    SELECT COALESCE(p.property_type, '') as property_type,
                           COALESCE(pr.wing_id, 0) as wing_id,
                           COALESCE(SUM(COALESCE(ci.discount_amount, 0)), 0) as disc_amount
                    FROM collection_installment ci
                    JOIN collection_order co ON co.id = ci.collection_id
                    JOIN property_sale ps ON ps.id = co.sale_id
                    JOIN property_property p ON p.id = ps.property_id
                    LEFT JOIN property_reservation pr ON pr.id = ps.reservation_id
                    WHERE ci.create_date >= %s
                      AND ci.create_date <= %s
                      AND ps.id IN ({placeholders}){legacy_disc}
                    GROUP BY COALESCE(p.property_type, ''), COALESCE(pr.wing_id, 0)
                """
                params = [date_from_datetime, date_to_datetime] + sale_ids
                env.cr.execute(query, tuple(params))
                for prop_type, w_id, disc_amount in env.cr.fetchall():
                    bucket = _bucket_from_property_type(prop_type)
                    if bucket in ('residence', 'shops', 'mixed'):
                        disc_by_type[bucket] += float(disc_amount or 0.0)
                    w_id_int = int(w_id or 0)
                    disc_by_wing[w_id_int] = disc_by_wing.get(w_id_int, 0.0) + float(disc_amount or 0.0)

            # 8.4) Compose rows (discount removed per user request)
            def _row(label, unit, total, adv, disc=0.0):
                adv_pct = (adv / total * 100.0) if total else 0.0
                if adv_pct > 100.0:
                    adv_pct = 100.0
                return {
                    'type': label,
                    'unit_sold': int(unit or 0),
                    'total_price': float(total or 0.0),
                    'advanced_paid': {'value': float(adv or 0.0), 'percentage': float(adv_pct)},
                    'discount_given': {'value': 0.0, 'percentage': 0.0},  # Discount removed
                }

            sales_table.append(_row('Residences', sold_by_type['residence']['unit'], sold_by_type['residence']['value'], adv_by_type['residence']))
            sales_table.append(_row('Shops', sold_by_type['shops']['unit'], sold_by_type['shops']['value'], adv_by_type['shops']))
            sales_table.append(_row('Mixed', sold_by_type['mixed']['unit'], sold_by_type['mixed']['value'], adv_by_type['mixed']))

            # Wing rows (use wing name from property.sales.wing / SQL)
            wing_names = {}
            all_wing_ids = []
            try:
                if 'property.sales.wing' in env:
                    for w in env['property.sales.wing'].sudo().search([]):
                        wing_names[w.id] = w.name or f'Wing {w.id}'
                        all_wing_ids.append(w.id)
                else:
                    env.cr.execute("SELECT id, name FROM property_sales_wing")
                    for w_id, w_name in env.cr.fetchall():
                        wing_names[int(w_id)] = w_name or f'Wing {w_id}'
                        all_wing_ids.append(int(w_id))
            except Exception:
                wing_names = {}
                all_wing_ids = []

            # Ensure we include ALL wings (even if 0), plus handle "No wing"
            if all_wing_ids:
                wing_iter = sorted(all_wing_ids, key=lambda x: wing_names.get(x, f'Wing {x}'))
            else:
                wing_iter = sorted(sold_by_wing.keys(), key=lambda x: wing_names.get(x, f'Wing {x}'))

            for w_id in wing_iter:
                if w_id == 0:
                    continue  # No wing handled separately below
                label = wing_names.get(w_id, f'Wing {w_id}')
                sales_table.append(_row(
                    label,
                    sold_by_wing.get(w_id, {}).get('unit', 0),
                    sold_by_wing.get(w_id, {}).get('value', 0.0),
                    adv_by_wing.get(w_id, 0.0),
                ))

            # "No wing" bucket - show only if it has count (unit > 0)
            no_wing_unit = sold_by_wing.get(0, {}).get('unit', 0)
            no_wing_value = sold_by_wing.get(0, {}).get('value', 0.0)
            no_wing_adv = adv_by_wing.get(0, 0.0)
            if no_wing_unit > 0 or no_wing_value > 0:
                sales_table.append(_row('No wing', no_wing_unit, no_wing_value, no_wing_adv))

            # Total row (residence + shops + mixed)
            total_unit = sold_by_type['residence']['unit'] + sold_by_type['shops']['unit'] + sold_by_type['mixed']['unit']
            total_value = sold_by_type['residence']['value'] + sold_by_type['shops']['value'] + sold_by_type['mixed']['value']
            total_adv = adv_by_type['residence'] + adv_by_type['shops'] + adv_by_type['mixed']
            sales_table.append(_row('TOTAL', total_unit, total_value, total_adv))
            
            result['sales_table'] = sales_table

            # 9) Wing metrics: Reservations, Cancelled, Expired per wing (no Advanced Paid - money vs count not comparable)
            reservations_by_wing = {}
            cancelled_by_wing = {}
            expired_by_wing = {}
            if 'property.reservation' in env:
                legacy_r = " AND (p.legacy IS NULL OR p.legacy = false)" if has_legacy_col else ""
                # Reservations (properties with state=reserved) per wing
                query = f"""
                    SELECT COALESCE(pr.wing_id, 0), COUNT(DISTINCT p.id)
                    FROM property_property p
                    JOIN property_reservation pr ON pr.property_id = p.id AND pr.status IN ('reserved','requested','pending_sales')
                    WHERE COALESCE(p.state, '') = 'reserved'{legacy_r}
                    GROUP BY pr.wing_id
                """
                env.cr.execute(query.strip(), ())
                for w_id, cnt in env.cr.fetchall():
                    reservations_by_wing[int(w_id or 0)] = int(cnt or 0)
                # Cancelled per wing
                legacy_c = " AND (p.legacy IS NULL OR p.legacy = false)" if has_legacy_col else ""
                query = f"""
                    SELECT COALESCE(pr.wing_id, 0), COUNT(DISTINCT pr.id)
                    FROM property_reservation pr
                    JOIN property_property p ON p.id = pr.property_id
                    WHERE pr.status = 'canceled'
                      AND pr.write_date >= %s AND pr.write_date <= %s{legacy_c}
                    GROUP BY pr.wing_id
                """
                env.cr.execute(query.strip(), (date_from_datetime, date_to_datetime))
                for w_id, cnt in env.cr.fetchall():
                    cancelled_by_wing[int(w_id or 0)] = int(cnt or 0)
                # Expired per wing
                query = f"""
                    SELECT COALESCE(pr.wing_id, 0), COUNT(DISTINCT pr.id)
                    FROM property_reservation pr
                    JOIN property_property p ON p.id = pr.property_id
                    WHERE pr.status = 'expired'
                      AND pr.write_date >= %s AND pr.write_date <= %s{legacy_c}
                    GROUP BY pr.wing_id
                """
                env.cr.execute(query.strip(), (date_from_datetime, date_to_datetime))
                for w_id, cnt in env.cr.fetchall():
                    expired_by_wing[int(w_id or 0)] = int(cnt or 0)

            # Collect all wing ids from reservations/cancelled/expired only (no adv - money vs count not comparable)
            all_wing_ids_metrics = set(wing_iter) | set(reservations_by_wing.keys()) | set(cancelled_by_wing.keys()) | set(expired_by_wing.keys())
            wing_metrics_table = []
            for w_id in sorted(all_wing_ids_metrics, key=lambda x: (x == 0, wing_names.get(x, f'Wing {x}'))):
                if w_id == 0:
                    continue
                label = wing_names.get(w_id, f'Wing {w_id}')
                wing_metrics_table.append({
                    'wing_name': label,
                    'wing_id': w_id,
                    'reservations': reservations_by_wing.get(w_id, 0),
                    'cancelled': cancelled_by_wing.get(w_id, 0),
                    'expired': expired_by_wing.get(w_id, 0),
                })
            if (reservations_by_wing.get(0, 0) or cancelled_by_wing.get(0, 0) or expired_by_wing.get(0, 0)):
                wing_metrics_table.append({
                    'wing_name': 'No wing',
                    'wing_id': 0,
                    'reservations': reservations_by_wing.get(0, 0),
                    'cancelled': cancelled_by_wing.get(0, 0),
                    'expired': expired_by_wing.get(0, 0),
                })
            result['wing_metrics_table'] = wing_metrics_table

            # Inventory Absorption Ratio (IAR) = percentage of stock sold (sales / available * 100), cap at 100%
            total_available_qty = result.get('stock_available', {}).get('total', {}).get('qty', 0) or 0
            result['total_sales_units'] = total_unit
            result['total_available_stock'] = total_available_qty
            if total_available_qty:
                iar = round((total_unit / float(total_available_qty)) * 100.0, 2)
                result['inventory_absorption_ratio'] = min(iar, 100.0)
            else:
                result['inventory_absorption_ratio'] = 0.0
            
            return {
                'success': True,
                'data': result
            }
            
        except Exception as e:
            _logger.error(f"Error getting stock inventory data: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'data': {}
            }
    
    @http.route('/manager_reports/api/stock_inventory_timeseries', type='json', auth='user', methods=['POST'])
    def api_stock_inventory_timeseries(self, **kwargs):
        """Get time-series data for Stock/Inventory Report activities"""
        try:
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            wing_id = kwargs.get('wing_id', None)
            
            date_from_obj, date_to_obj = self._get_date_range(date_from, date_to)
            from datetime import datetime, timedelta, time
            date_from_datetime = datetime.combine(date_from_obj, time.min)
            date_to_datetime = datetime.combine(date_to_obj, time.max)
            
            env = request.env
            has_legacy_col = False
            try:
                env.cr.execute("""
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'property_property' AND column_name = 'legacy'
                """)
                has_legacy_col = env.cr.fetchone() is not None
            except Exception:
                pass

            result = {
                'labels': [],
                'sites_handed_over': [],
                'signed_contracts': [],
                'reservations': [],
                'cancelled_reservations': [],
                'expired_reservations': []
            }
            
            # Determine granularity based on date range
            days_diff = (date_to_obj - date_from_obj).days + 1
            if days_diff <= 31:
                # Daily breakdown
                current_date = date_from_obj
                while current_date <= date_to_obj:
                    day_start = datetime.combine(current_date, time.min)
                    day_end = datetime.combine(current_date, time.max)
                    result['labels'].append(current_date.strftime('%Y-%m-%d'))
                    
                    # Sites handed over (exclude legacy)
                    ts_legacy_join = " JOIN property_property ppts ON ppts.id = ps.property_id AND (ppts.legacy IS NULL OR ppts.legacy = false)" if has_legacy_col else ""
                    query = f"""
                        SELECT COUNT(*)
                        FROM property_sale ps
                        {ts_legacy_join}
                        LEFT JOIN property_reservation pr ON pr.id = ps.reservation_id
                        WHERE ps.state = 'confirm'
                          AND ps.create_date >= %s AND ps.create_date <= %s
                    """
                    params = [day_start, day_end]
                    if wing_id and wing_id != 'all':
                        query += " AND pr.wing_id = %s"
                        params.append(int(wing_id))
                    env.cr.execute(query.strip(), tuple(params))
                    result['sites_handed_over'].append(env.cr.fetchone()[0] or 0)
                    
                    # Signed contracts (exclude legacy)
                    query = f"""
                        SELECT COUNT(*)
                        FROM property_sale ps
                        {ts_legacy_join}
                        LEFT JOIN property_reservation pr ON pr.id = ps.reservation_id
                        WHERE ps.state = 'confirm'
                          AND ps.create_date >= %s AND ps.create_date <= %s
                    """
                    params = [day_start, day_end]
                    if wing_id and wing_id != 'all':
                        query += " AND pr.wing_id = %s"
                        params.append(int(wing_id))
                    env.cr.execute(query, tuple(params))
                    result['signed_contracts'].append(env.cr.fetchone()[0] or 0)
                    
                    # Reservations active during period (exclude legacy)
                    ts_legacy_r = " JOIN property_property pptr ON pptr.id = pr.property_id AND (pptr.legacy IS NULL OR pptr.legacy = false)" if has_legacy_col else ""
                    query = f"""
                        SELECT COUNT(DISTINCT pr.id)
                        FROM property_reservation pr
                        {ts_legacy_r}
                        JOIN property_reservation_configuration prc ON prc.id = pr.reservation_type_id
                        WHERE pr.status IN ('reserved', 'requested', 'pending_sales')
                          AND prc.reservation_type IN ('quick', 'regular')
                          AND pr.create_date <= %s
                          AND (pr.expire_date >= %s OR pr.expire_date IS NULL)
                    """
                    params = [day_end, day_start]
                    if wing_id and wing_id != 'all':
                        query += " AND pr.wing_id = %s"
                        params.append(int(wing_id))
                    env.cr.execute(query.strip(), tuple(params))
                    result['reservations'].append(env.cr.fetchone()[0] or 0)
                    
                    # Cancelled reservations - all types (exclude legacy)
                    query = f"""
                        SELECT COUNT(DISTINCT pr.id)
                        FROM property_reservation pr
                        {ts_legacy_r}
                        WHERE pr.status = 'canceled'
                          AND pr.write_date >= %s AND pr.write_date <= %s
                    """
                    params = [day_start, day_end]
                    if wing_id and wing_id != 'all':
                        query += " AND pr.wing_id = %s"
                        params.append(int(wing_id))
                    env.cr.execute(query.strip(), tuple(params))
                    result['cancelled_reservations'].append(env.cr.fetchone()[0] or 0)
                    
                    # Expired reservations - all types (exclude legacy)
                    query = f"""
                        SELECT COUNT(DISTINCT pr.id)
                        FROM property_reservation pr
                        {ts_legacy_r}
                        WHERE pr.status = 'expired'
                          AND pr.write_date >= %s AND pr.write_date <= %s
                    """
                    params = [day_start, day_end]
                    if wing_id and wing_id != 'all':
                        query += " AND pr.wing_id = %s"
                        params.append(int(wing_id))
                    env.cr.execute(query, tuple(params))
                    result['expired_reservations'].append(env.cr.fetchone()[0] or 0)
                    
                    current_date += timedelta(days=1)
            elif days_diff <= 365:
                # Weekly breakdown
                current_date = date_from_obj
                while current_date <= date_to_obj:
                    week_end = min(current_date + timedelta(days=6), date_to_obj)
                    week_start_dt = datetime.combine(current_date, time.min)
                    week_end_dt = datetime.combine(week_end, time.max)
                    result['labels'].append(f"{current_date.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}")
                    
                    # Sites handed over (exclude legacy)
                    ts_legacy_join = " JOIN property_property ppts ON ppts.id = ps.property_id AND (ppts.legacy IS NULL OR ppts.legacy = false)" if has_legacy_col else ""
                    query = f"""
                        SELECT COUNT(*)
                        FROM property_sale ps
                        {ts_legacy_join}
                        LEFT JOIN property_reservation pr ON pr.id = ps.reservation_id
                        WHERE ps.state = 'confirm'
                          AND ps.create_date >= %s AND ps.create_date <= %s
                    """
                    params = [week_start_dt, week_end_dt]
                    if wing_id and wing_id != 'all':
                        query += " AND pr.wing_id = %s"
                        params.append(int(wing_id))
                    env.cr.execute(query.strip(), tuple(params))
                    result['sites_handed_over'].append(env.cr.fetchone()[0] or 0)
                    
                    # Signed contracts (exclude legacy)
                    query = f"""
                        SELECT COUNT(*)
                        FROM property_sale ps
                        {ts_legacy_join}
                        LEFT JOIN property_reservation pr ON pr.id = ps.reservation_id
                        WHERE ps.state = 'confirm'
                          AND ps.create_date >= %s AND ps.create_date <= %s
                    """
                    params = [week_start_dt, week_end_dt]
                    if wing_id and wing_id != 'all':
                        query += " AND pr.wing_id = %s"
                        params.append(int(wing_id))
                    env.cr.execute(query.strip(), tuple(params))
                    result['signed_contracts'].append(env.cr.fetchone()[0] or 0)
                    
                    # Reservations / cancelled / expired (exclude legacy)
                    ts_legacy_r = " JOIN property_property pptr ON pptr.id = pr.property_id AND (pptr.legacy IS NULL OR pptr.legacy = false)" if has_legacy_col else ""
                    query = f"""
                        SELECT COUNT(DISTINCT pr.id)
                        FROM property_reservation pr
                        {ts_legacy_r}
                        JOIN property_reservation_configuration prc ON prc.id = pr.reservation_type_id
                        WHERE pr.status IN ('reserved', 'requested', 'pending_sales')
                          AND prc.reservation_type IN ('quick', 'regular')
                          AND pr.create_date <= %s
                          AND (pr.expire_date >= %s OR pr.expire_date IS NULL)
                    """
                    params = [week_end_dt, week_start_dt]
                    if wing_id and wing_id != 'all':
                        query += " AND pr.wing_id = %s"
                        params.append(int(wing_id))
                    env.cr.execute(query.strip(), tuple(params))
                    result['reservations'].append(env.cr.fetchone()[0] or 0)
                    
                    query = f"""
                        SELECT COUNT(DISTINCT pr.id)
                        FROM property_reservation pr
                        {ts_legacy_r}
                        WHERE pr.status = 'canceled'
                          AND pr.write_date >= %s AND pr.write_date <= %s
                    """
                    params = [week_start_dt, week_end_dt]
                    if wing_id and wing_id != 'all':
                        query += " AND pr.wing_id = %s"
                        params.append(int(wing_id))
                    env.cr.execute(query.strip(), tuple(params))
                    result['cancelled_reservations'].append(env.cr.fetchone()[0] or 0)
                    
                    query = f"""
                        SELECT COUNT(DISTINCT pr.id)
                        FROM property_reservation pr
                        {ts_legacy_r}
                        WHERE pr.status = 'expired'
                          AND pr.write_date >= %s AND pr.write_date <= %s
                    """
                    params = [week_start_dt, week_end_dt]
                    if wing_id and wing_id != 'all':
                        query += " AND pr.wing_id = %s"
                        params.append(int(wing_id))
                    env.cr.execute(query.strip(), tuple(params))
                    result['expired_reservations'].append(env.cr.fetchone()[0] or 0)
                    
                    current_date += timedelta(days=7)
            else:
                # Monthly breakdown
                current_date = date_from_obj.replace(day=1)
                while current_date <= date_to_obj:
                    # Get last day of month
                    if current_date.month == 12:
                        next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
                    else:
                        next_month = current_date.replace(month=current_date.month + 1, day=1)
                    month_end = min(next_month - timedelta(days=1), date_to_obj)
                    month_start_dt = datetime.combine(current_date, time.min)
                    month_end_dt = datetime.combine(month_end, time.max)
                    result['labels'].append(current_date.strftime('%Y-%m'))
                    
                    # Sites handed over (exclude legacy)
                    ts_legacy_join = " JOIN property_property ppts ON ppts.id = ps.property_id AND (ppts.legacy IS NULL OR ppts.legacy = false)" if has_legacy_col else ""
                    query = f"""
                        SELECT COUNT(*)
                        FROM property_sale ps
                        {ts_legacy_join}
                        LEFT JOIN property_reservation pr ON pr.id = ps.reservation_id
                        WHERE ps.state = 'confirm'
                          AND ps.create_date >= %s AND ps.create_date <= %s
                    """
                    params = [month_start_dt, month_end_dt]
                    if wing_id and wing_id != 'all':
                        query += " AND pr.wing_id = %s"
                        params.append(int(wing_id))
                    env.cr.execute(query.strip(), tuple(params))
                    result['sites_handed_over'].append(env.cr.fetchone()[0] or 0)
                    
                    # Signed contracts (exclude legacy)
                    query = f"""
                        SELECT COUNT(*)
                        FROM property_sale ps
                        {ts_legacy_join}
                        LEFT JOIN property_reservation pr ON pr.id = ps.reservation_id
                        WHERE ps.state = 'confirm'
                          AND ps.create_date >= %s AND ps.create_date <= %s
                    """
                    params = [month_start_dt, month_end_dt]
                    if wing_id and wing_id != 'all':
                        query += " AND pr.wing_id = %s"
                        params.append(int(wing_id))
                    env.cr.execute(query.strip(), tuple(params))
                    result['signed_contracts'].append(env.cr.fetchone()[0] or 0)
                    
                    # Reservations / cancelled / expired (exclude legacy)
                    ts_legacy_r = " JOIN property_property pptr ON pptr.id = pr.property_id AND (pptr.legacy IS NULL OR pptr.legacy = false)" if has_legacy_col else ""
                    query = f"""
                        SELECT COUNT(DISTINCT pr.id)
                        FROM property_reservation pr
                        {ts_legacy_r}
                        JOIN property_reservation_configuration prc ON prc.id = pr.reservation_type_id
                        WHERE pr.status IN ('reserved', 'requested', 'pending_sales')
                          AND prc.reservation_type IN ('quick', 'regular')
                          AND pr.create_date <= %s
                          AND (pr.expire_date >= %s OR pr.expire_date IS NULL)
                    """
                    params = [month_end_dt, month_start_dt]
                    if wing_id and wing_id != 'all':
                        query += " AND pr.wing_id = %s"
                        params.append(int(wing_id))
                    env.cr.execute(query.strip(), tuple(params))
                    result['reservations'].append(env.cr.fetchone()[0] or 0)
                    
                    query = f"""
                        SELECT COUNT(DISTINCT pr.id)
                        FROM property_reservation pr
                        {ts_legacy_r}
                        WHERE pr.status = 'canceled'
                          AND pr.write_date >= %s AND pr.write_date <= %s
                    """
                    params = [month_start_dt, month_end_dt]
                    if wing_id and wing_id != 'all':
                        query += " AND pr.wing_id = %s"
                        params.append(int(wing_id))
                    env.cr.execute(query.strip(), tuple(params))
                    result['cancelled_reservations'].append(env.cr.fetchone()[0] or 0)
                    
                    query = f"""
                        SELECT COUNT(DISTINCT pr.id)
                        FROM property_reservation pr
                        {ts_legacy_r}
                        WHERE pr.status = 'expired'
                          AND pr.write_date >= %s AND pr.write_date <= %s
                    """
                    params = [month_start_dt, month_end_dt]
                    if wing_id and wing_id != 'all':
                        query += " AND pr.wing_id = %s"
                        params.append(int(wing_id))
                    env.cr.execute(query.strip(), tuple(params))
                    result['expired_reservations'].append(env.cr.fetchone()[0] or 0)
                    
                    # Move to next month
                    if current_date.month == 12:
                        current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
                    else:
                        current_date = current_date.replace(month=current_date.month + 1, day=1)
            
            return {
                'success': True,
                'data': result
            }
            
        except Exception as e:
            _logger.error(f"Error getting stock inventory timeseries data: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'data': {}
            }

    # ============================================
    # EXPORTS: REPORT 1 Stock/Inventory
    # ============================================

    def _get_stock_inventory_export_data(self, date_from, date_to):
        """Reuse the same computation as API endpoint for export."""
        res = self.api_stock_inventory_data(date_from=date_from, date_to=date_to)
        if not res or not res.get('success'):
            raise Exception(res.get('error') if res else 'Unknown error generating report data')
        return res['data']

    def _img_data_to_bytes(self, data_url):
        """Convert data:image/png;base64,... to bytes. Returns None if invalid."""
        if not data_url or not isinstance(data_url, str):
            return None
        if 'base64,' not in data_url:
            return None
        try:
            b64 = data_url.split('base64,', 1)[1]
            return base64.b64decode(b64)
        except Exception:
            return None

    @http.route('/manager_reports/api/export_stock_inventory_excel', type='http', auth='user', methods=['POST'], csrf=False)
    def api_export_stock_inventory_excel(self, date_from=None, date_to=None, **kwargs):
        """Export Stock/Inventory report to Excel (tables + charts)."""
        try:
            import xlsxwriter

            data = self._get_stock_inventory_export_data(date_from, date_to)

            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            ws = workbook.add_worksheet('Stock Inventory')

            title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
            sub_fmt = workbook.add_format({'bold': True, 'font_size': 10, 'align': 'center'})
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#E5E7EB', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
            cell_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})
            num_fmt = workbook.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter'})
            money_fmt = workbook.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter', 'num_format': '#,##0'})
            pct_fmt = workbook.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter', 'num_format': '0.00%'})

            row = 0
            ws.merge_range(row, 0, row, 6, 'Stock / Inventory Report', title_fmt)
            row += 1
            ws.merge_range(row, 0, row, 6, f'Date From: {date_from or "All"}   |   Date To: {date_to or "All"}', sub_fmt)
            row += 2

            # KPIs
            ws.write(row, 0, 'No. of sites handed over', header_fmt)
            ws.write(row, 1, data.get('sites_handed_over', 0), num_fmt)
            ws.write(row, 3, 'No. of available properties', header_fmt)
            ws.write(row, 4, data.get('available_properties', 0), num_fmt)
            ws.write(row, 5, 'No. of available sites', header_fmt)
            ws.write(row, 6, data.get('available_sites', 0), num_fmt)
            row += 2

            # Stock Available table
            ws.write(row, 0, 'Stock Available', header_fmt)
            row += 1
            ws.write_row(row, 0, ['Type', 'QTY', 'Estimated Value (Birr)'], header_fmt)
            row += 1
            sa = data.get('stock_available', {}) or {}
            for label, key in [('Residence', 'residence'), ('Shops', 'shops'), ('Mixed', 'mixed'), ('Total', 'total')]:
                ws.write(row, 0, label, cell_fmt)
                ws.write(row, 1, (sa.get(key, {}) or {}).get('qty', 0), num_fmt)
                ws.write(row, 2, (sa.get(key, {}) or {}).get('estimated_value', 0.0), money_fmt)
                row += 1
            row += 1

            # Currently Reserved / Signed Contracts / Cancelled / Expired
            ws.write(row, 0, 'Currently Reserved', header_fmt)
            ws.write(row, 1, data.get('reservations', 0), num_fmt)
            ws.write(row, 2, 'Signed Contracts', header_fmt)
            ws.write(row, 3, data.get('signed_contracts', 0), num_fmt)
            ws.write(row, 4, 'Cancelled', header_fmt)
            ws.write(row, 5, data.get('cancelled_reservations', 0), num_fmt)
            ws.write(row, 6, 'Expired', header_fmt)
            ws.write(row, 7, data.get('expired_reservations', 0), num_fmt)
            row += 2

            # Sales table (discount removed)
            ws.write(row, 0, 'Sales', header_fmt)
            row += 1
            ws.write_row(row, 0, ['Type', 'Unit sold', 'Total Price', 'Advanced Paid', 'Advanced %'], header_fmt)
            row += 1
            for r in (data.get('sales_table') or []):
                ws.write(row, 0, r.get('type', ''), cell_fmt)
                ws.write(row, 1, r.get('unit_sold', 0), num_fmt)
                ws.write(row, 2, r.get('total_price', 0.0), money_fmt)
                ws.write(row, 3, (r.get('advanced_paid') or {}).get('value', 0.0), money_fmt)
                ws.write(row, 4, ((r.get('advanced_paid') or {}).get('percentage', 0.0) or 0.0) / 100.0, pct_fmt)
                row += 1
            row += 1

            # Per Wing: Reservations, Cancelled, Expired
            ws.write(row, 0, 'Per Wing: Reservations, Cancelled, Expired', header_fmt)
            row += 1
            ws.write_row(row, 0, ['Wing', 'Reservations', 'Cancelled', 'Expired'], header_fmt)
            row += 1
            for r in (data.get('wing_metrics_table') or []):
                ws.write(row, 0, r.get('wing_name', ''), cell_fmt)
                ws.write(row, 1, r.get('reservations', 0), num_fmt)
                ws.write(row, 2, r.get('cancelled', 0), num_fmt)
                ws.write(row, 3, r.get('expired', 0), num_fmt)
                row += 1
            row += 1

            # Column widths
            ws.set_column(0, 0, 26)
            ws.set_column(1, 1, 10)
            ws.set_column(2, 4, 18)

            # Charts images (from client) - place in a clean grid (2 per row)
            # Start charts BELOW the sales table, in column H (index 7) to leave space for tables on the left
            img_keys = [
                ('type_mini_chart', 'Sales by Type (Unit Sold)'),
                ('wing_mini_chart', 'Sales Distribution by Wing (Unit Sold)'),
                ('advanced_chart', 'Advanced Paid (Type)'),
                ('wing_advanced_chart', 'Advanced Paid (Wing)'),
                ('wing_metrics_chart', 'Per Wing: Reservations / Cancelled / Expired'),
                ('reservation_activity_chart', 'Currently Reserved / Cancelled / Expired'),
            ]
            
            # Start charts BELOW the sales table (row + 3 for spacing)
            chart_start_row = row + 3
            chart_left_col = 7  # Column H
            chart_right_col = 12  # Column M (5 columns gap between left and right charts)
            chart_row_height = 22  # Rows per chart (title + image + spacing) - increased to prevent overlap
            cur_chart_row = chart_start_row
            
            pair = []
            for k, title in img_keys:
                img_bytes = self._img_data_to_bytes(kwargs.get(k))
                if not img_bytes:
                    continue
                pair.append((k, title, img_bytes))
                if len(pair) == 2:
                    # Place 2 charts side by side
                    for idx, (kk, tt, bb) in enumerate(pair):
                        c = chart_left_col if idx == 0 else chart_right_col
                        # Chart title
                        ws.merge_range(cur_chart_row, c, cur_chart_row, c + 3, tt, header_fmt)
                        # Chart image (smaller scale to fit better and prevent overlap)
                        ws.insert_image(
                            cur_chart_row + 1, c, f'{kk}.png',
                            {
                                'image_data': io.BytesIO(bb),
                                'x_scale': 0.65,
                                'y_scale': 0.65,
                                'x_offset': 5,
                                'y_offset': 5
                            }
                        )
                    cur_chart_row += chart_row_height
                    pair = []
            
            # Handle last single chart if odd number
            if pair:
                kk, tt, bb = pair[0]
                ws.merge_range(cur_chart_row, chart_left_col, cur_chart_row, chart_left_col + 3, tt, header_fmt)
                ws.insert_image(
                    cur_chart_row + 1, chart_left_col, f'{kk}.png',
                    {
                        'image_data': io.BytesIO(bb),
                        'x_scale': 0.65,
                        'y_scale': 0.65,
                        'x_offset': 5,
                        'y_offset': 5
                    }
                )
            
            # Set column widths for chart area (wider to prevent overlap)
            ws.set_column(chart_left_col, chart_left_col + 3, 18)  # Left chart columns
            ws.set_column(chart_right_col, chart_right_col + 3, 18)  # Right chart columns

            workbook.close()
            output.seek(0)
            filename = f'Stock_Inventory_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            return request.make_response(
                output.read(),
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                ],
            )
        except Exception as e:
            _logger.error(f"Error exporting stock inventory Excel: {str(e)}", exc_info=True)
            return request.make_response(f"Error: {str(e)}", status=500)

    @http.route('/manager_reports/api/export_stock_inventory_pdf', type='http', auth='user', methods=['POST'], csrf=False)
    def api_export_stock_inventory_pdf(self, date_from=None, date_to=None, **kwargs):
        """Export Stock/Inventory report to PDF (HTML with print dialog - like sales_performance)."""
        try:
            data = self._get_stock_inventory_export_data(date_from, date_to)

            def img_tag(key):
                src = kwargs.get(key) or ''
                return f'<img src="{src}" style="max-width: 100%; height: auto; border: 1px solid #e5e7eb; border-radius: 8px;" />' if src else ''

            sa = data.get('stock_available', {}) or {}
            sa_res = sa.get('residence', {}) or {}
            sa_shops = sa.get('shops', {}) or {}
            sa_mixed = sa.get('mixed', {}) or {}
            sa_total = sa.get('total', {}) or {}
            refunds = data.get('refunds', {}) or {}
            
            sales_rows_html = ""
            for r in (data.get('sales_table') or []):
                adv_paid = r.get('advanced_paid') or {}
                sales_rows_html += f"""
                <tr>
                    <td>{r.get('type','')}</td>
                    <td style="text-align:right">{r.get('unit_sold',0)}</td>
                    <td style="text-align:right">{int(r.get('total_price',0) or 0):,}</td>
                    <td style="text-align:right">{int(adv_paid.get('value',0) or 0):,}</td>
                    <td style="text-align:right">{(adv_paid.get('percentage',0) or 0):.2f}%</td>
                </tr>
                """

            wing_metrics_rows_html = ""
            for r in (data.get('wing_metrics_table') or []):
                wing_metrics_rows_html += f"""
                <tr>
                    <td>{r.get('wing_name','')}</td>
                    <td style="text-align:right">{r.get('reservations',0)}</td>
                    <td style="text-align:right">{r.get('cancelled',0)}</td>
                    <td style="text-align:right">{r.get('expired',0)}</td>
                </tr>
                """

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Stock / Inventory Report</title>
                <style>
                    @media print {{
                        .no-print {{ display: none; }}
                    }}
                    @media screen {{
                        .print-button {{
                            position: fixed;
                            top: 10px;
                            right: 10px;
                            padding: 10px 20px;
                            background-color: #007bff;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            cursor: pointer;
                            font-size: 14px;
                            z-index: 1000;
                        }}
                        .print-button:hover {{
                            background-color: #0056b3;
                        }}
                    }}
                    body {{ font-family: Arial, sans-serif; margin: 20px; color: #111827; }}
                    h1 {{ margin: 0 0 6px 0; font-size: 18px; text-align: center; }}
                    .sub {{ margin: 0 0 14px 0; color: #374151; font-size: 12px; text-align: center; }}
                    .kpi {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
                    .kpi .card {{ border:1px solid #e5e7eb; border-radius: 8px; padding:10px 12px; min-width: 220px; }}
                    .kpi .label {{ font-size: 12px; color: #6b7280; font-weight: bold; }}
                    .kpi .val {{ font-size: 16px; font-weight: 700; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 10px 0 16px 0; }}
                    th, td {{ border: 1px solid #000; padding: 8px; font-size: 11px; }}
                    th {{ background: #D3D3D3; text-align: left; font-weight: bold; }}
                    .number {{ text-align: right; }}
                    .center {{ text-align: center; }}
                    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }}
                    .chartgrid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
                    .box {{ border:1px solid #e5e7eb; border-radius: 8px; padding: 10px; }}
                    .boxtitle {{ font-weight: 700; margin-bottom: 8px; }}
                </style>
                <script>
                    var printTriggered = false;
                    var referrerUrl = document.referrer || '';
                    
                    function triggerPrint() {{
                        if (printTriggered) {{
                            return; // Only trigger once
                        }}
                        printTriggered = true;
                        try {{
                            window.print();
                        }} catch(e) {{
                            console.error('Print error:', e);
                        }}
                    }}
                    
                    // Only trigger print once when page loads
                    if (document.readyState === 'loading') {{
                        document.addEventListener('DOMContentLoaded', function() {{
                            setTimeout(triggerPrint, 500);
                        }});
                    }} else {{
                        setTimeout(triggerPrint, 500);
                    }}
                    
                    // Close window when print dialog is dismissed (cancelled or printed)
                    window.addEventListener('afterprint', function() {{
                        // Close the window after print dialog closes
                        setTimeout(function() {{
                            window.close();
                        }}, 100);
                    }});
                    
                </script>
            </head>
            <body>
                <button class="print-button no-print" onclick="window.print()">Print</button>
                <h1>Stock / Inventory Report</h1>
                <div class="sub">Date From: {date_from or 'All'} | Date To: {date_to or 'All'}</div>

                <div class="kpi">
                    <div class="card"><div class="label">No. of sites handed over</div><div class="val">{data.get('sites_handed_over',0)}</div></div>
                    <div class="card"><div class="label">No. of available properties</div><div class="val">{data.get('available_properties',0)}</div></div>
                    <div class="card"><div class="label">No. of available sites</div><div class="val">{data.get('available_sites',0)}</div></div>
                    <div class="card"><div class="label">Currently Reserved</div><div class="val">{data.get('reservations',0)}</div></div>
                    <div class="card"><div class="label">Signed Contracts</div><div class="val">{data.get('signed_contracts',0)}</div></div>
                    <div class="card"><div class="label">Cancelled</div><div class="val">{data.get('cancelled_reservations',0)}</div></div>
                    <div class="card"><div class="label">Expired</div><div class="val">{data.get('expired_reservations',0)}</div></div>
                </div>

                <div class="grid">
                    <div class="box">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                            <div>
                                <div class="boxtitle">Stock Available</div>
                                <table>
                                    <thead><tr><th>Type</th><th style="text-align:right">QTY</th><th style="text-align:right">Estimated Value (Birr)</th></tr></thead>
                                    <tbody>
                                        <tr><td>Residence</td><td class="number">{sa_res.get('qty',0)}</td><td class="number">{int(sa_res.get('estimated_value',0) or 0):,}</td></tr>
                                        <tr><td>Shops</td><td class="number">{sa_shops.get('qty',0)}</td><td class="number">{int(sa_shops.get('estimated_value',0) or 0):,}</td></tr>
                                        <tr><td>Mixed</td><td class="number">{sa_mixed.get('qty',0)}</td><td class="number">{int(sa_mixed.get('estimated_value',0) or 0):,}</td></tr>
                                        <tr><td><strong>Total</strong></td><td class="number"><strong>{sa_total.get('qty',0)}</strong></td><td class="number"><strong>{int(sa_total.get('estimated_value',0) or 0):,}</strong></td></tr>
                                    </tbody>
                                </table>
                            </div>
                            <div style="display: flex; align-items: center; justify-content: center;">
                                {img_tag('stock_pie_chart')}
                            </div>
                        </div>
                    </div>
                </div>

                <div class="box">
                    <div class="boxtitle">Sales</div>
                    <table>
                        <thead>
                            <tr>
                                <th>Type</th>
                                <th style="text-align:right">Unit sold</th>
                                <th style="text-align:right">Total Price</th>
                                <th style="text-align:right">Advanced Paid</th>
                                <th style="text-align:right">Advanced %</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sales_rows_html}
                        </tbody>
                    </table>
                </div>

                <div class="box">
                    <div class="boxtitle">Per Wing: Reservations, Cancelled, Expired</div>
                    <table>
                        <thead>
                            <tr>
                                <th>Wing</th>
                                <th style="text-align:right">Reservations</th>
                                <th style="text-align:right">Cancelled</th>
                                <th style="text-align:right">Expired</th>
                            </tr>
                        </thead>
                        <tbody>
                            {wing_metrics_rows_html}
                        </tbody>
                    </table>
                    <div style="margin-top: 12px;">{img_tag('wing_metrics_chart')}</div>
                </div>

                <div class="box">
                    <div class="boxtitle">Graphs</div>
                    <div class="chartgrid">
                        <div>{img_tag('type_mini_chart')}</div>
                        <div>{img_tag('wing_mini_chart')}</div>
                        <div>{img_tag('advanced_chart')}</div>
                        <div>{img_tag('wing_advanced_chart')}</div>
                        <div>{img_tag('reservation_activity_chart')}</div>
                    </div>
                </div>
            </body>
            </html>
            """

            filename = f'Stock_Inventory_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
            return request.make_response(
                html,
                headers=[
                    ('Content-Type', 'text/html'),
                    ('Content-Disposition', f'inline; filename="{filename}"'),
                ],
            )
        except Exception as e:
            _logger.error(f"Error exporting stock inventory PDF: {str(e)}", exc_info=True)
            return request.make_response(f"Error: {str(e)}", status=500)

    # ============================================
    # REPORT 2: Sales Performance Report (Duplicate from sales_performance)
    # ============================================
    
    @http.route('/manager_reports/api/sales_performance_data', type='json', auth='user', methods=['POST'])
    def api_sales_performance_data(self, **kwargs):
        """Get Sales Performance Report data"""
        try:
            period_type = kwargs.get('period_type', 'custom')
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            wing_id = kwargs.get('wing_id', None)

            # Parse dates
            if date_from:
                try:
                    date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                except Exception:
                    date_from_obj = datetime.today().date()
            else:
                date_from_obj = datetime.today().date()

            if date_to:
                try:
                    date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                except Exception:
                    date_to_obj = datetime.today().date()
            else:
                date_to_obj = datetime.today().date()

            yesterday = datetime.today().date() - timedelta(days=1)
            yesterday_from = yesterday
            yesterday_to = yesterday

            date_from_datetime = datetime.combine(date_from_obj, datetime.min.time())
            date_to_datetime = datetime.combine(date_to_obj, datetime.max.time())
            yesterday_from_datetime = datetime.combine(yesterday_from, datetime.min.time())
            yesterday_to_datetime = datetime.combine(yesterday_to, datetime.max.time())

            env = request.env

            # Wing filtering
            wing_domain = []
            wing_user_ids = []
            wing_id_int = None
            if wing_id and wing_id != 'all':
                try:
                    wing_id_int = int(wing_id)
                    wing_domain = [('wing_id', '=', wing_id_int)]
                    if 'property.sales.supervisor' in env:
                        supervisors = env['property.sales.supervisor'].sudo().search([
                            ('sales_team_id.wing_id', '=', wing_id_int)
                        ])
                        supervisor_user_ids = supervisors.mapped('name.id')
                        if 'property.salesperson.mapping' in env:
                            salesperson_mappings = env['property.salesperson.mapping'].sudo().search([
                                ('supervisor_id.name', 'in', supervisor_user_ids)
                            ])
                            salesperson_user_ids = salesperson_mappings.mapped('user_id.id')
                            wing_user_ids = list(set(list(supervisor_user_ids) + list(salesperson_user_ids)))
                        else:
                            wing_user_ids = supervisor_user_ids
                except (ValueError, TypeError):
                    wing_domain = []
                    wing_user_ids = []

            # Prospects
            prospect_count = 0
            prospect_count_yesterday = 0
            if 'temer.lead' in env:
                if wing_domain and wing_id_int:
                    query = """
                        SELECT COUNT(DISTINCT tl.id) FROM temer_lead tl
                        WHERE tl.create_date >= %s AND tl.create_date <= %s
                          AND (tl.wing_id = %s OR EXISTS (
                              SELECT 1 FROM property_reservation pr
                              WHERE pr.crm_lead_id = tl.id AND pr.wing_id = %s))
                    """
                    env.cr.execute(query, (date_from_datetime, date_to_datetime, wing_id_int, wing_id_int))
                    prospect_count += env.cr.fetchone()[0] or 0
                    env.cr.execute(query, (yesterday_from_datetime, yesterday_to_datetime, wing_id_int, wing_id_int))
                    prospect_count_yesterday += env.cr.fetchone()[0] or 0
                else:
                    prospect_count += env['temer.lead'].sudo().search_count([('create_date', '>=', date_from_datetime), ('create_date', '<=', date_to_datetime)])
                    prospect_count_yesterday += env['temer.lead'].sudo().search_count([('create_date', '>=', yesterday_from_datetime), ('create_date', '<=', yesterday_to_datetime)])

            # Reservations
            reservation_count = 0
            reservation_count_yesterday = 0
            if 'temer.lead' in env:
                if wing_domain and wing_id_int:
                    query = """
                        SELECT COUNT(DISTINCT tl.id) FROM temer_lead tl
                        WHERE tl.state = 'reservation' AND tl.create_date >= %s AND tl.create_date <= %s
                          AND (tl.wing_id = %s OR EXISTS (
                              SELECT 1 FROM property_reservation pr
                              WHERE pr.crm_lead_id = tl.id AND pr.wing_id = %s))
                    """
                    env.cr.execute(query, (date_from_datetime, date_to_datetime, wing_id_int, wing_id_int))
                    reservation_count += env.cr.fetchone()[0] or 0
                    env.cr.execute(query, (yesterday_from_datetime, yesterday_to_datetime, wing_id_int, wing_id_int))
                    reservation_count_yesterday += env.cr.fetchone()[0] or 0
                else:
                    reservation_count += env['temer.lead'].sudo().search_count([('state', '=', 'reservation'), ('create_date', '>=', date_from_datetime), ('create_date', '<=', date_to_datetime)])
                    reservation_count_yesterday += env['temer.lead'].sudo().search_count([('state', '=', 'reservation'), ('create_date', '>=', yesterday_from_datetime), ('create_date', '<=', yesterday_to_datetime)])

            # Cancellations
            cancellation_count = 0
            cancellation_count_yesterday = 0
            if 'property.reservation' in env:
                query = "SELECT COUNT(DISTINCT pr.id) FROM property_reservation pr WHERE pr.status = 'canceled' AND pr.write_date >= %s AND pr.write_date <= %s"
                params = [date_from_datetime, date_to_datetime]
                if wing_id_int:
                    query += " AND pr.wing_id = %s"
                    params.append(wing_id_int)
                env.cr.execute(query, tuple(params))
                cancellation_count = env.cr.fetchone()[0] or 0

                params_y = [yesterday_from_datetime, yesterday_to_datetime]
                query_y = "SELECT COUNT(DISTINCT pr.id) FROM property_reservation pr WHERE pr.status = 'canceled' AND pr.write_date >= %s AND pr.write_date <= %s"
                if wing_id_int:
                    query_y += " AND pr.wing_id = %s"
                    params_y.append(wing_id_int)
                env.cr.execute(query_y, tuple(params_y))
                cancellation_count_yesterday = env.cr.fetchone()[0] or 0

            # Sales QTY & Value
            sales_qty = 0
            sales_qty_yesterday = 0
            sales_value = 0.0
            sales_value_yesterday = 0.0
            if 'property.sale' in env:
                sold_sales = env['property.sale'].sudo().search([
                    ('order_date', '>=', date_from_obj), ('order_date', '<=', date_to_obj), ('state', '=', 'confirm')
                ])
                if wing_id_int:
                    sold_sales = sold_sales.filtered(lambda s: s.reservation_id and s.reservation_id.wing_id and s.reservation_id.wing_id.id == wing_id_int)
                sales_qty = len(sold_sales)

                sold_props = env['property.sale'].sudo().search([
                    ('order_date', '>=', date_from_obj), ('order_date', '<=', date_to_obj)
                ])
                sold_props = sold_props.filtered(lambda p: p.property_id.state == 'sold')
                if wing_id_int:
                    sold_props = sold_props.filtered(lambda p: p.reservation_id and p.reservation_id.wing_id and p.reservation_id.wing_id.id == wing_id_int)
                sales_value = sum(sold_props.mapped('sale_price') or [0])

            # Advance Paid
            advance_paid = 0.0
            advance_paid_yesterday = 0.0
            if 'property.sale.payment.term.line' in env:
                payment_lines = env['property.sale.payment.term.line'].sudo().search([
                    ('create_date', '>=', date_from_datetime), ('create_date', '<=', date_to_datetime), ('state', '=', 'paid')
                ])
                if wing_id_int:
                    payment_lines = payment_lines.filtered(lambda p: p.sale_id and p.sale_id.reservation_id and p.sale_id.reservation_id.wing_id and p.sale_id.reservation_id.wing_id.id == wing_id_int)
                advance_paid = sum(payment_lines.mapped('amount') or [0])

            # Opening Stock
            opening_stock_residence_qty = opening_stock_residence_value = 0
            opening_stock_shops_qty = opening_stock_shops_value = 0
            opening_stock_mixed_use_qty = opening_stock_mixed_use_value = 0
            if 'property.property' in env:
                date_from_str = date_from_obj.strftime('%Y-%m-%d')
                date_to_str = date_to_obj.strftime('%Y-%m-%d')
                query = """
                    SELECT COALESCE(p.property_type, '') as property_type,
                           COUNT(*) as qty, COALESCE(SUM(p.unit_price), 0) as total_value
                    FROM property_property p
                    WHERE p.sale_rent = 'for_sale'
                      AND p.create_date::date >= %s AND p.create_date::date <= %s
                      AND NOT EXISTS (SELECT 1 FROM property_sale ps WHERE ps.property_id = p.id AND ps.state != 'cancel')
                    GROUP BY COALESCE(p.property_type, '')
                """
                env.cr.execute(query, [date_from_str, date_to_str])
                for row in env.cr.fetchall():
                    prop_type, qty, total_value = row
                    prop_type_lower = (prop_type or '').lower()
                    qty = int(qty or 0)
                    total_value = float(total_value or 0.0)
                    if prop_type_lower in ('residential', 'residence'):
                        opening_stock_residence_qty = qty
                        opening_stock_residence_value = total_value
                    elif prop_type_lower in ('commercial', 'shop', 'shops'):
                        opening_stock_shops_qty = qty
                        opening_stock_shops_value = total_value
                    elif 'mixed' in prop_type_lower:
                        opening_stock_mixed_use_qty = qty
                        opening_stock_mixed_use_value = total_value

            opening_stock_total_qty = opening_stock_residence_qty + opening_stock_shops_qty + opening_stock_mixed_use_qty
            opening_stock_total_value = opening_stock_residence_value + opening_stock_shops_value + opening_stock_mixed_use_value

            # Plan values
            plan_prospect = plan_reservation = plan_cancellation = plan_sales_qty = 0
            plan_sales_value = plan_advance_paid = plan_conversion = plan_iar = 0.0
            try:
                query = """
                    SELECT COALESCE(SUM(prospect_plan),0), COALESCE(SUM(unit_reservation_plan),0),
                           COALESCE(SUM(deals_closed_plan),0), COALESCE(SUM(total_deal_value_plan),0),
                           COALESCE(SUM(cash_collected_plan),0), COALESCE(AVG(conversion_plan),0),
                           COALESCE(AVG(iar_plan),0)
                    FROM sales_plan WHERE start_date <= %s AND end_date >= %s AND state = 'completed'
                """
                params = [date_to_obj, date_from_obj]
                if wing_id_int:
                    query += " AND wing_id = %s"
                    params.append(wing_id_int)
                env.cr.execute(query, params)
                result = env.cr.fetchone()
                if result:
                    plan_prospect = int(result[0] or 0)
                    plan_reservation = int(result[1] or 0)
                    plan_sales_qty = int(result[2] or 0)
                    plan_sales_value = float(result[3] or 0.0)
                    plan_advance_paid = float(result[4] or 0.0)
                    plan_conversion = float(result[5] or 0.0)
                    plan_iar = float(result[6] or 0.0)
            except Exception as e:
                _logger.error(f"Error fetching plan values: {e}")

            def calc_achievement(actual, plan):
                if plan and plan > 0:
                    return min(round((actual / plan) * 100, 2), 100.0)
                return 0.0

            conversion_rate_actual = round((sales_qty / prospect_count * 100.0) if prospect_count else 0.0, 2)
            plan_conversion_for_achievement = (plan_conversion * 100.0) if plan_conversion and plan_conversion <= 1.0 else plan_conversion
            iar_actual_ratio = round((sales_qty / opening_stock_total_qty) if opening_stock_total_qty else 0.0, 4)
            iar_actual_pct = round(iar_actual_ratio * 100.0, 2)

            wings = []
            if 'property.sales.wing' in env:
                wings = env['property.sales.wing'].sudo().search_read([], ['id', 'name'])

            return {
                'success': True,
                'wings': wings,
                'data': {
                    'performance': {
                        'prospect': {'plan': plan_prospect, 'actual': prospect_count, 'achievement': calc_achievement(prospect_count, plan_prospect)},
                        'reservation': {'plan': plan_reservation, 'actual': reservation_count, 'achievement': calc_achievement(reservation_count, plan_reservation)},
                        'cancellation': {'plan': plan_cancellation, 'actual': cancellation_count, 'achievement': calc_achievement(cancellation_count, plan_cancellation)},
                        'sales_qty': {'plan': plan_sales_qty, 'actual': sales_qty, 'achievement': calc_achievement(sales_qty, plan_sales_qty)},
                        'sales_value': {'plan': plan_sales_value, 'actual': sales_value, 'achievement': calc_achievement(sales_value, plan_sales_value)},
                        'advance_paid': {'plan': plan_advance_paid, 'actual': advance_paid, 'achievement': calc_achievement(advance_paid, plan_advance_paid)},
                        'conversion_rate': {'plan': round(plan_conversion, 4), 'actual': conversion_rate_actual, 'achievement': calc_achievement(conversion_rate_actual, plan_conversion_for_achievement)},
                        'iar': {'plan': round(plan_iar, 4), 'actual': iar_actual_ratio, 'achievement': calc_achievement(iar_actual_pct, plan_iar)},
                    },
                    'opening_stock': {
                        'residence': {'qty': opening_stock_residence_qty, 'value': opening_stock_residence_value},
                        'shops': {'qty': opening_stock_shops_qty, 'value': opening_stock_shops_value},
                        'mixed_use': {'qty': opening_stock_mixed_use_qty, 'value': opening_stock_mixed_use_value},
                        'total': {'qty': opening_stock_total_qty, 'value': opening_stock_total_value},
                    },
                },
                'date_from': date_from_obj.strftime('%Y-%m-%d'),
                'date_to': date_to_obj.strftime('%Y-%m-%d'),
                'period_type': period_type,
            }
        except Exception as e:
            _logger.error(f"Error getting sales performance data: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e), 'data': {}}

    # ============================================
    # REPORT 3: Collection Report (Duplicate from collection_reports)
    # ============================================
    
    @http.route('/manager_reports/api/collection_data', type='json', auth='user', methods=['POST'])
    def api_collection_data(self, **kwargs):
        """Get Collection Report data - Duplicated from collection_reports module"""
        # Redirect to the original collection_reports endpoint
        # The frontend will call the original endpoint directly
        try:
            # Just return success - frontend will call /collection_reports/api/get_general_info directly
            return {
                'success': True,
                'message': 'Use /collection_reports/api/get_general_info endpoint'
            }
        except Exception as e:
            _logger.error(f"Error getting collection data: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'data': {}
            }
    
    @http.route('/manager_reports/api/sales_performance_timeseries', type='json', auth='user', methods=['POST'])
    def api_sales_performance_timeseries(self, **kwargs):
        """Get time-series data for Sales Performance Report activities"""
        try:
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            wing_id = kwargs.get('wing_id', None)
            
            date_from_obj, date_to_obj = self._get_date_range(date_from, date_to)
            from datetime import datetime, timedelta, time
            date_from_datetime = datetime.combine(date_from_obj, time.min)
            date_to_datetime = datetime.combine(date_to_obj, time.max)
            
            env = request.env
            result = {
                'labels': [],
                'prospects': [],
                'reservations': [],
                'cancellations': [],
                'sales_qty': [],
                'sales_value': [],
                'advance_paid': []
            }
            
            # Determine granularity based on date range
            days_diff = (date_to_obj - date_from_obj).days + 1
            wing_id_int = None
            if wing_id and wing_id != 'all':
                try:
                    wing_id_int = int(wing_id)
                except Exception:
                    wing_id_int = None
            
            if days_diff <= 31:
                # Daily breakdown
                current_date = date_from_obj
                while current_date <= date_to_obj:
                    day_start = datetime.combine(current_date, time.min)
                    day_end = datetime.combine(current_date, time.max)
                    result['labels'].append(current_date.strftime('%Y-%m-%d'))
                    
                    # Get data for this day - query from sales_performance module data
                    # Prospects
                    prospects = 0
                    if 'crm.lead' in env:
                        lead_domain = [
                            ('create_date', '>=', day_start),
                            ('create_date', '<=', day_end)
                        ]
                        # Note: crm.lead doesn't support wing filtering directly
                        # Only count if no wing filter is applied, or skip wing filtering for crm.lead
                        if not wing_id_int:
                            prospects = env['crm.lead'].sudo().search_count(lead_domain)
                        # If wing_id is specified, skip crm.lead prospects (they don't have wing association)
                        # Only count temer.lead prospects which support wing filtering
                    if 'temer.lead' in env and wing_id_int:
                        temer_lead_domain = [
                            ('create_date', '>=', day_start),
                            ('create_date', '<=', day_end),
                            ('wing_id', '=', wing_id_int)
                        ]
                        prospects += env['temer.lead'].sudo().search_count(temer_lead_domain)
                    elif 'temer.lead' in env and not wing_id_int:
                        temer_lead_domain = [
                            ('create_date', '>=', day_start),
                            ('create_date', '<=', day_end)
                        ]
                        prospects += env['temer.lead'].sudo().search_count(temer_lead_domain)
                    
                    # Reservations
                    reservations = 0
                    if 'property.reservation' in env:
                        res_domain = [
                            ('create_date', '>=', day_start),
                            ('create_date', '<=', day_end),
                            ('status', 'in', ['reserved', 'requested', 'pending_sales'])
                        ]
                        if wing_id_int:
                            res_domain.append(('wing_id', '=', wing_id_int))
                        reservations = env['property.reservation'].sudo().search_count(res_domain)
                    
                    # Cancellations
                    cancellations = 0
                    if 'property.reservation' in env:
                        cancel_domain = [
                            ('write_date', '>=', day_start),
                            ('write_date', '<=', day_end),
                            ('status', '=', 'canceled')
                        ]
                        if wing_id_int:
                            cancel_domain.append(('wing_id', '=', wing_id_int))
                        cancellations = env['property.reservation'].sudo().search_count(cancel_domain)
                    
                    # Sales QTY
                    sales_qty = 0
                    sales_value = 0.0
                    if 'property.sale' in env:
                        sale_domain = [
                            ('create_date', '>=', day_start),
                            ('create_date', '<=', day_end),
                            ('state', '=', 'confirm')
                        ]
                        if wing_id_int:
                            sale_domain.append(('reservation_id.wing_id', '=', wing_id_int))
                        sales = env['property.sale'].sudo().search(sale_domain)
                        sales_qty = len(sales)
                        sales_value = sum(sale.sale_price or 0.0 for sale in sales if hasattr(sale, 'sale_price'))
                    
                    # Advance Paid
                    advance_paid = 0.0
                    if 'property.reservation.payment' in env:
                        payment_domain = [
                            ('create_date', '>=', day_start),
                            ('create_date', '<=', day_end),
                            ('status', '=', 'approved')
                        ]
                        if wing_id_int:
                            payment_domain.append(('reservation_id.wing_id', '=', wing_id_int))
                        payments = env['property.reservation.payment'].sudo().search(payment_domain)
                        advance_paid = sum(payment.amount or 0.0 for payment in payments if hasattr(payment, 'amount'))
                    
                    result['prospects'].append(prospects)
                    result['reservations'].append(reservations)
                    result['cancellations'].append(cancellations)
                    result['sales_qty'].append(sales_qty)
                    result['sales_value'].append(sales_value)
                    result['advance_paid'].append(advance_paid)
                    
                    current_date += timedelta(days=1)
            elif days_diff <= 365:
                # Weekly breakdown
                current_date = date_from_obj
                while current_date <= date_to_obj:
                    week_end = min(current_date + timedelta(days=6), date_to_obj)
                    week_start_dt = datetime.combine(current_date, time.min)
                    week_end_dt = datetime.combine(week_end, time.max)
                    result['labels'].append(f"{current_date.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}")
                    
                    # Similar queries but for week range
                    prospects = 0
                    if 'crm.lead' in env:
                        lead_domain = [
                            ('create_date', '>=', week_start_dt),
                            ('create_date', '<=', week_end_dt)
                        ]
                        # Note: crm.lead doesn't support wing filtering directly
                        if not wing_id_int:
                            prospects = env['crm.lead'].sudo().search_count(lead_domain)
                    if 'temer.lead' in env and wing_id_int:
                        temer_lead_domain = [
                            ('create_date', '>=', week_start_dt),
                            ('create_date', '<=', week_end_dt),
                            ('wing_id', '=', wing_id_int)
                        ]
                        prospects += env['temer.lead'].sudo().search_count(temer_lead_domain)
                    elif 'temer.lead' in env and not wing_id_int:
                        temer_lead_domain = [
                            ('create_date', '>=', week_start_dt),
                            ('create_date', '<=', week_end_dt)
                        ]
                        prospects += env['temer.lead'].sudo().search_count(temer_lead_domain)
                    
                    reservations = 0
                    if 'property.reservation' in env:
                        res_domain = [
                            ('create_date', '>=', week_start_dt),
                            ('create_date', '<=', week_end_dt),
                            ('status', 'in', ['reserved', 'requested', 'pending_sales'])
                        ]
                        if wing_id_int:
                            res_domain.append(('wing_id', '=', wing_id_int))
                        reservations = env['property.reservation'].sudo().search_count(res_domain)
                    
                    cancellations = 0
                    if 'property.reservation' in env:
                        cancel_domain = [
                            ('write_date', '>=', week_start_dt),
                            ('write_date', '<=', week_end_dt),
                            ('status', '=', 'canceled')
                        ]
                        if wing_id_int:
                            cancel_domain.append(('wing_id', '=', wing_id_int))
                        cancellations = env['property.reservation'].sudo().search_count(cancel_domain)
                    
                    sales_qty = 0
                    sales_value = 0.0
                    if 'property.sale' in env:
                        sale_domain = [
                            ('create_date', '>=', week_start_dt),
                            ('create_date', '<=', week_end_dt),
                            ('state', '=', 'confirm')
                        ]
                        if wing_id_int:
                            sale_domain.append(('reservation_id.wing_id', '=', wing_id_int))
                        sales = env['property.sale'].sudo().search(sale_domain)
                        sales_qty = len(sales)
                        sales_value = sum(sale.sale_price or 0.0 for sale in sales if hasattr(sale, 'sale_price'))
                    
                    advance_paid = 0.0
                    if 'property.reservation.payment' in env:
                        payment_domain = [
                            ('create_date', '>=', week_start_dt),
                            ('create_date', '<=', week_end_dt),
                            ('status', '=', 'approved')
                        ]
                        if wing_id_int:
                            payment_domain.append(('reservation_id.wing_id', '=', wing_id_int))
                        payments = env['property.reservation.payment'].sudo().search(payment_domain)
                        advance_paid = sum(payment.amount or 0.0 for payment in payments if hasattr(payment, 'amount'))
                    
                    result['prospects'].append(prospects)
                    result['reservations'].append(reservations)
                    result['cancellations'].append(cancellations)
                    result['sales_qty'].append(sales_qty)
                    result['sales_value'].append(sales_value)
                    result['advance_paid'].append(advance_paid)
                    
                    current_date += timedelta(days=7)
            else:
                # Monthly breakdown
                current_date = date_from_obj.replace(day=1)
                while current_date <= date_to_obj:
                    if current_date.month == 12:
                        next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
                    else:
                        next_month = current_date.replace(month=current_date.month + 1, day=1)
                    month_end = min(next_month - timedelta(days=1), date_to_obj)
                    month_start_dt = datetime.combine(current_date, time.min)
                    month_end_dt = datetime.combine(month_end, time.max)
                    result['labels'].append(current_date.strftime('%Y-%m'))
                    
                    prospects = 0
                    if 'crm.lead' in env:
                        lead_domain = [
                            ('create_date', '>=', month_start_dt),
                            ('create_date', '<=', month_end_dt)
                        ]
                        # Note: crm.lead doesn't support wing filtering directly
                        if not wing_id_int:
                            prospects = env['crm.lead'].sudo().search_count(lead_domain)
                    if 'temer.lead' in env and wing_id_int:
                        temer_lead_domain = [
                            ('create_date', '>=', month_start_dt),
                            ('create_date', '<=', month_end_dt),
                            ('wing_id', '=', wing_id_int)
                        ]
                        prospects += env['temer.lead'].sudo().search_count(temer_lead_domain)
                    elif 'temer.lead' in env and not wing_id_int:
                        temer_lead_domain = [
                            ('create_date', '>=', month_start_dt),
                            ('create_date', '<=', month_end_dt)
                        ]
                        prospects += env['temer.lead'].sudo().search_count(temer_lead_domain)
                    
                    reservations = 0
                    if 'property.reservation' in env:
                        res_domain = [
                            ('create_date', '>=', month_start_dt),
                            ('create_date', '<=', month_end_dt),
                            ('status', 'in', ['reserved', 'requested', 'pending_sales'])
                        ]
                        if wing_id_int:
                            res_domain.append(('wing_id', '=', wing_id_int))
                        reservations = env['property.reservation'].sudo().search_count(res_domain)
                    
                    cancellations = 0
                    if 'property.reservation' in env:
                        cancel_domain = [
                            ('write_date', '>=', month_start_dt),
                            ('write_date', '<=', month_end_dt),
                            ('status', '=', 'canceled')
                        ]
                        if wing_id_int:
                            cancel_domain.append(('wing_id', '=', wing_id_int))
                        cancellations = env['property.reservation'].sudo().search_count(cancel_domain)
                    
                    sales_qty = 0
                    sales_value = 0.0
                    if 'property.sale' in env:
                        sale_domain = [
                            ('create_date', '>=', month_start_dt),
                            ('create_date', '<=', month_end_dt),
                            ('state', '=', 'confirm')
                        ]
                        if wing_id_int:
                            sale_domain.append(('reservation_id.wing_id', '=', wing_id_int))
                        sales = env['property.sale'].sudo().search(sale_domain)
                        sales_qty = len(sales)
                        sales_value = sum(sale.sale_price or 0.0 for sale in sales if hasattr(sale, 'sale_price'))
                    
                    advance_paid = 0.0
                    if 'property.reservation.payment' in env:
                        payment_domain = [
                            ('create_date', '>=', month_start_dt),
                            ('create_date', '<=', month_end_dt),
                            ('status', '=', 'approved')
                        ]
                        if wing_id_int:
                            payment_domain.append(('reservation_id.wing_id', '=', wing_id_int))
                        payments = env['property.reservation.payment'].sudo().search(payment_domain)
                        advance_paid = sum(payment.amount or 0.0 for payment in payments if hasattr(payment, 'amount'))
                    
                    result['prospects'].append(prospects)
                    result['reservations'].append(reservations)
                    result['cancellations'].append(cancellations)
                    result['sales_qty'].append(sales_qty)
                    result['sales_value'].append(sales_value)
                    result['advance_paid'].append(advance_paid)
                    
                    if current_date.month == 12:
                        current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
                    else:
                        current_date = current_date.replace(month=current_date.month + 1, day=1)
            
            return {
                'success': True,
                'data': result
            }
            
        except Exception as e:
            _logger.error(f"Error getting sales performance timeseries data: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'data': {}
            }

    # ============================================
    # REPORT 4: Stock and Collection Summary
    # ============================================
    
    @http.route('/manager_reports/api/stock_collection_summary_data', type='json', auth='user', methods=['POST'])
    def api_stock_collection_summary_data(self, **kwargs):
        """Get Stock and Collection Summary Report data.

        METRIC EXPLANATIONS, QUERIES & CALCULATIONS:
        ===========================================

        1. Total Average progress compared to plan (e.g. 65.18%)
           - Same as Average achievement in %.
           - Calculation: (Total Stock Sold QTY / Total Stock Available QTY) * 100, capped at 100%.
           - Example: sold_total=865, available_total=1327 => 865/1327*100 = 65.18%

        2. No. of sites ready for handover (e.g. 865)
           - Count of all confirmed property sales (no date filter; includes all time).
           - Query: SELECT COUNT(DISTINCT ps.id) FROM property_sale ps
                    WHERE ps.state = 'confirm'
           - Wing filter applied if wing_id != 'all'.

        3. Total Collection to date (e.g. 3,300,000)
           - Sum of all paid installment amounts within the date range.
           - Query: collection.installment.payment where payment_date in [date_from, date_to], status='paid'
           - Calculation: sum(payment.amount)

        4. Average collection per day (e.g. 345.51)
           - Total collection / number of days in selected range.
           - Calculation: total_collection / (date_to - date_from).days + 1
           - Example: 3,300,000 / 9555 days (2000-01-01 to 2026-02-23) ≈ 345.51

        5. Average collection per site (e.g. 3,300,000)
           - Total collection / count of distinct properties that had payments in the period.
           - Calculation: total_collection / len(unique property_ids from payments)
           - If only 1 property had payments: 3,300,000 / 1 = 3,300,000

        6. Average achievement in % (e.g. 65.18%)
           - Same as Total Average progress compared to plan.
           - Calculation: stock_sold.total.achievement_percent = (sold_qty / available_qty) * 100
        """
        try:
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            wing_id = kwargs.get('wing_id', None)
            
            date_from_obj, date_to_obj = self._get_date_range(date_from, date_to)
            env = request.env
            result = {}
            
            # 1. Total Stock Available - only within selected date range
            # Count properties created in [date_from, date_to] that are still available (no confirmed sale)
            stock_available = {
                'residential': {'qty': 0, 'values': 0.0},
                'commercial': {'qty': 0, 'values': 0.0},
                'mixed_use': {'qty': 0, 'values': 0.0},
                'total': {'qty': 0, 'values': 0.0}
            }
            
            date_from_datetime = datetime.combine(date_from_obj, datetime.min.time())
            date_to_datetime = datetime.combine(date_to_obj, datetime.max.time())
            
            if 'property.property' in env:
                query = """
                    SELECT p.id,
                           COALESCE(p.property_type, '') as property_type,
                           COALESCE(p.unit_price, p.price, 0) as unit_price
                    FROM property_property p
                    WHERE p.state IN ('available', 'draft')
                      AND p.create_date >= %s
                      AND p.create_date <= %s
                      AND NOT EXISTS (
                          SELECT 1 FROM property_sale ps
                          WHERE ps.property_id = p.id AND ps.state = 'confirm'
                      )
                """
                params = [date_from_datetime, date_to_datetime]
                if wing_id and wing_id != 'all':
                    wing_id_int = int(wing_id)
                    query = """
                        SELECT p.id,
                               COALESCE(p.property_type, '') as property_type,
                               COALESCE(p.unit_price, p.price, 0) as unit_price
                        FROM property_property p
                        WHERE p.state IN ('available', 'draft')
                          AND p.create_date >= %s
                          AND p.create_date <= %s
                          AND NOT EXISTS (
                              SELECT 1 FROM property_sale ps
                              WHERE ps.property_id = p.id AND ps.state = 'confirm'
                          )
                          AND EXISTS (
                              SELECT 1 FROM property_reservation pr
                              WHERE pr.property_id = p.id AND pr.wing_id = %s
                          )
                    """
                    params = [date_from_datetime, date_to_datetime, wing_id_int]
                env.cr.execute(query, tuple(params))
                for _id, property_type, price in env.cr.fetchall():
                    prop_type_lower = (property_type or '').lower()
                    price_val = float(price or 0.0)
                    if 'residence' in prop_type_lower or 'residential' in prop_type_lower:
                        stock_available['residential']['qty'] += 1
                        stock_available['residential']['values'] += price_val
                    elif 'shop' in prop_type_lower or 'commercial' in prop_type_lower or 'office' in prop_type_lower:
                        stock_available['commercial']['qty'] += 1
                        stock_available['commercial']['values'] += price_val
                    elif 'mixed' in prop_type_lower:
                        stock_available['mixed_use']['qty'] += 1
                        stock_available['mixed_use']['values'] += price_val
                    stock_available['total']['qty'] += 1
                    stock_available['total']['values'] += price_val
            
            result['stock_available'] = stock_available
            
            # 2. Total Stock Sold - use property.sale (confirmed sales) in date range, same as Stock/Inventory and sites_ready_for_handover
            stock_sold = {
                'residential': {'qty': 0, 'values': 0.0, 'achievement_percent': 0.0},
                'commercial': {'qty': 0, 'values': 0.0, 'achievement_percent': 0.0},
                'mixed_use': {'qty': 0, 'values': 0.0, 'achievement_percent': 0.0},
                'total': {'qty': 0, 'values': 0.0, 'achievement_percent': 0.0}
            }
            
            date_from_datetime = datetime.combine(date_from_obj, datetime.min.time())
            date_to_datetime = datetime.combine(date_to_obj, datetime.max.time())
            if 'property.sale' in env:
                query = """
                    SELECT COALESCE(p.property_type, '') as property_type,
                           COALESCE(ps.sale_price, 0) as sale_price
                    FROM property_sale ps
                    JOIN property_property p ON p.id = ps.property_id
                    LEFT JOIN property_reservation pr ON pr.id = ps.reservation_id
                    WHERE ps.state = 'confirm'
                      AND ps.create_date >= %s
                      AND ps.create_date <= %s
                """
                params = [date_from_datetime, date_to_datetime]
                if wing_id and wing_id != 'all':
                    query += " AND pr.wing_id = %s"
                    params.append(int(wing_id))
                env.cr.execute(query, tuple(params))
                for property_type, sale_price in env.cr.fetchall():
                    prop_type_lower = (property_type or '').lower()
                    price = float(sale_price or 0.0)
                    if 'residence' in prop_type_lower or 'residential' in prop_type_lower:
                        stock_sold['residential']['qty'] += 1
                        stock_sold['residential']['values'] += price
                    elif 'shop' in prop_type_lower or 'commercial' in prop_type_lower or 'office' in prop_type_lower:
                        stock_sold['commercial']['qty'] += 1
                        stock_sold['commercial']['values'] += price
                    elif 'mixed' in prop_type_lower:
                        stock_sold['mixed_use']['qty'] += 1
                        stock_sold['mixed_use']['values'] += price
                    stock_sold['total']['qty'] += 1
                    stock_sold['total']['values'] += price
                
                # Achievement % = (sold qty in category / available qty in category) * 100, cap at 100%
                # All sold counts are already in date range (create_date filter above).
                for key in ('residential', 'commercial', 'mixed_use', 'total'):
                    avail_qty = stock_available[key]['qty'] or 0
                    sold_qty = stock_sold[key]['qty'] or 0
                    if avail_qty > 0:
                        pct = (sold_qty / avail_qty) * 100
                        stock_sold[key]['achievement_percent'] = min(100.0, round(pct, 2))
                    else:
                        stock_sold[key]['achievement_percent'] = 0.0
            
            result['stock_sold'] = stock_sold
            
            # 3. Collection Metrics - Use collection.installment.payment with payment_date
            total_collection = 0.0
            if 'collection.installment.payment' in env:
                payment_domain = [
                    ('payment_date', '>=', date_from_obj),
                    ('payment_date', '<=', date_to_obj),
                    ('status', '=', 'paid')
                ]
                payments = env['collection.installment.payment'].sudo().search(payment_domain)
                total_collection = sum(payments.mapped('amount') or [0.0])
            
            result['total_collection'] = total_collection
            
            # Calculate averages
            days_diff = (date_to_obj - date_from_obj).days + 1
            result['average_collection_per_day'] = total_collection / days_diff if days_diff > 0 else 0.0
            
            # Average collection per site (total collection / number of unique properties with collections)
            if 'collection.installment.payment' in env:
                payment_domain = [
                    ('payment_date', '>=', date_from_obj),
                    ('payment_date', '<=', date_to_obj),
                    ('status', '=', 'paid')
                ]
                payments = env['collection.installment.payment'].sudo().search(payment_domain)
                # Get unique properties from payments via collection orders
                collection_ids = payments.mapped('installment_id.collection_id.id')
                if collection_ids:
                    collections = env['collection.order'].sudo().search([('id', 'in', collection_ids)])
                    unique_properties = len(set(collections.mapped('property_id.id')))
                    result['average_collection_per_site'] = total_collection / unique_properties if unique_properties > 0 else 0.0
                else:
                    result['average_collection_per_site'] = 0.0
            else:
                result['average_collection_per_site'] = 0.0
            
            # Average achievement percentage
            if stock_available['total']['values'] > 0:
                result['average_achievement_percent'] = stock_sold['total']['achievement_percent']
            else:
                result['average_achievement_percent'] = 0.0
            
            # 4. Total Average progress compared to plan
            # This is the average achievement percentage (already calculated above)
            result['total_average_progress_compared_to_plan'] = result['average_achievement_percent']
            
            # 5. No. of sites ready for handover
            # Sites that are sold (confirmed) but may not yet be delivered
            # This is similar to "sites handed over" but for ready-to-deliver status
            sites_ready_for_handover = 0
            if 'property.sale' in env:
                query = """
                    SELECT COUNT(DISTINCT ps.id)
                    FROM property_sale ps
                    LEFT JOIN property_reservation pr ON pr.id = ps.reservation_id
                    WHERE ps.state = 'confirm'
                """
                params = []
                if wing_id and wing_id != 'all':
                    query += " AND pr.wing_id = %s"
                    params.append(int(wing_id))
                env.cr.execute(query, tuple(params))
                sites_ready_for_handover = env.cr.fetchone()[0] or 0
            result['sites_ready_for_handover'] = sites_ready_for_handover
            
            return {
                'success': True,
                'data': result
            }
            
        except Exception as e:
            _logger.error(f"Error getting stock collection summary data: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'data': {}
            }
    
    @http.route('/manager_reports/api/collection_timeseries', type='json', auth='user', methods=['POST'])
    def api_collection_timeseries(self, **kwargs):
        """Get time-series data for Collection Report activities"""
        try:
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            
            date_from_obj, date_to_obj = self._get_date_range(date_from, date_to)
            from datetime import datetime, timedelta, time
            date_from_datetime = datetime.combine(date_from_obj, time.min)
            date_to_datetime = datetime.combine(date_to_obj, time.max)
            
            env = request.env
            result = {
                'labels': [],
                'collected_amount': [],
                'collected_clients': [],
                'discount_amount': []
            }
            
            # Determine granularity based on date range
            days_diff = (date_to_obj - date_from_obj).days + 1
            
            if days_diff <= 31:
                # Daily breakdown
                current_date = date_from_obj
                while current_date <= date_to_obj:
                    day_start = datetime.combine(current_date, time.min)
                    day_end = datetime.combine(current_date, time.max)
                    result['labels'].append(current_date.strftime('%Y-%m-%d'))
                    
                    # Get collection data for this day
                    collected_amount = 0.0
                    collected_clients = 0
                    discount_amount = 0.0
                    
                    # Use collection.installment.payment for payment data
                    if 'collection.installment.payment' in env:
                        payments = env['collection.installment.payment'].sudo().search([
                            ('payment_date', '>=', day_start),
                            ('payment_date', '<=', day_end),
                            ('status', '=', 'paid')
                        ])
                        collected_amount = sum(payments.mapped('amount') or [0.0])
                        collected_clients = len(set(payments.mapped('installment_id.collection_id.partner_id.id')))
                    
                    # Get discount from collection.installment
                    if 'collection.installment' in env:
                        installments = env['collection.installment'].sudo().search([
                            ('create_date', '>=', day_start),
                            ('create_date', '<=', day_end)
                        ])
                        discount_amount = sum(installments.mapped('discount_amount') or [0.0])
                    
                    result['collected_amount'].append(collected_amount)
                    result['collected_clients'].append(collected_clients)
                    result['discount_amount'].append(discount_amount)
                    
                    current_date += timedelta(days=1)
            elif days_diff <= 365:
                # Weekly breakdown
                current_date = date_from_obj
                while current_date <= date_to_obj:
                    week_end = min(current_date + timedelta(days=6), date_to_obj)
                    week_start_dt = datetime.combine(current_date, time.min)
                    week_end_dt = datetime.combine(week_end, time.max)
                    result['labels'].append(f"{current_date.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}")
                    
                    collected_amount = 0.0
                    collected_clients = 0
                    discount_amount = 0.0
                    
                    # Use collection.installment.payment for payment data
                    if 'collection.installment.payment' in env:
                        payments = env['collection.installment.payment'].sudo().search([
                            ('payment_date', '>=', week_start_dt),
                            ('payment_date', '<=', week_end_dt),
                            ('status', '=', 'paid')
                        ])
                        collected_amount = sum(payments.mapped('amount') or [0.0])
                        collected_clients = len(set(payments.mapped('installment_id.collection_id.partner_id.id')))
                    
                    # Get discount from collection.installment
                    if 'collection.installment' in env:
                        installments = env['collection.installment'].sudo().search([
                            ('create_date', '>=', week_start_dt),
                            ('create_date', '<=', week_end_dt)
                        ])
                        discount_amount = sum(installments.mapped('discount_amount') or [0.0])
                    
                    result['collected_amount'].append(collected_amount)
                    result['collected_clients'].append(collected_clients)
                    result['discount_amount'].append(discount_amount)
                    
                    current_date += timedelta(days=7)
            else:
                # Monthly breakdown
                current_date = date_from_obj.replace(day=1)
                while current_date <= date_to_obj:
                    if current_date.month == 12:
                        next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
                    else:
                        next_month = current_date.replace(month=current_date.month + 1, day=1)
                    month_end = min(next_month - timedelta(days=1), date_to_obj)
                    month_start_dt = datetime.combine(current_date, time.min)
                    month_end_dt = datetime.combine(month_end, time.max)
                    result['labels'].append(current_date.strftime('%Y-%m'))
                    
                    collected_amount = 0.0
                    collected_clients = 0
                    discount_amount = 0.0
                    
                    # Use collection.installment.payment for payment data
                    if 'collection.installment.payment' in env:
                        payments = env['collection.installment.payment'].sudo().search([
                            ('payment_date', '>=', month_start_dt),
                            ('payment_date', '<=', month_end_dt),
                            ('status', '=', 'paid')
                        ])
                        collected_amount = sum(payments.mapped('amount') or [0.0])
                        collected_clients = len(set(payments.mapped('installment_id.collection_id.partner_id.id')))
                    
                    # Get discount from collection.installment
                    if 'collection.installment' in env:
                        installments = env['collection.installment'].sudo().search([
                            ('create_date', '>=', month_start_dt),
                            ('create_date', '<=', month_end_dt)
                        ])
                        discount_amount = sum(installments.mapped('discount_amount') or [0.0])
                    
                    result['collected_amount'].append(collected_amount)
                    result['collected_clients'].append(collected_clients)
                    result['discount_amount'].append(discount_amount)
                    
                    if current_date.month == 12:
                        current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
                    else:
                        current_date = current_date.replace(month=current_date.month + 1, day=1)
            
            return {
                'success': True,
                'data': result
            }
            
        except Exception as e:
            _logger.error(f"Error getting collection timeseries data: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'data': {}
            }
    
    @http.route('/manager_reports/api/stock_collection_summary_timeseries', type='json', auth='user', methods=['POST'])
    def api_stock_collection_summary_timeseries(self, **kwargs):
        """Get time-series data for Stock Collection Summary Report activities"""
        try:
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            wing_id = kwargs.get('wing_id', None)
            
            date_from_obj, date_to_obj = self._get_date_range(date_from, date_to)
            from datetime import datetime, timedelta, time
            date_from_datetime = datetime.combine(date_from_obj, time.min)
            date_to_datetime = datetime.combine(date_to_obj, time.max)
            
            env = request.env
            result = {
                'labels': [],
                'stock_sold_residential': [],
                'stock_sold_commercial': [],
                'stock_sold_mixed_use': [],
                'collection_amount': []
            }
            
            # Determine granularity based on date range
            days_diff = (date_to_obj - date_from_obj).days + 1
            wing_id_int = None
            if wing_id and wing_id != 'all':
                try:
                    wing_id_int = int(wing_id)
                except Exception:
                    wing_id_int = None
            
            if days_diff <= 31:
                # Daily breakdown
                current_date = date_from_obj
                while current_date <= date_to_obj:
                    day_start = datetime.combine(current_date, time.min)
                    day_end = datetime.combine(current_date, time.max)
                    result['labels'].append(current_date.strftime('%Y-%m-%d'))
                    
                    # Stock sold (QTY)
                    sold_residential = 0
                    sold_commercial = 0
                    sold_mixed_use = 0
                    if 'property.sale' in env:
                        query = """
                            SELECT COALESCE(p.property_type, '') as property_type
                            FROM property_sale ps
                            JOIN property_property p ON p.id = ps.property_id
                            LEFT JOIN property_reservation pr ON pr.id = ps.reservation_id
                            WHERE ps.state = 'confirm'
                              AND ps.create_date >= %s AND ps.create_date <= %s
                        """
                        params = [day_start, day_end]
                        if wing_id_int:
                            query += " AND pr.wing_id = %s"
                            params.append(wing_id_int)
                        env.cr.execute(query, tuple(params))
                        for (prop_type,) in env.cr.fetchall():
                            prop_type_lower = (prop_type or '').lower()
                            if 'residence' in prop_type_lower or 'residential' in prop_type_lower:
                                sold_residential += 1
                            elif 'shop' in prop_type_lower or 'commercial' in prop_type_lower:
                                sold_commercial += 1
                            elif 'mixed' in prop_type_lower:
                                sold_mixed_use += 1
                    
                    # Collection (money)
                    collection_amount = 0.0
                    if 'collection.installment.payment' in env:
                        payments = env['collection.installment.payment'].sudo().search([
                            ('payment_date', '>=', day_start),
                            ('payment_date', '<=', day_end),
                            ('status', '=', 'paid')
                        ])
                        collection_amount = sum(payments.mapped('amount') or [0.0])
                    
                    result['stock_sold_residential'].append(sold_residential)
                    result['stock_sold_commercial'].append(sold_commercial)
                    result['stock_sold_mixed_use'].append(sold_mixed_use)
                    result['collection_amount'].append(collection_amount)
                    
                    current_date += timedelta(days=1)
            elif days_diff <= 365:
                # Weekly breakdown
                current_date = date_from_obj
                while current_date <= date_to_obj:
                    week_end = min(current_date + timedelta(days=6), date_to_obj)
                    week_start_dt = datetime.combine(current_date, time.min)
                    week_end_dt = datetime.combine(week_end, time.max)
                    result['labels'].append(f"{current_date.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}")
                    
                    sold_residential = 0
                    sold_commercial = 0
                    sold_mixed_use = 0
                    if 'property.sale' in env:
                        query = """
                            SELECT COALESCE(p.property_type, '') as property_type
                            FROM property_sale ps
                            JOIN property_property p ON p.id = ps.property_id
                            LEFT JOIN property_reservation pr ON pr.id = ps.reservation_id
                            WHERE ps.state = 'confirm'
                              AND ps.create_date >= %s AND ps.create_date <= %s
                        """
                        params = [week_start_dt, week_end_dt]
                        if wing_id_int:
                            query += " AND pr.wing_id = %s"
                            params.append(wing_id_int)
                        env.cr.execute(query, tuple(params))
                        for (prop_type,) in env.cr.fetchall():
                            prop_type_lower = (prop_type or '').lower()
                            if 'residence' in prop_type_lower or 'residential' in prop_type_lower:
                                sold_residential += 1
                            elif 'shop' in prop_type_lower or 'commercial' in prop_type_lower:
                                sold_commercial += 1
                            elif 'mixed' in prop_type_lower:
                                sold_mixed_use += 1
                    
                    collection_amount = 0.0
                    if 'collection.installment.payment' in env:
                        payments = env['collection.installment.payment'].sudo().search([
                            ('payment_date', '>=', week_start_dt),
                            ('payment_date', '<=', week_end_dt),
                            ('status', '=', 'paid')
                        ])
                        collection_amount = sum(payments.mapped('amount') or [0.0])
                    
                    result['stock_sold_residential'].append(sold_residential)
                    result['stock_sold_commercial'].append(sold_commercial)
                    result['stock_sold_mixed_use'].append(sold_mixed_use)
                    result['collection_amount'].append(collection_amount)
                    
                    current_date += timedelta(days=7)
            else:
                # Monthly breakdown
                current_date = date_from_obj.replace(day=1)
                while current_date <= date_to_obj:
                    if current_date.month == 12:
                        next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
                    else:
                        next_month = current_date.replace(month=current_date.month + 1, day=1)
                    month_end = min(next_month - timedelta(days=1), date_to_obj)
                    month_start_dt = datetime.combine(current_date, time.min)
                    month_end_dt = datetime.combine(month_end, time.max)
                    result['labels'].append(current_date.strftime('%Y-%m'))
                    
                    sold_residential = 0
                    sold_commercial = 0
                    sold_mixed_use = 0
                    if 'property.sale' in env:
                        query = """
                            SELECT COALESCE(p.property_type, '') as property_type
                            FROM property_sale ps
                            JOIN property_property p ON p.id = ps.property_id
                            LEFT JOIN property_reservation pr ON pr.id = ps.reservation_id
                            WHERE ps.state = 'confirm'
                              AND ps.create_date >= %s AND ps.create_date <= %s
                        """
                        params = [month_start_dt, month_end_dt]
                        if wing_id_int:
                            query += " AND pr.wing_id = %s"
                            params.append(wing_id_int)
                        env.cr.execute(query, tuple(params))
                        for (prop_type,) in env.cr.fetchall():
                            prop_type_lower = (prop_type or '').lower()
                            if 'residence' in prop_type_lower or 'residential' in prop_type_lower:
                                sold_residential += 1
                            elif 'shop' in prop_type_lower or 'commercial' in prop_type_lower:
                                sold_commercial += 1
                            elif 'mixed' in prop_type_lower:
                                sold_mixed_use += 1
                    
                    collection_amount = 0.0
                    if 'collection.installment.payment' in env:
                        payments = env['collection.installment.payment'].sudo().search([
                            ('payment_date', '>=', month_start_dt),
                            ('payment_date', '<=', month_end_dt),
                            ('status', '=', 'paid')
                        ])
                        collection_amount = sum(payments.mapped('amount') or [0.0])
                    
                    result['stock_sold_residential'].append(sold_residential)
                    result['stock_sold_commercial'].append(sold_commercial)
                    result['stock_sold_mixed_use'].append(sold_mixed_use)
                    result['collection_amount'].append(collection_amount)
                    
                    if current_date.month == 12:
                        current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
                    else:
                        current_date = current_date.replace(month=current_date.month + 1, day=1)
            
            return {
                'success': True,
                'data': result
            }
            
        except Exception as e:
            _logger.error(f"Error getting stock collection summary timeseries data: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'data': {}
            }

    # ============================================
    # EXPORTS: REPORT 2 Sales Performance
    # ============================================

    @http.route('/manager_reports/api/export_sales_performance_excel', type='json', auth='user', methods=['POST'], csrf=False)
    def api_export_sales_performance_excel(self, **kwargs):
        """Export Sales Performance report to Excel with charts."""
        try:
            import xlsxwriter
            import base64
            
            # Extract parameters from JSON-RPC data
            period_type = kwargs.get('period_type', 'custom')
            date_from = kwargs.get('date_from') or None
            date_to = kwargs.get('date_to') or None
            wing_id = kwargs.get('wing_id') or None
            chart_images = kwargs.get('chart_images', {}) or {}
            
            _logger.info(f"Sales Performance Excel export - Received JSON data: period_type={period_type}, date_from={date_from}, date_to={date_to}, wing_id={wing_id}")
            _logger.info(f"Sales Performance Excel export - Chart images keys: {list(chart_images.keys())}")
            for key, img_data in chart_images.items():
                if img_data and len(img_data) > 100:
                    _logger.info(f"Sales Performance Excel export - Chart {key}: provided ({len(img_data)} bytes)")
                else:
                    _logger.warning(f"Sales Performance Excel export - Chart {key}: missing or invalid (length: {len(img_data) if img_data else 0})")
            
            # Get data from sales_performance API - use direct controller call with request.env
            from odoo.addons.sales_performance.controllers import sales_performance_controller
            sp_controller = sales_performance_controller.SalesPerformanceController()
            
            # Ensure we're using the request environment
            env = request.env
            report_result = sp_controller.api_report_data(
                period_type=period_type or 'custom',
                date_from=date_from,
                date_to=date_to,
                wing_id=wing_id
            )
            
            if not report_result or not report_result.get('success'):
                error_msg = report_result.get('error', 'Unknown error') if report_result else 'Failed to get report data'
                _logger.error(f"Excel export error: {error_msg}")
                return request.make_response(f"Error: {error_msg}", status=500)
            
            report_data = report_result.get('data', {})
            if not report_data:
                _logger.error("Excel export: No data in report_result")
                return request.make_response("Error: No data returned from API", status=500)
            
            performance = report_data.get('performance', {})
            opening_stock = report_data.get('opening_stock', {})
            
            _logger.info(f"Excel export - Performance data keys: {list(performance.keys())}")
            _logger.info(f"Excel export - Opening stock data: {opening_stock}")
            _logger.info(f"Excel export - Performance sample (prospect): {performance.get('prospect', {})}")
            _logger.info(f"Excel export - Chart images provided: {[k for k in ['actual_plan_chart', 'achievement_chart', 'opening_stock_pie_chart', 'plan_actual_line_chart', 'performance_overview_chart'] if kwargs.get(k)]}")
            
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            ws = workbook.add_worksheet('Sales Performance')
            
            title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
            sub_fmt = workbook.add_format({'bold': True, 'font_size': 10, 'align': 'center'})
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#E5E7EB', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
            cell_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})
            num_fmt = workbook.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter'})
            money_fmt = workbook.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter', 'num_format': '#,##0.00'})
            
            row = 0
            ws.merge_range(row, 0, row, 4, 'Sales Performance Report', title_fmt)
            row += 1
            # Format date display
            date_from_display = date_from if date_from else "All"
            date_to_display = date_to if date_to else "All"
            wing_display = wing_id if wing_id and wing_id != "all" else "All"
            ws.merge_range(row, 0, row, 4, f'Date From: {date_from_display}   |   Date To: {date_to_display}   |   Wing: {wing_display}', sub_fmt)
            row += 2
            
            # Opening Stock table
            ws.write(row, 0, 'Opening Stock', header_fmt)
            row += 1
            ws.write_row(row, 0, ['Type', 'QTY', 'Estimated Value (Birr)'], header_fmt)
            row += 1
            # Extract opening stock values
            os_res = opening_stock.get('residence', {}) or {}
            os_shops = opening_stock.get('shops', {}) or {}
            os_mixed = opening_stock.get('mixed_use', {}) or {}
            os_total = opening_stock.get('total', {}) or {}
            
            os_res_qty = int(os_res.get('qty', 0) or 0)
            os_res_value = float(os_res.get('value', 0) or 0)
            os_shops_qty = int(os_shops.get('qty', 0) or 0)
            os_shops_value = float(os_shops.get('value', 0) or 0)
            os_mixed_qty = int(os_mixed.get('qty', 0) or 0)
            os_mixed_value = float(os_mixed.get('value', 0) or 0)
            os_total_qty = int(os_total.get('qty', 0) or 0)
            os_total_value = float(os_total.get('value', 0) or 0)
            
            ws.write(row, 0, 'Residence', cell_fmt)
            ws.write(row, 1, os_res_qty, num_fmt)
            ws.write(row, 2, os_res_value, money_fmt)
            row += 1
            ws.write(row, 0, 'Shops', cell_fmt)
            ws.write(row, 1, os_shops_qty, num_fmt)
            ws.write(row, 2, os_shops_value, money_fmt)
            row += 1
            ws.write(row, 0, 'Mixed use', cell_fmt)
            ws.write(row, 1, os_mixed_qty, num_fmt)
            ws.write(row, 2, os_mixed_value, money_fmt)
            row += 1
            ws.write(row, 0, 'Total', cell_fmt)
            ws.write(row, 1, os_total_qty, num_fmt)
            ws.write(row, 2, os_total_value, money_fmt)
            row += 2
            
            # Performance table (4 columns; Conversion rate and IAR as rows with plan and achievement)
            conv_data = performance.get('conversion_rate') or {}
            iar_data = performance.get('iar') or {}
            conversion_rate = conv_data.get('actual') or 0
            conversion_plan = conv_data.get('plan') or 0
            conversion_achievement = conv_data.get('achievement') or 0
            iar = iar_data.get('actual') or 0
            iar_plan = iar_data.get('plan') or 0
            iar_achievement = iar_data.get('achievement') or 0
            ws.write(row, 0, 'Sales Metrics', header_fmt)
            row += 1
            ws.write_row(row, 0, ['Sales Metrics', 'Plan', 'Actual', 'Metrics %'], header_fmt)
            row += 1
            
            perf_rows = [
                ('Prospects', performance.get('prospect', {})),
                ('Reservations', performance.get('reservation', {})),
                ('Sales QTY', performance.get('sales_qty', {})),
                ('Sales Value', performance.get('sales_value', {})),
                ('Advance paid', performance.get('advance_paid', {})),
            ]
            
            for label, perf_data in perf_rows:
                if not perf_data:
                    perf_data = {}
                plan_val = perf_data.get('plan') or 0
                actual_val = perf_data.get('actual') or 0
                achievement_val = perf_data.get('achievement') or 0
                ws.write(row, 0, label, cell_fmt)
                if 'sales_value' in label or 'advance_paid' in label:
                    plan_val = float(plan_val) if plan_val else 0.0
                    actual_val = float(actual_val) if actual_val else 0.0
                    ws.write(row, 1, plan_val, money_fmt)
                    ws.write(row, 2, actual_val, money_fmt)
                else:
                    plan_val = int(plan_val) if plan_val else 0
                    actual_val = int(actual_val) if actual_val else 0
                    ws.write(row, 1, plan_val, num_fmt)
                    ws.write(row, 2, actual_val, num_fmt)
                achievement_val = float(achievement_val) if achievement_val else 0.0
                ws.write(row, 3, f"{achievement_val:.2f}%", num_fmt)
                row += 1
            
            ws.write(row, 0, 'Conversion rate (deal/leads)', cell_fmt)
            ws.write(row, 1, float(conversion_plan), num_fmt)
            ws.write(row, 2, float(conversion_rate), num_fmt)
            ws.write(row, 3, f"{float(conversion_achievement):.2f}%", num_fmt)
            row += 1
            ws.write(row, 0, 'IAR (Inventory absorption rate)', cell_fmt)
            ws.write(row, 1, f"{float(iar_plan):.2f}%", num_fmt)
            ws.write(row, 2, f"{(float(iar) * 100):.2f}%", num_fmt)
            ws.write(row, 3, f"{float(iar_achievement):.2f}%", num_fmt)
            row += 1
            
            ws.set_column(0, 0, 30)
            ws.set_column(1, 3, 18)
            
            # Charts images (from client) - place after tables in column H
            chart_start_row = row + 2  # Start charts after the performance table
            chart_left_col = 7
            chart_row_height = 22
            cur_chart_row = chart_start_row
            
            img_keys = [('opening_stock_pie_chart', 'Opening Stock Distribution')]
            for k in (sorted(chart_images.keys()) if chart_images else []):
                if k.startswith('wing_chart_') and chart_images.get(k):
                    img_keys.append((k, k.replace('wing_chart_', 'Wing ')))
            
            charts_added = 0
            pair = []
            for k, title in img_keys:
                img_data = chart_images.get(k)  # Get from chart_images dict instead of kwargs
                if not img_data:
                    _logger.warning(f"Chart image not provided: {k}")
                    continue
                img_bytes = self._img_data_to_bytes(img_data)
                if not img_bytes:
                    _logger.warning(f"Chart image conversion failed: {k}")
                    continue
                pair.append((k, title, img_bytes))
                charts_added += 1
                if len(pair) == 2:
                    for idx, (kk, tt, bb) in enumerate(pair):
                        c = chart_left_col if idx == 0 else chart_left_col + 5
                        ws.merge_range(cur_chart_row, c, cur_chart_row, c + 3, tt, header_fmt)
                        try:
                            ws.insert_image(
                                cur_chart_row + 1, c, f'{kk}.png',
                                {
                                    'image_data': io.BytesIO(bb),
                                    'x_scale': 0.65,
                                    'y_scale': 0.65,
                                    'x_offset': 5,
                                    'y_offset': 5
                                }
                            )
                        except Exception as e:
                            _logger.error(f"Error inserting chart {kk}: {str(e)}")
                    cur_chart_row += chart_row_height
                    pair = []
            
            if pair:
                kk, tt, bb = pair[0]
                ws.merge_range(cur_chart_row, chart_left_col, cur_chart_row, chart_left_col + 3, tt, header_fmt)
                try:
                    ws.insert_image(
                        cur_chart_row + 1, chart_left_col, f'{kk}.png',
                        {
                            'image_data': io.BytesIO(bb),
                            'x_scale': 0.65,
                            'y_scale': 0.65,
                            'x_offset': 5,
                            'y_offset': 5
                        }
                    )
                except Exception as e:
                    _logger.error(f"Error inserting chart {kk}: {str(e)}")
            
            _logger.info(f"Excel export: Added {charts_added} charts")
            
            ws.set_column(chart_left_col, chart_left_col + 3, 18)
            ws.set_column(chart_left_col + 5, chart_left_col + 8, 18)
            
            workbook.close()
            output.seek(0)
            
            # Return as base64 for JSON-RPC response
            file_data = base64.b64encode(output.read()).decode('utf-8')
            return {
                'success': True,
                'file_data': file_data,
                'filename': f'Sales_Report_{date_from or "all"}_{date_to or "all"}.xlsx'
            }
        except Exception as e:
            _logger.error(f"Error exporting sales performance Excel: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    @http.route('/manager_reports/api/export_sales_performance_pdf', type='json', auth='user', methods=['POST'], csrf=False)
    def api_export_sales_performance_pdf(self, **kwargs):
        """Export Sales Performance report to PDF with charts."""
        try:
            # Extract parameters from JSON-RPC data
            period_type = kwargs.get('period_type', 'custom')
            date_from = kwargs.get('date_from') or None
            date_to = kwargs.get('date_to') or None
            wing_id = kwargs.get('wing_id') or None
            chart_images = kwargs.get('chart_images', {}) or {}
            
            _logger.info(f"Sales Performance PDF export - Received JSON data: period_type={period_type}, date_from={date_from}, date_to={date_to}, wing_id={wing_id}")
            _logger.info(f"Sales Performance PDF export - Chart images keys: {list(chart_images.keys())}")
            for key, img_data in chart_images.items():
                if img_data and len(img_data) > 100:
                    _logger.info(f"Sales Performance PDF export - Chart {key}: provided ({len(img_data)} bytes)")
                else:
                    _logger.warning(f"Sales Performance PDF export - Chart {key}: missing or invalid (length: {len(img_data) if img_data else 0})")
            
            # Get data from sales_performance API
            from odoo.addons.sales_performance.controllers import sales_performance_controller
            sp_controller = sales_performance_controller.SalesPerformanceController()
            report_result = sp_controller.api_report_data(
                period_type=period_type,
                date_from=date_from,
                date_to=date_to,
                wing_id=wing_id
            )
            
            if not report_result or not report_result.get('success'):
                error_msg = report_result.get('error', 'Unknown error') if report_result else 'Failed to get report data'
                return request.make_response(f"Error: {error_msg}", status=500)
            
            report_data = report_result.get('data', {})
            if not report_data:
                _logger.error("PDF export: No data in report_result")
                return request.make_response("Error: No data returned from API", status=500)
            
            performance = report_data.get('performance', {})
            opening_stock = report_data.get('opening_stock', {})
            
            _logger.info(f"PDF export - Performance data keys: {list(performance.keys())}")
            _logger.info(f"PDF export - Opening stock data: {opening_stock}")
            _logger.info(f"PDF export - Performance sample (prospect): {performance.get('prospect', {})}")
            
            os_res = opening_stock.get('residence', {}) or {}
            os_shops = opening_stock.get('shops', {}) or {}
            os_mixed = opening_stock.get('mixed_use', {}) or {}
            os_total = opening_stock.get('total', {}) or {}
            
            os_res_qty = int(os_res.get('qty', 0) or 0)
            os_res_value = int(os_res.get('value', 0) or 0)
            os_shops_qty = int(os_shops.get('qty', 0) or 0)
            os_shops_value = int(os_shops.get('value', 0) or 0)
            os_mixed_qty = int(os_mixed.get('qty', 0) or 0)
            os_mixed_value = int(os_mixed.get('value', 0) or 0)
            os_total_qty = int(os_total.get('qty', 0) or 0)
            os_total_value = int(os_total.get('value', 0) or 0)
            
            conv_data = performance.get('conversion_rate') or {}
            iar_data = performance.get('iar') or {}
            conversion_rate = conv_data.get('actual') or 0
            conversion_plan = conv_data.get('plan') or 0
            conversion_achievement = conv_data.get('achievement') or 0
            iar_val = iar_data.get('actual') or 0
            iar_plan_val = iar_data.get('plan') or 0
            iar_achievement_val = iar_data.get('achievement') or 0
            
            def img_tag(key):
                src = chart_images.get(key) or ''  # Get from chart_images dict
                return f'<img src="{src}" style="max-width: 100%; height: auto; border: 1px solid #e5e7eb; border-radius: 8px;" />' if src else ''
            
            perf_rows_html = ""
            perf_rows = [
                ('Prospects', performance.get('prospect', {})),
                ('Reservations', performance.get('reservation', {})),
                ('Sales QTY', performance.get('sales_qty', {})),
                ('Sales Value', performance.get('sales_value', {})),
                ('Advance paid', performance.get('advance_paid', {})),
            ]
            
            for label, perf_data in perf_rows:
                if not perf_data:
                    perf_data = {}
                plan_val = perf_data.get('plan') or 0
                actual_val = perf_data.get('actual') or 0
                achievement_val = min(float(perf_data.get('achievement', 0) or 0), 100.0)
                if 'sales_value' in label or 'advance_paid' in label:
                    plan_val = f"{float(plan_val):,.2f}" if plan_val else "0.00"
                    actual_val = f"{float(actual_val):,.2f}" if actual_val else "0.00"
                else:
                    plan_val = int(plan_val) if plan_val else 0
                    actual_val = int(actual_val) if actual_val else 0
                perf_rows_html += f"""
                <tr>
                    <td>{label}</td>
                    <td class="number">{plan_val}</td>
                    <td class="number">{actual_val}</td>
                    <td class="number">{achievement_val:.2f}%</td>
                </tr>
                """
            perf_rows_html += f"""
                <tr>
                    <td>Conversion rate (deal/leads)</td>
                    <td class="number">{float(conversion_plan):.2f}</td>
                    <td class="number">{float(conversion_rate):.2f}</td>
                    <td class="number">{float(conversion_achievement):.2f}%</td>
                </tr>
                <tr>
                    <td>IAR (Inventory absorption rate)</td>
                    <td class="number">{float(iar_plan_val):.2f}%</td>
                    <td class="number">{float(iar_val) * 100:.2f}%</td>
                    <td class="number">{float(iar_achievement_val):.2f}%</td>
                </tr>
                """
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Sales Performance Report</title>
                <style>
                    @media print {{
                        .no-print {{ display: none; }}
                    }}
                    @media screen {{
                        .print-button {{
                            position: fixed;
                            top: 10px;
                            right: 10px;
                            padding: 10px 20px;
                            background-color: #007bff;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            cursor: pointer;
                            font-size: 14px;
                            z-index: 1000;
                        }}
                        .print-button:hover {{
                            background-color: #0056b3;
                        }}
                    }}
                    body {{ font-family: Arial, sans-serif; margin: 20px; color: #111827; }}
                    h1 {{ margin: 0 0 6px 0; font-size: 18px; text-align: center; }}
                    .sub {{ margin: 0 0 14px 0; color: #374151; font-size: 12px; text-align: center; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 10px 0 16px 0; }}
                    th, td {{ border: 1px solid #000; padding: 8px; font-size: 11px; }}
                    th {{ background: #D3D3D3; text-align: left; font-weight: bold; }}
                    .number {{ text-align: right; }}
                    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }}
                    .box {{ border:1px solid #e5e7eb; border-radius: 8px; padding: 10px; }}
                    .boxtitle {{ font-weight: 700; margin-bottom: 8px; }}
                    .chartgrid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
                </style>
                <script>
                    var printTriggered = false;
                    function triggerPrint() {{
                        if (printTriggered) return;
                        printTriggered = true;
                        try {{
                            window.print();
                        }} catch(e) {{
                            console.error('Print error:', e);
                        }}
                    }}
                    if (document.readyState === 'loading') {{
                        document.addEventListener('DOMContentLoaded', function() {{
                            setTimeout(triggerPrint, 500);
                        }});
                    }} else {{
                        setTimeout(triggerPrint, 500);
                    }}
                    window.addEventListener('afterprint', function() {{
                        setTimeout(function() {{
                            window.close();
                        }}, 100);
                    }});
                </script>
            </head>
            <body>
                <button class="print-button no-print" onclick="window.print()">Print</button>
                <h1>Sales Performance Report</h1>
                <div class="sub">Date From: {date_from if date_from else 'All'} | Date To: {date_to if date_to else 'All'} | Wing: {wing_id if wing_id and wing_id != 'all' else 'All'}</div>

                <div class="grid">
                    <div class="box">
                        <div class="boxtitle">Opening Stock</div>
                        <table>
                            <thead><tr><th>Type</th><th style="text-align:right">QTY</th><th style="text-align:right">Estimated Value (Birr)</th></tr></thead>
                            <tbody>
                                <tr><td>Residence</td><td class="number">{os_res_qty}</td><td class="number">{os_res_value:,}</td></tr>
                                <tr><td>Shops</td><td class="number">{os_shops_qty}</td><td class="number">{os_shops_value:,}</td></tr>
                                <tr><td>Mixed use</td><td class="number">{os_mixed_qty}</td><td class="number">{os_mixed_value:,}</td></tr>
                                <tr><td><strong>Total</strong></td><td class="number"><strong>{os_total_qty}</strong></td><td class="number"><strong>{os_total_value:,}</strong></td></tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="box">
                        <div class="boxtitle">Opening Stock Distribution</div>
                        {img_tag('opening_stock_pie_chart')}
                    </div>
                </div>

                <div class="box">
                    <div class="boxtitle">Sales Metrics</div>
                    <table>
                        <thead>
                            <tr>
                                <th>Sales Metrics</th>
                                <th style="text-align:right">Plan</th>
                                <th style="text-align:right">Actual</th>
                                <th style="text-align:right">Metrics %</th>
                            </tr>
                        </thead>
                        <tbody>
                            {perf_rows_html}
                        </tbody>
                    </table>
                </div>

                <div class="box">
                    <div class="boxtitle">Per Wing: Plan vs Actual</div>
                    <div class="chartgrid">
                        {''.join(f'<div>{img_tag(k)}</div>' for k, v in (chart_images or {}).items() if k.startswith('wing_chart_') and v)}
                    </div>
                </div>
            </body>
            </html>
            """
            
            filename = f'Sales_Performance_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
            return request.make_response(
                html,
                headers=[
                    ('Content-Type', 'text/html'),
                    ('Content-Disposition', f'inline; filename="{filename}"'),
                ],
            )
        except Exception as e:
            _logger.error(f"Error exporting sales performance PDF: {str(e)}", exc_info=True)
            return request.make_response(f"Error: {str(e)}", status=500)

    def _get_collection_export_data(self, date_from, date_to):
        """Get Collection Report data for export."""
        try:
            from odoo.addons.collection_reports.controllers import collection_report_controller
            coll_controller = collection_report_controller.SalesReportController()
            result = coll_controller.api_collection_plan(
                period_type='custom',
                date_from=date_from,
                date_to=date_to
            )
            if not result or not result.get('success'):
                raise Exception(result.get('error') if result else 'Unknown error generating report data')
            data = result.get('data', {})
            
            # Calculate discount percentage based on total sold properties value
            discount_amount = data.get('discount_amount', 0.0) or 0.0
            discount_percentage = 0.0
            
            # Get total value of sold properties in date range
            env = request.env
            total_sold_properties_value = 0.0
            if 'property.sale' in env:
                from datetime import datetime, time
                date_from_obj = fields.Date.from_string(date_from) if date_from else None
                date_to_obj = fields.Date.from_string(date_to) if date_to else None
                if date_from_obj and date_to_obj:
                    date_from_datetime = datetime.combine(date_from_obj, time.min)
                    date_to_datetime = datetime.combine(date_to_obj, time.max)
                    
                    sales_domain = [
                        ('state', 'in', ['signed', 'contract', 'confirmed', 'sold', 'confirm']),
                        ('create_date', '>=', date_from_datetime),
                        ('create_date', '<=', date_to_datetime)
                    ]
                    sales = env['property.sale'].sudo().search(sales_domain)
                    # Use sale_price instead of total_price
                    total_sold_properties_value = sum(sale.sale_price or 0.0 for sale in sales if hasattr(sale, 'sale_price'))
            
            # Calculate discount percentage based on sold properties total
            if total_sold_properties_value > 0:
                discount_percentage = (discount_amount / total_sold_properties_value) * 100
            else:
                discount_percentage = data.get('discount_percentage', 0.0) or 0.0
            
            # Transform to match our structure
            return {
                'total_clients': data.get('total_clients', 0),
                'total_sites': data.get('no_of_sites', 0),
                'stock_under_collection': {
                    'residences': data.get('stock_residences', 0),
                    'shops': data.get('stock_shops', 0),
                    'mixed_use': data.get('stock_mixed_use', 0)
                },
                'total_receivable': data.get('total_receivable', 0.0),
                'collection_performance': {
                    'collected_amount': {
                        'plan': data.get('collected_amount_plan', 0.0),
                        'actual': data.get('collected_amount_actual', 0.0),
                        'achievement': data.get('collected_amount_achievement', 0.0)
                    },
                    'collected_from_clients': {
                        'plan': data.get('collected_clients_plan', 0),
                        'actual': data.get('collected_clients_actual', 0),
                        'achievement': data.get('collected_clients_achievement', 0.0)
                    }
                },
                'discount_given': {
                    'amount': discount_amount,
                    'percentage': discount_percentage
                },
                'qty': (data.get('stock_residences', 0) or 0) + (data.get('stock_shops', 0) or 0) + (data.get('stock_mixed_use', 0) or 0),
                'properties_returned': 0
            }
        except Exception as e:
            _logger.error(f"Error getting collection export data: {str(e)}", exc_info=True)
            raise

    @http.route('/manager_reports/api/export_collection_excel', type='json', auth='user', methods=['POST'], csrf=False)
    def api_export_collection_excel(self, **kwargs):
        """Export Collection Report to Excel with charts."""
        try:
            import xlsxwriter
            import base64
            
            # Extract parameters from JSON-RPC data
            date_from = kwargs.get('date_from') or None
            date_to = kwargs.get('date_to') or None
            chart_images = kwargs.get('chart_images', {}) or {}
            
            _logger.info(f"Collection Excel export - Received JSON data: date_from={date_from}, date_to={date_to}")
            _logger.info(f"Collection Excel export - Chart images keys: {list(chart_images.keys())}")
            for key, img_data in chart_images.items():
                if img_data and len(img_data) > 100:
                    _logger.info(f"Collection Excel export - Chart {key}: provided ({len(img_data)} bytes)")
                else:
                    _logger.warning(f"Collection Excel export - Chart {key}: missing or invalid (length: {len(img_data) if img_data else 0})")
            
            # Get data
            data = self._get_collection_export_data(date_from, date_to)
            
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            ws = workbook.add_worksheet('Collection Report')
            
            title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
            sub_fmt = workbook.add_format({'bold': True, 'font_size': 10, 'align': 'center'})
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#E5E7EB', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
            cell_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})
            num_fmt = workbook.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter'})
            money_fmt = workbook.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter', 'num_format': '#,##0.00'})
            
            row = 0
            ws.merge_range(row, 0, row, 4, 'Collection Report', title_fmt)
            row += 1
            date_from_display = date_from if date_from else "All"
            date_to_display = date_to if date_to else "All"
            ws.merge_range(row, 0, row, 4, f'Date From: {date_from_display}   |   Date To: {date_to_display}', sub_fmt)
            row += 2
            
            # KPI Summary
            ws.write(row, 0, 'Summary', header_fmt)
            row += 1
            ws.write_row(row, 0, ['Metric', 'Value'], header_fmt)
            row += 1
            ws.write(row, 0, 'Total No. of clients', cell_fmt)
            ws.write(row, 1, data.get('total_clients', 0), num_fmt)
            row += 1
            ws.write(row, 0, 'No. of sites', cell_fmt)
            ws.write(row, 1, data.get('total_sites', 0), num_fmt)
            row += 1
            ws.write(row, 0, 'Total Receivable Amount', cell_fmt)
            ws.write(row, 1, data.get('total_receivable', 0.0), money_fmt)
            row += 1
            ws.write(row, 0, 'Stock under collection (units)', cell_fmt)
            ws.write(row, 1, data.get('qty', 0), num_fmt)
            row += 1
            ws.write(row, 0, 'Properties returned', cell_fmt)
            ws.write(row, 1, data.get('properties_returned', 0), num_fmt)
            row += 2
            
            # Stock Under Collection
            stock = data.get('stock_under_collection', {}) or {}
            ws.write(row, 0, 'Total no. of stock under collection', header_fmt)
            row += 1
            ws.write_row(row, 0, ['Type', 'QTY'], header_fmt)
            row += 1
            ws.write(row, 0, 'Residences', cell_fmt)
            ws.write(row, 1, stock.get('residences', 0), num_fmt)
            row += 1
            ws.write(row, 0, 'Shops', cell_fmt)
            ws.write(row, 1, stock.get('shops', 0), num_fmt)
            row += 1
            ws.write(row, 0, 'Mixed use', cell_fmt)
            ws.write(row, 1, stock.get('mixed_use', 0), num_fmt)
            row += 1
            ws.write(row, 0, 'Total', cell_fmt)
            ws.write(row, 1, (stock.get('residences', 0) or 0) + (stock.get('shops', 0) or 0) + (stock.get('mixed_use', 0) or 0), num_fmt)
            row += 2
            
            # Collection Performance
            perf = data.get('collection_performance', {}) or {}
            collected_amount = perf.get('collected_amount', {}) or {}
            collected_clients = perf.get('collected_from_clients', {}) or {}
            ws.write(row, 0, 'Collection Performance & Discount', header_fmt)
            row += 1
            ws.write_row(row, 0, ['Performance', 'Plan', 'Actual', 'Achievement %'], header_fmt)
            row += 1
            ws.write(row, 0, 'Collected amount', cell_fmt)
            ws.write(row, 1, collected_amount.get('plan', 0.0), money_fmt)
            ws.write(row, 2, collected_amount.get('actual', 0.0), money_fmt)
            achievement = min(float(collected_amount.get('achievement', 0) or 0), 100.0)
            ws.write(row, 3, f"{achievement:.2f}%", num_fmt)
            row += 1
            ws.write(row, 0, 'Collected from no. of clients', cell_fmt)
            ws.write(row, 1, collected_clients.get('plan', 0), num_fmt)
            ws.write(row, 2, collected_clients.get('actual', 0), num_fmt)
            achievement_clients = min(float(collected_clients.get('achievement', 0) or 0), 100.0)
            ws.write(row, 3, f"{achievement_clients:.2f}%", num_fmt)
            row += 1
            discount = data.get('discount_given', {}) or {}
            ws.write(row, 0, 'Collection discount', cell_fmt)
            ws.write(row, 1, '—', cell_fmt)
            ws.write(row, 2, discount.get('amount', 0.0), money_fmt)
            ws.write(row, 3, f"{discount.get('percentage', 0.0):.2f}%", num_fmt)
            row += 2
            
            # Column widths
            ws.set_column(0, 0, 30)
            ws.set_column(1, 3, 18)
            
            # Charts images (from client) - place after tables in column H
            chart_start_row = row + 2
            chart_left_col = 7
            chart_row_height = 22
            cur_chart_row = chart_start_row
            
            img_keys = [
                ('stock_distribution_chart', 'Stock Under Collection Distribution'),
                ('collection_amount_chart', 'Plan vs Actual (Amount)'),
                ('collection_clients_chart', 'Plan vs Actual (Clients)'),
                ('activity_timeseries_chart', 'Activity Timeline'),
            ]
            
            charts_added = 0
            pair = []
            for k, title in img_keys:
                img_data = chart_images.get(k)
                if not img_data:
                    _logger.warning(f"Chart image not provided: {k}")
                    continue
                img_bytes = self._img_data_to_bytes(img_data)
                if not img_bytes:
                    _logger.warning(f"Chart image conversion failed: {k}")
                    continue
                pair.append((k, title, img_bytes))
                charts_added += 1
                if len(pair) == 2:
                    for idx, (kk, tt, bb) in enumerate(pair):
                        c = chart_left_col if idx == 0 else chart_left_col + 5
                        ws.merge_range(cur_chart_row, c, cur_chart_row, c + 3, tt, header_fmt)
                        try:
                            ws.insert_image(
                                cur_chart_row + 1, c, f'{kk}.png',
                                {
                                    'image_data': io.BytesIO(bb),
                                    'x_scale': 0.65,
                                    'y_scale': 0.65,
                                    'x_offset': 5,
                                    'y_offset': 5
                                }
                            )
                        except Exception as e:
                            _logger.error(f"Error inserting chart {kk}: {str(e)}")
                    cur_chart_row += chart_row_height
                    pair = []
            
            if pair:
                kk, tt, bb = pair[0]
                ws.merge_range(cur_chart_row, chart_left_col, cur_chart_row, chart_left_col + 3, tt, header_fmt)
                try:
                    ws.insert_image(
                        cur_chart_row + 1, chart_left_col, f'{kk}.png',
                        {
                            'image_data': io.BytesIO(bb),
                            'x_scale': 0.65,
                            'y_scale': 0.65,
                            'x_offset': 5,
                            'y_offset': 5
                        }
                    )
                except Exception as e:
                    _logger.error(f"Error inserting chart {kk}: {str(e)}")
            
            _logger.info(f"Collection Excel export: Added {charts_added} charts")
            
            ws.set_column(chart_left_col, chart_left_col + 3, 18)
            ws.set_column(chart_left_col + 5, chart_left_col + 8, 18)
            
            workbook.close()
            output.seek(0)
            
            # Return as base64 for JSON-RPC response
            import base64
            file_data = base64.b64encode(output.read()).decode('utf-8')
            return {
                'success': True,
                'file_data': file_data,
                'filename': f'Collection_Report_{date_from or "all"}_{date_to or "all"}.xlsx'
            }
        except Exception as e:
            _logger.error(f"Error exporting collection Excel: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    @http.route('/manager_reports/api/export_collection_pdf', type='json', auth='user', methods=['POST'], csrf=False)
    def api_export_collection_pdf(self, **kwargs):
        """Export Collection Report to PDF with charts."""
        try:
            # Extract parameters from JSON-RPC data
            date_from = kwargs.get('date_from') or None
            date_to = kwargs.get('date_to') or None
            chart_images = kwargs.get('chart_images', {}) or {}
            
            _logger.info(f"Collection PDF export - Received JSON data: date_from={date_from}, date_to={date_to}")
            _logger.info(f"Collection PDF export - Chart images keys: {list(chart_images.keys())}")
            for key, img_data in chart_images.items():
                if img_data and len(img_data) > 100:
                    _logger.info(f"Collection PDF export - Chart {key}: provided ({len(img_data)} bytes)")
                else:
                    _logger.warning(f"Collection PDF export - Chart {key}: missing or invalid (length: {len(img_data) if img_data else 0})")
            
            # Get data
            data = self._get_collection_export_data(date_from, date_to)
            
            # Extract values to avoid f-string dict issues
            stock = data.get('stock_under_collection', {}) or {}
            stock_res = stock.get('residences', 0) or 0
            stock_shops = stock.get('shops', 0) or 0
            stock_mixed = stock.get('mixed_use', 0) or 0
            stock_total = stock_res + stock_shops + stock_mixed
            
            perf = data.get('collection_performance', {}) or {}
            collected_amount = perf.get('collected_amount', {}) or {}
            collected_clients = perf.get('collected_from_clients', {}) or {}
            
            discount = data.get('discount_given', {}) or {}
            discount_amount = discount.get('amount', 0.0) or 0.0
            discount_percentage = discount.get('percentage', 0.0) or 0.0
            
            collected_amount_plan = float(collected_amount.get('plan', 0) or 0)
            collected_amount_actual = float(collected_amount.get('actual', 0) or 0)
            collected_amount_achievement = min(float(collected_amount.get('achievement', 0) or 0), 100.0)
            
            collected_clients_plan = int(collected_clients.get('plan', 0) or 0)
            collected_clients_actual = int(collected_clients.get('actual', 0) or 0)
            collected_clients_achievement = min(float(collected_clients.get('achievement', 0) or 0), 100.0)
            
            def img_tag(key):
                src = chart_images.get(key) or ''
                return f'<img src="{src}" style="max-width: 100%; height: auto; border: 1px solid #e5e7eb; border-radius: 8px;" />' if src else ''
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Collection Report</title>
                <style>
                    @media print {{
                        .no-print {{ display: none; }}
                    }}
                    @media screen {{
                        .print-button {{
                            position: fixed;
                            top: 10px;
                            right: 10px;
                            padding: 10px 20px;
                            background-color: #007bff;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            cursor: pointer;
                            font-size: 14px;
                            z-index: 1000;
                        }}
                        .print-button:hover {{
                            background-color: #0056b3;
                        }}
                    }}
                    body {{ font-family: Arial, sans-serif; margin: 20px; color: #111827; }}
                    h1 {{ margin: 0 0 6px 0; font-size: 18px; text-align: center; }}
                    .sub {{ margin: 0 0 14px 0; color: #374151; font-size: 12px; text-align: center; }}
                    .kpi {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
                    .kpi .card {{ border:1px solid #e5e7eb; border-radius: 8px; padding:10px 12px; min-width: 220px; }}
                    .kpi .label {{ font-size: 12px; color: #6b7280; font-weight: bold; }}
                    .kpi .val {{ font-size: 16px; font-weight: 700; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 10px 0 16px 0; }}
                    th, td {{ border: 1px solid #000; padding: 8px; font-size: 11px; }}
                    th {{ background: #D3D3D3; text-align: left; font-weight: bold; }}
                    .number {{ text-align: right; }}
                    .center {{ text-align: center; }}
                    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }}
                    .box {{ border:1px solid #e5e7eb; border-radius: 8px; padding: 10px; }}
                    .boxtitle {{ font-weight: 700; margin-bottom: 8px; }}
                </style>
                <script>
                    var printTriggered = false;
                    function triggerPrint() {{
                        if (!printTriggered) {{
                            window.print();
                            printTriggered = true;
                        }}
                    }}
                    window.addEventListener('DOMContentLoaded', function() {{
                        setTimeout(triggerPrint, 500);
                    }});
                    window.addEventListener('afterprint', function() {{
                        window.close();
                    }});
                </script>
            </head>
            <body>
                <button class="print-button no-print" onclick="window.print()">Print</button>
                <h1>Collection Report</h1>
                <div class="sub">Date From: {date_from if date_from else 'All'} | Date To: {date_to if date_to else 'All'}</div>

                <div class="kpi">
                    <div class="card"><div class="label">Total No. of clients</div><div class="val">{data.get('total_clients',0)}</div></div>
                    <div class="card"><div class="label">No. of sites</div><div class="val">{data.get('total_sites',0)}</div></div>
                    <div class="card"><div class="label">Total Receivable Amount</div><div class="val">{int(data.get('total_receivable',0) or 0):,}</div></div>
                    <div class="card"><div class="label">QTY</div><div class="val">{data.get('qty',0)}</div></div>
                    <div class="card"><div class="label">Properties returned</div><div class="val">{data.get('properties_returned',0)}</div></div>
                </div>

                <div class="grid">
                    <div class="box">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                            <div>
                                <div class="boxtitle">Total no. of stock under collection</div>
                                <table>
                                    <thead><tr><th>Type</th><th style="text-align:right">QTY</th></tr></thead>
                                    <tbody>
                                        <tr><td>Residences</td><td class="number">{stock_res}</td></tr>
                                        <tr><td>Shops</td><td class="number">{stock_shops}</td></tr>
                                        <tr><td>Mixed use</td><td class="number">{stock_mixed}</td></tr>
                                        <tr><td><strong>Total</strong></td><td class="number"><strong>{stock_total}</strong></td></tr>
                                    </tbody>
                                </table>
                            </div>
                            <div style="display: flex; align-items: center; justify-content: center;">
                                {img_tag('stock_distribution_chart')}
                            </div>
                        </div>
                    </div>
                </div>

                <div class="box">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <div class="boxtitle">Collection Performance &amp; Discount</div>
                            <table>
                                <thead>
                                    <tr>
                                        <th>Performance</th>
                                        <th style="text-align:right">Plan</th>
                                        <th style="text-align:right">Actual</th>
                                        <th style="text-align:right">Achievement %</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td>Collected amount</td>
                                        <td class="number">{int(collected_amount_plan):,}</td>
                                        <td class="number">{int(collected_amount_actual):,}</td>
                                        <td class="number">{collected_amount_achievement:.2f}%</td>
                                    </tr>
                                    <tr>
                                        <td>Collected from no. of clients</td>
                                        <td class="number">{collected_clients_plan}</td>
                                        <td class="number">{collected_clients_actual}</td>
                                        <td class="number">{collected_clients_achievement:.2f}%</td>
                                    </tr>
                                    <tr>
                                        <td>Collection discount</td>
                                        <td class="number">—</td>
                                        <td class="number">{int(discount_amount):,}</td>
                                        <td class="number">{discount_percentage:.2f}%</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 12px; align-items: center; justify-content: center;">
                            {img_tag('collection_amount_chart')}
                            {img_tag('collection_clients_chart')}
                        </div>
                    </div>
                </div>
                <div class="box">
                    <div class="boxtitle">Activity Timeline</div>
                    {img_tag('activity_timeseries_chart')}
                </div>
            </body>
            </html>
            """
            
            # Return HTML content for JSON-RPC response
            return {
                'success': True,
                'html_content': html
            }
        except Exception as e:
            _logger.error(f"Error exporting collection PDF: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    @http.route('/manager_reports/api/export_stock_collection_summary_excel', type='json', auth='user', methods=['POST'], csrf=False)
    def api_export_stock_collection_summary_excel(self, **kwargs):
        """Export Stock and Collection Summary Report to Excel with charts."""
        try:
            import xlsxwriter
            import base64
            
            # Extract parameters from JSON-RPC data
            date_from = kwargs.get('date_from') or None
            date_to = kwargs.get('date_to') or None
            wing_id = kwargs.get('wing_id') or None
            chart_images = kwargs.get('chart_images', {}) or {}
            
            _logger.info(f"Stock Collection Summary Excel export - Received JSON data: date_from={date_from}, date_to={date_to}, wing_id={wing_id}")
            _logger.info(f"Stock Collection Summary Excel export - Chart images keys: {list(chart_images.keys())}")
            for key, img_data in chart_images.items():
                if img_data and len(img_data) > 100:
                    _logger.info(f"Stock Collection Summary Excel export - Chart {key}: provided ({len(img_data)} bytes)")
                else:
                    _logger.warning(f"Stock Collection Summary Excel export - Chart {key}: missing or invalid (length: {len(img_data) if img_data else 0})")
            
            # Get data
            result = self.api_stock_collection_summary_data(date_from=date_from, date_to=date_to, wing_id=wing_id)
            if not result or not result.get('success'):
                raise Exception(result.get('error') if result else 'Unknown error generating report data')
            data = result.get('data', {})
            
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            ws = workbook.add_worksheet('Consolidate Report')
            
            title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
            sub_fmt = workbook.add_format({'bold': True, 'font_size': 10, 'align': 'center'})
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#E5E7EB', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
            cell_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})
            num_fmt = workbook.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter'})
            money_fmt = workbook.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter', 'num_format': '#,##0.00'})
            
            row = 0
            ws.merge_range(row, 0, row, 4, 'Consolidate Report', title_fmt)
            row += 1
            date_from_display = date_from if date_from else "All"
            date_to_display = date_to if date_to else "All"
            wing_display = wing_id if wing_id and wing_id != 'all' else "All"
            ws.merge_range(row, 0, row, 4, f'Date From: {date_from_display}   |   Date To: {date_to_display}   |   Wing: {wing_display}', sub_fmt)
            row += 2
            
            # Stock Available
            stock_avail = data.get('stock_available', {}) or {}
            ws.write(row, 0, 'Total Stock Available', header_fmt)
            row += 1
            ws.write_row(row, 0, ['Type', 'QTY', 'Values'], header_fmt)
            row += 1
            ws.write(row, 0, 'Residential', cell_fmt)
            ws.write(row, 1, stock_avail.get('residential', {}).get('qty', 0), num_fmt)
            ws.write(row, 2, stock_avail.get('residential', {}).get('values', 0.0), money_fmt)
            row += 1
            ws.write(row, 0, 'Commercial', cell_fmt)
            ws.write(row, 1, stock_avail.get('commercial', {}).get('qty', 0), num_fmt)
            ws.write(row, 2, stock_avail.get('commercial', {}).get('values', 0.0), money_fmt)
            row += 1
            ws.write(row, 0, 'Mixed use', cell_fmt)
            ws.write(row, 1, stock_avail.get('mixed_use', {}).get('qty', 0), num_fmt)
            ws.write(row, 2, stock_avail.get('mixed_use', {}).get('values', 0.0), money_fmt)
            row += 1
            ws.write(row, 0, 'Total', cell_fmt)
            ws.write(row, 1, stock_avail.get('total', {}).get('qty', 0), num_fmt)
            ws.write(row, 2, stock_avail.get('total', {}).get('values', 0.0), money_fmt)
            row += 2
            
            # Stock Sold
            stock_sold = data.get('stock_sold', {}) or {}
            ws.write(row, 0, 'Total Stock Sold', header_fmt)
            row += 1
            ws.write_row(row, 0, ['Type', 'QTY', 'Values', 'Achievement %'], header_fmt)
            row += 1
            ws.write(row, 0, 'Residential', cell_fmt)
            ws.write(row, 1, stock_sold.get('residential', {}).get('qty', 0), num_fmt)
            ws.write(row, 2, stock_sold.get('residential', {}).get('values', 0.0), money_fmt)
            ws.write(row, 3, f"{stock_sold.get('residential', {}).get('achievement_percent', 0.0):.2f}%", num_fmt)
            row += 1
            ws.write(row, 0, 'Commercial', cell_fmt)
            ws.write(row, 1, stock_sold.get('commercial', {}).get('qty', 0), num_fmt)
            ws.write(row, 2, stock_sold.get('commercial', {}).get('values', 0.0), money_fmt)
            ws.write(row, 3, f"{stock_sold.get('commercial', {}).get('achievement_percent', 0.0):.2f}%", num_fmt)
            row += 1
            ws.write(row, 0, 'Mixed use', cell_fmt)
            ws.write(row, 1, stock_sold.get('mixed_use', {}).get('qty', 0), num_fmt)
            ws.write(row, 2, stock_sold.get('mixed_use', {}).get('values', 0.0), money_fmt)
            ws.write(row, 3, f"{stock_sold.get('mixed_use', {}).get('achievement_percent', 0.0):.2f}%", num_fmt)
            row += 1
            ws.write(row, 0, 'Total', cell_fmt)
            ws.write(row, 1, stock_sold.get('total', {}).get('qty', 0), num_fmt)
            ws.write(row, 2, stock_sold.get('total', {}).get('values', 0.0), money_fmt)
            ws.write(row, 3, f"{stock_sold.get('total', {}).get('achievement_percent', 0.0):.2f}%", num_fmt)
            row += 2
            
            # Collection Metrics
            ws.write(row, 0, 'Collection Metrics', header_fmt)
            row += 1
            ws.write_row(row, 0, ['Metric', 'Value'], header_fmt)
            row += 1
            ws.write(row, 0, 'Total Collection to date', cell_fmt)
            ws.write(row, 1, data.get('total_collection', 0.0), money_fmt)
            row += 1
            ws.write(row, 0, 'Average collection per day', cell_fmt)
            ws.write(row, 1, data.get('average_collection_per_day', 0.0), money_fmt)
            row += 1
            ws.write(row, 0, 'Average collection per site', cell_fmt)
            ws.write(row, 1, data.get('average_collection_per_site', 0.0), money_fmt)
            row += 1
            ws.write(row, 0, 'Average achievement in %', cell_fmt)
            ws.write(row, 1, f"{data.get('average_achievement_percent', 0.0):.2f}%", num_fmt)
            row += 2
            
            # Column widths
            ws.set_column(0, 0, 30)
            ws.set_column(1, 3, 18)
            
            # Charts images
            chart_start_row = row + 2
            chart_left_col = 7
            chart_row_height = 22
            cur_chart_row = chart_start_row
            
            img_keys = [
                ('stock_available_chart', 'Stock Available Distribution'),
                ('stock_sold_chart', 'Stock Sold (QTY)'),
                ('stock_sold_timeline_chart', 'Stock Sold Over Time'),
            ]
            
            charts_added = 0
            pair = []
            for k, title in img_keys:
                img_data = chart_images.get(k)
                if not img_data:
                    continue
                img_bytes = self._img_data_to_bytes(img_data)
                if not img_bytes:
                    continue
                pair.append((k, title, img_bytes))
                charts_added += 1
                if len(pair) == 2:
                    for idx, (kk, tt, bb) in enumerate(pair):
                        c = chart_left_col if idx == 0 else chart_left_col + 5
                        ws.merge_range(cur_chart_row, c, cur_chart_row, c + 3, tt, header_fmt)
                        try:
                            ws.insert_image(
                                cur_chart_row + 1, c, f'{kk}.png',
                                {
                                    'image_data': io.BytesIO(bb),
                                    'x_scale': 0.65,
                                    'y_scale': 0.65,
                                    'x_offset': 5,
                                    'y_offset': 5
                                }
                            )
                        except Exception as e:
                            _logger.error(f"Error inserting chart {kk}: {str(e)}")
                    cur_chart_row += chart_row_height
                    pair = []
            
            if pair:
                kk, tt, bb = pair[0]
                ws.merge_range(cur_chart_row, chart_left_col, cur_chart_row, chart_left_col + 3, tt, header_fmt)
                try:
                    ws.insert_image(
                        cur_chart_row + 1, chart_left_col, f'{kk}.png',
                        {
                            'image_data': io.BytesIO(bb),
                            'x_scale': 0.65,
                            'y_scale': 0.65,
                            'x_offset': 5,
                            'y_offset': 5
                        }
                    )
                except Exception as e:
                    _logger.error(f"Error inserting chart {kk}: {str(e)}")
            
            _logger.info(f"Stock Collection Summary Excel export: Added {charts_added} charts")
            
            ws.set_column(chart_left_col, chart_left_col + 3, 18)
            ws.set_column(chart_left_col + 5, chart_left_col + 8, 18)
            
            workbook.close()
            output.seek(0)
            
            # Return as base64 for JSON-RPC response
            import base64
            file_data = base64.b64encode(output.read()).decode('utf-8')
            return {
                'success': True,
                'file_data': file_data,
                'filename': f'Consolidate_Report_{date_from or "all"}_{date_to or "all"}.xlsx'
            }
        except Exception as e:
            _logger.error(f"Error exporting stock collection summary Excel: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    @http.route('/manager_reports/api/export_stock_collection_summary_pdf', type='json', auth='user', methods=['POST'], csrf=False)
    def api_export_stock_collection_summary_pdf(self, **kwargs):
        """Export Stock and Collection Summary Report to PDF (HTML for print). Returns JSON with html_content for opening in new window."""
        try:
            # Parameters from JSON body (rpc call)
            date_from = kwargs.get('date_from') or None
            date_to = kwargs.get('date_to') or None
            wing_id = kwargs.get('wing_id') or None
            chart_images = kwargs.get('chart_images') or {}
            # Normalize chart_images: ensure we have dict and only include valid base64 strings
            if isinstance(chart_images, dict):
                chart_images = {k: v for k, v in chart_images.items()
                                if v and isinstance(v, str) and len(v) > 100}
            else:
                chart_images = {}
            for key in ['stock_available_chart', 'stock_sold_chart', 'stock_sold_timeline_chart']:
                if key not in chart_images:
                    _logger.warning(f"Stock Collection Summary PDF export - Chart {key}: missing or invalid")
            _logger.info(f"Stock Collection Summary PDF export - Received: date_from={date_from}, date_to={date_to}, wing_id={wing_id}")
            
            # Get data
            result = self.api_stock_collection_summary_data(date_from=date_from, date_to=date_to, wing_id=wing_id)
            if not result or not result.get('success'):
                raise Exception(result.get('error') if result else 'Unknown error generating report data')
            data = result.get('data', {})
            
            # Extract values
            stock_avail = data.get('stock_available', {}) or {}
            stock_sold = data.get('stock_sold', {}) or {}
            
            def img_tag(key):
                src = chart_images.get(key) or ''
                return f'<img src="{src}" style="max-width: 100%; height: auto; border: 1px solid #e5e7eb; border-radius: 8px;" />' if src else ''
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Consolidate Report</title>
                <style>
                    @media print {{ .no-print {{ display: none; }} }}
                    @media screen {{
                        .print-button {{
                            position: fixed; top: 10px; right: 10px; padding: 10px 20px;
                            background-color: #007bff; color: white; border: none;
                            border-radius: 4px; cursor: pointer; font-size: 14px; z-index: 1000;
                        }}
                        .print-button:hover {{ background-color: #0056b3; }}
                    }}
                    body {{ font-family: Arial, sans-serif; margin: 20px; color: #111827; }}
                    h1 {{ margin: 0 0 6px 0; font-size: 18px; text-align: center; }}
                    .sub {{ margin: 0 0 14px 0; color: #374151; font-size: 12px; text-align: center; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 10px 0 16px 0; }}
                    th, td {{ border: 1px solid #000; padding: 8px; font-size: 11px; }}
                    th {{ background: #D3D3D3; text-align: left; font-weight: bold; }}
                    .number {{ text-align: right; }}
                    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }}
                    .box {{ border:1px solid #e5e7eb; border-radius: 8px; padding: 10px; }}
                    .boxtitle {{ font-weight: 700; margin-bottom: 8px; }}
                    .summary {{ margin: 10px 0; }}
                    .summary-item {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e0e0e0; }}
                </style>
                <script>
                    var printTriggered = false;
                    function triggerPrint() {{
                        if (!printTriggered) {{
                            window.print();
                            printTriggered = true;
                        }}
                    }}
                    window.addEventListener('DOMContentLoaded', function() {{
                        setTimeout(triggerPrint, 500);
                    }});
                    window.addEventListener('afterprint', function() {{
                        window.close();
                    }});
                </script>
            </head>
            <body>
                <button class="print-button no-print" onclick="window.print()">Print</button>
                <h1>Consolidate Report</h1>
                <div class="sub">Date From: {date_from if date_from else 'All'} | Date To: {date_to if date_to else 'All'} | Wing: {wing_id if wing_id and wing_id != 'all' else 'All'}</div>

                <div class="grid">
                    <div class="box">
                        <div class="boxtitle">Total Stock Available</div>
                        <table>
                            <thead><tr><th>Type</th><th style="text-align:right">QTY</th><th style="text-align:right">Values</th></tr></thead>
                            <tbody>
                                <tr><td>Residential</td><td class="number">{stock_avail.get('residential', {}).get('qty', 0)}</td><td class="number">{int(stock_avail.get('residential', {}).get('values', 0) or 0):,}</td></tr>
                                <tr><td>Commercial</td><td class="number">{stock_avail.get('commercial', {}).get('qty', 0)}</td><td class="number">{int(stock_avail.get('commercial', {}).get('values', 0) or 0):,}</td></tr>
                                <tr><td>Mixed use</td><td class="number">{stock_avail.get('mixed_use', {}).get('qty', 0)}</td><td class="number">{int(stock_avail.get('mixed_use', {}).get('values', 0) or 0):,}</td></tr>
                                <tr><td><strong>Total</strong></td><td class="number"><strong>{stock_avail.get('total', {}).get('qty', 0)}</strong></td><td class="number"><strong>{int(stock_avail.get('total', {}).get('values', 0) or 0):,}</strong></td></tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="box">
                        <div style="display: flex; align-items: center; justify-content: center;">
                            {img_tag('stock_available_chart')}
                        </div>
                    </div>
                </div>

                <div class="grid">
                    <div class="box">
                        <div class="boxtitle">Total Stock Sold</div>
                        <table>
                            <thead><tr><th>Type</th><th style="text-align:right">QTY</th><th style="text-align:right">Values</th><th style="text-align:right">Achievement %</th></tr></thead>
                            <tbody>
                                <tr><td>Residential</td><td class="number">{stock_sold.get('residential', {}).get('qty', 0)}</td><td class="number">{int(stock_sold.get('residential', {}).get('values', 0) or 0):,}</td><td class="number">{stock_sold.get('residential', {}).get('achievement_percent', 0.0):.2f}%</td></tr>
                                <tr><td>Commercial</td><td class="number">{stock_sold.get('commercial', {}).get('qty', 0)}</td><td class="number">{int(stock_sold.get('commercial', {}).get('values', 0) or 0):,}</td><td class="number">{stock_sold.get('commercial', {}).get('achievement_percent', 0.0):.2f}%</td></tr>
                                <tr><td>Mixed use</td><td class="number">{stock_sold.get('mixed_use', {}).get('qty', 0)}</td><td class="number">{int(stock_sold.get('mixed_use', {}).get('values', 0) or 0):,}</td><td class="number">{stock_sold.get('mixed_use', {}).get('achievement_percent', 0.0):.2f}%</td></tr>
                                <tr><td><strong>Total</strong></td><td class="number"><strong>{stock_sold.get('total', {}).get('qty', 0)}</strong></td><td class="number"><strong>{int(stock_sold.get('total', {}).get('values', 0) or 0):,}</strong></td><td class="number"><strong>{stock_sold.get('total', {}).get('achievement_percent', 0.0):.2f}%</strong></td></tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="box">
                        <div style="display: flex; align-items: center; justify-content: center;">
                            {img_tag('stock_sold_chart')}
                        </div>
                    </div>
                </div>

                <div class="box">
                    <div class="boxtitle">Collection Metrics</div>
                    <div class="summary">
                        <div class="summary-item"><label>Total Collection to date:</label><span>{int(data.get('total_collection', 0) or 0):,}</span></div>
                        <div class="summary-item"><label>Average collection per day:</label><span>{int(data.get('average_collection_per_day', 0) or 0):,}</span></div>
                        <div class="summary-item"><label>Average collection per site:</label><span>{int(data.get('average_collection_per_site', 0) or 0):,}</span></div>
                        <div class="summary-item"><label>Average achievement in %:</label><span>{data.get('average_achievement_percent', 0.0):.2f}%</span></div>
                    </div>
                </div>

                <div class="grid">
                    <div class="box">
                        <div class="boxtitle">Stock Sold Over Time (units)</div>
                        {img_tag('stock_sold_timeline_chart')}
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Return HTML content for JSON-RPC response
            return {
                'success': True,
                'html_content': html
            }
        except Exception as e:
            _logger.error(f"Error exporting stock collection summary PDF: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

