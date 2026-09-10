from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    title = fields.Selection([
        ('ato', 'Ato'),
        ('wro', 'Wro'),
        ('wz', 'Wz'),
    ], string="Title")

    coach_id = fields.Many2one('hr.employee', string='Immediate Manager')

    # Identification Fields
    tin_number = fields.Char(string="TIN Number", index=True)
    pension_number = fields.Char(string="Pension Number", index=True)
    fayda_fan_number = fields.Char(string="Fayda FAN Number", index=True)

    # Bank Account Details
    personal_cbe_account_number = fields.Char(string="Personal CBE Bank Account Number")
    cbe_branch = fields.Char(string="CBE Bank Account Branch")
    personal_awash_account_number = fields.Char(string="Personal Awash Bank Account Number")
    awash_branch = fields.Char(string="Awash Bank Account Branch")
    personal_abyssinia_account_number = fields.Char(string="Personal Abyssinia Bank Account Number")
    abyssinia_branch = fields.Char(string="Abyssinia Bank Account Branch")
    personal_dashen_account_number = fields.Char(string="Personal Dashen Bank Account Number")
    dashen_branch = fields.Char(string="Dashen Bank Account Branch")

    # Private Address Custom Fields
    subcity = fields.Char(string="SubCity")
    district = fields.Char(string="District")
    house_no = fields.Char(string="House No.")
    
    private_city = fields.Char(string="City", default="Addis Ababa")
    
    def _default_ethiopia(self):
        return self.env['res.country'].search([('name', '=', 'Ethiopia')], limit=1).id

    private_country_id = fields.Many2one('res.country', string="Country", default=_default_ethiopia)

    # Parent Information
    mother_name = fields.Char(string="Mother's Name")
    mother_birth_date = fields.Date(string="Mother's Birth Date")
    mother_place_of_birth = fields.Char(string="Mother's Place of Birth")
    father_name = fields.Char(string="Father's Name")
    father_birth_date = fields.Date(string="Father's Birth Date")
    father_place_of_birth = fields.Char(string="Father's Place of Birth")

    # Spouse's Detail
    spouse_name_custom = fields.Char(string="Wife / Husband Name")
    spouse_birth_date_custom = fields.Date(string="Spouse's Birth Date")
    spouse_place_of_birth = fields.Char(string="Spouse's Place of Birth")
    spouse_nationality = fields.Char(string="Spouse's Nationality")
    spouse_phone = fields.Char(string="Spouse's Phone Number")
    marriage_date = fields.Date(string="Marriage Date")

    # Children Information
    family_child_ids = fields.One2many(
        'employee.child',
        'employee_id',
        string="Children Information"
    )

    # Company Assets
    asset_ids = fields.One2many(
        'employee.asset',
        'employee_id',
        string="Company Assets"
    )

    assigned_company = fields.Selection([
        ('filtema', 'Filtema Trading'),
        ('temer', 'Temer Trading'),
    ], string="Company You are Assigned In")
