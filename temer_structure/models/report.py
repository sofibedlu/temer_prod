from odoo import fields, models
import logging

_logger = logging.getLogger(__name__)

class PropertySaleReportInherit(models.TransientModel):
    """A class for the transient model property.sale.report"""
    _inherit = 'property.sale.report'
    site_ids = fields.Many2many('property.site', string="Site")

    def action_create_report(self):
        """The function executes query related to the datas given
        and returns a pdf report"""
        query="""SELECT s.id AS site_id, s.name AS site_name,
                        SUM(x.total_discount) AS discount_sum,
                        SUM(x.total_paid) AS total_paid_sum,
                        SUM(x.remaining) AS remaining_sum,
                        SUM(x.sale_price) AS initial_price_sum,
                        JSON_AGG(
                            JSON_BUILD_OBJECT(
                                'customer', a.name,
                                'property', b.name,
                                'site', s.name,
                                'total_discount', x.total_discount,
                                'initial_price', x.sale_price,
                                'paid', x.total_paid,
                                'remaining', x.remaining,
                                'order_date', TO_CHAR(x.order_date, 'YYYY-MM-DD'),
                                'reservation_id', r.id
                            )
                        ) AS sales_details
                    FROM property_sale x
                    JOIN res_partner a ON x.partner_id = a.id
                    JOIN property_property b ON x.property_id = b.id
                    JOIN property_site s ON b.site = s.id
                    JOIN property_reservation r ON x.reservation_id = r.id
                    WHERE x.state = 'confirm'"""
        if self.partner_id:
            query += """ and a.name = '%s'""" % self.partner_id.name
        if self.property_id:
            query += """ and b.name = '%s'""" % self.property_id.name
        if self.from_date:
            query += """ and x.create_date > '%s'""" % self.from_date
        if self.to_date:
            query += """ and x.create_date < '%s'""" % self.to_date
        if self.site_ids:
            if len(self.site_ids)>1:
                site_ids = tuple(self.site_ids.ids)
                query += """ and s.id in %s""" % (site_ids,)
            else:
                query += """ and s.id = %s""" % self.site_ids.id
        query +=" GROUP BY s.id, s.name"
        self._cr.execute(query)
        datas = self.env.cr.dictfetchall()
        _logger.info("----------**************----------------------datas")
        _logger.info(datas)

        data = {
            'datas': datas,
            'to_date': self.to_date,
            'from_date': self.from_date,
            'partner_name': self.partner_id.name,
            'property_name': self.property_id.name,
            'site_ids': self.site_ids,
        }
        return self.env.ref(
            'ahadubit_property_base.property_sale_report_action_report_custom').report_action(
            self, data=data)
