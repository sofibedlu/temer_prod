from odoo import models, fields, api
from datetime import timedelta

class PropertyDashboard(models.Model):
    _name = 'property.dashboard'
    _description = 'Collection Dashboard'

    @api.model
    def get_dashboard_data(self):
        """ Gather data for the collection management dashboard:"""
        # KPI: Portfolio & Collected (from collection orders)
        all_collections = self.env['collection.order'].search([('state', 'in', ['active', 'fully_paid'])])
        total_portfolio = sum(all_collections.mapped('amount_total'))
        total_collected = sum(all_collections.mapped('amount_collected'))

        # KPI: Total Overdue (sum of residuals for overdue installments on active collections)
        installments = self.env['collection.installment']
        total_overdue = sum(installments.search([
            ('state', '=', 'overdue'),
            ('collection_id.state', '=', 'active')
        ]).mapped('amount_residual'))

        collection_rate = (total_collected / total_portfolio * 100) if total_portfolio else 0

        today = fields.Date.today()
        six_months_later = today + timedelta(days=180)

        # Chart: Cash Flow (monthly sum of amount_residual for active collections within window)
        self._cr.execute("""
            SELECT to_char(i.due_date, 'YYYY-MM') AS month, COALESCE(SUM(i.amount_residual),0) AS total
            FROM collection_installment i
            JOIN collection_order c ON i.collection_id = c.id
            WHERE i.due_date >= %s AND i.due_date <= %s
              AND c.state = 'active'
            GROUP BY 1
            ORDER BY 1
        """, (today, six_months_later))
        cash_flow_rows = self._cr.fetchall()  # list of (month, total)
        cash_flow_labels = [r[0] for r in cash_flow_rows]
        cash_flow_values = [r[1] for r in cash_flow_rows]

        # Chart: Overdue by Site
        overdue_site_labels = []
        overdue_site_values = []
        collection_model = self.env['collection.order']
        if 'project_id' in collection_model._fields:
            # collection.order has direct project_id -> use property_project
            self._cr.execute("""
                SELECT pp.name AS site_name, COALESCE(SUM(i.amount_residual),0) AS total
                FROM collection_installment i
                JOIN collection_order c ON i.collection_id = c.id
                JOIN property_project pp ON c.project_id = pp.id
                WHERE i.state = 'overdue'
                  AND c.state = 'active'
                GROUP BY pp.name
                ORDER BY total DESC
            """)
            rows = self._cr.fetchall()
            overdue_site_labels = [r[0] for r in rows]
            overdue_site_values = [r[1] for r in rows]
        else:
            # fallback: collection.order -> property_property -> property_site
            try:
                self._cr.execute("""
                    SELECT pp.name AS site_name, COALESCE(SUM(i.amount_residual),0) AS total
                    FROM collection_installment i
                    JOIN collection_order c ON i.collection_id = c.id
                    JOIN property_property u ON c.property_id = u.id
                    JOIN property_site pp ON u.site = pp.id
                    WHERE i.state = 'overdue'
                      AND c.state = 'active'
                    GROUP BY pp.name
                    ORDER BY total DESC
                """)
                rows = self._cr.fetchall()
                overdue_site_labels = [r[0] for r in rows]
                overdue_site_values = [r[1] for r in rows]
            except Exception:
                # Fallback: try property_site table naming (already correct)
                self._cr.execute("""
                    SELECT s.name AS site_name, COALESCE(SUM(i.amount_residual),0) AS total
                    FROM collection_installment i
                    JOIN collection_order c ON i.collection_id = c.id
                    JOIN property_property u ON c.property_id = u.id
                    JOIN property_site s ON u.site = s.id
                    WHERE i.state = 'overdue'
                      AND c.state = 'active'
                    GROUP BY s.name
                    ORDER BY total DESC
                """)
                rows = self._cr.fetchall()
                overdue_site_labels = [r[0] for r in rows]
                overdue_site_values = [r[1] for r in rows]

        # Ensure labels/values are lists (avoid None)
        overdue_site_labels = overdue_site_labels or []
        overdue_site_values = overdue_site_values or []

        # List: Top Overdue Installments (limit 10)
        top_overdue = installments.search_read(
            [('state', '=', 'overdue'), ('collection_id.state', '=', 'active')],
            ['name', 'due_date', 'amount_residual', 'collection_id'],
            order='amount_residual desc',
            limit=10
        )
        for item in top_overdue:
            item['contract_name'] = item['collection_id'][1] if item.get('collection_id') else 'N/A'
            # ensure id key for OWL rendering
            if 'id' not in item:
                item['id'] = item.get('collection_id')[0] if item.get('collection_id') else item.get('name')

        # List: Upcoming Installments (next 7 days) using amount_residual
        upcoming = installments.search_read(
            [
                ('state', '!=', 'paid'),
                ('due_date', '>=', today),
                ('due_date', '<=', today + timedelta(days=7)),
                ('collection_id.state', '=', 'active')
            ],
            ['name', 'due_date', 'amount_residual', 'collection_id'],
            order='due_date asc',
            limit=10
        )
        for item in upcoming:
            item['contract_name'] = item['collection_id'][1] if item.get('collection_id') else 'N/A'
            if 'id' not in item:
                item['id'] = item.get('collection_id')[0] if item.get('collection_id') else item.get('name')

        return {
            'kpi': {
                'portfolio': total_portfolio,
                'collected': total_collected,
                'overdue': total_overdue,
                'rate': round(collection_rate, 2),
            },
            'charts': {
                'cash_flow': {
                    'labels': cash_flow_labels,
                    'data': cash_flow_values
                },
                'overdue_site': {
                    'labels': overdue_site_labels,
                    'data': overdue_site_values
                }
            },
            'lists': {
                'top_overdue': top_overdue,
                'upcoming': upcoming
            }
        }