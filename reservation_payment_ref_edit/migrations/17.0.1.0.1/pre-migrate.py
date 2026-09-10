# -*- coding: utf-8 -*-
def migrate(cr, version):
    cr.execute("DELETE FROM ir_ui_view WHERE id IN (SELECT v.id FROM ir_ui_view v JOIN ir_model_data d ON d.model = 'ir.ui.view' AND d.res_id = v.id WHERE d.module = 'reservation_payment_ref_edit')")
    cr.execute("DELETE FROM ir_model_data WHERE module = 'reservation_payment_ref_edit' AND model = 'ir.ui.view'")
