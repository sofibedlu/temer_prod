from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    
    @api.model
    def check_duplicate_phones(self, phone_no=False, phone_ids=False, lead_id=False):
        """
        Check if phone numbers already exist in the database
        :param phone_no: phone number string to check
        :param phone_ids: list of phone record IDs to check
        :param lead_id: current lead id (for excluding during update)
        :return: dict with exists flag and lead info if exists
        """
        if not phone_no and not phone_ids:
            return {'exists': False}

        domain = []
        duplicate_type = None
        
        # Check phone_no field
        if phone_no:
            domain.append('|')
            domain.append(('phone_no', '=', phone_no))
            duplicate_type = 'phone_no'
        
        # Check phone_ids field
        if phone_ids:
            # Convert to list of integers if needed
            if isinstance(phone_ids, list) and phone_ids and isinstance(phone_ids[0], dict):
                phone_ids = [phone.get('id') for phone in phone_ids if phone.get('id')]
            
            phone_ids = [int(pid) for pid in phone_ids if pid]

            if phone_ids:
                if domain:  # If there's already conditions, use OR
                    domain.append('|')
                domain.append(('phone_ids', 'in', phone_ids))
                duplicate_type = 'phone_ids' if not duplicate_type else 'both'

        if not domain:
            return {'exists': False}

        if lead_id:
            domain.append(('id', '!=', lead_id))

        duplicate_leads = self.search(domain, limit=1)

        if duplicate_leads:
            result_data = {
                'exists': True,
                'duplicate_type': duplicate_type
            }

            # Add specific duplicate information
            if duplicate_type == 'phone_no':
                result_data['duplicate_phone'] = phone_no
            elif duplicate_type == 'phone_ids':
                # Get the common phone numbers
                common_phones = duplicate_leads.phone_ids.filtered(lambda p: p.id in phone_ids)
                phone_names = ", ".join(common_phones.mapped('name') or common_phones.mapped('number'))
                result_data['duplicate_phones'] = phone_names
                result_data['duplicate_count'] = len(common_phones)
            elif duplicate_type == 'both':
                # Get both types of duplicates
                result_data['duplicate_phone'] = phone_no
                common_phones = duplicate_leads.phone_ids.filtered(lambda p: p.id in phone_ids)
                phone_names = ", ".join(common_phones.mapped('name') or common_phones.mapped('number'))
                result_data['duplicate_phones'] = phone_names
                result_data['duplicate_count'] = len(common_phones)

            return result_data
        
        return {'exists': False}

    @api.constrains('phone_no', 'phone_ids')
    def _check_phone_uniqueness(self):
        """
        Constraint method to validate phone uniqueness on save
        """
        for lead in self:
            phone_ids = lead.phone_ids.ids if lead.phone_ids else False
            
            result = self.check_duplicate_phones(
                lead.phone_no, 
                phone_ids, 
                lead.id
            )
            
            if result['exists']:
                if result['duplicate_type'] == 'phone_no':
                    raise ValidationError(
                        _("Phone number %s is already registered.") %
                        result['duplicate_phone']
                    )
                elif result['duplicate_type'] == 'phone_ids':
                    if result['duplicate_count'] == 1:
                        raise ValidationError(
                            _("Phone number %s is already registered.") %
                            result['duplicate_phones']
                        )
                    else:
                        raise ValidationError(
                            _("Phone numbers %s are already registered.") %
                            result['duplicate_phones']
                        )
                elif result['duplicate_type'] == 'both':
                    raise ValidationError(
                        _("Phone number %s and phone numbers %s are already registered.") %
                        (result['duplicate_phone'], result['duplicate_phones'])
                    )

    def write(self, vals):
        """
        Override write to handle phone validation during updates
        """
        for lead in self:
            phone_no = vals.get('phone_no', lead.phone_no)
            phone_ids = vals.get('phone_ids')
            
            if phone_ids is None:
                phone_ids = lead.phone_ids.ids if lead.phone_ids else False
            elif isinstance(phone_ids, list):
                # Extract IDs from command list
                phone_ids = [cmd[1] for cmd in phone_ids if cmd[0] == 4]
            
            if 'phone_no' in vals or 'phone_ids' in vals:
                result = self.check_duplicate_phones(phone_no, phone_ids, lead.id)
                if result['exists']:
                    if result['duplicate_type'] == 'phone_no':
                        raise ValidationError(
                            _("Cannot update: Phone number %s is already registered.") %
                            result['duplicate_phone']
                        )
                    elif result['duplicate_type'] == 'phone_ids':
                        if result['duplicate_count'] == 1:
                            raise ValidationError(
                                _("Cannot update: Phone number %s is already registered.") %
                                result['duplicate_phones']
                            )
                        else:
                            raise ValidationError(
                                _("Cannot update: Phone numbers %s are already registered.") %
                                result['duplicate_phones']
                            )
                    elif result['duplicate_type'] == 'both':
                        raise ValidationError(
                            _("Cannot update: Phone number %s and phone numbers %s are already registered.") %
                            (result['duplicate_phone'], result['duplicate_phones'])
                        )
        
        return super(CrmLead, self).write(vals)