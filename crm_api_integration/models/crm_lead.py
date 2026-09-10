from odoo import models, fields, _
import requests
import logging
import re
from requests.exceptions import RequestException

_logger = logging.getLogger(__name__)

class TemerLead(models.Model):
    _inherit = 'temer.lead'

    def write(self, vals):
        if 'state' in vals:
            old_states = {lead.id: lead.state for lead in self}
            result = super(TemerLead, self).write(vals)
            
            for lead in self:
                old_state = old_states.get(lead.id)
                new_state = vals.get('state')
                
                if old_state != new_state:
                    # Extract phone number
                    phone = self._extract_phone_from_lead(lead)
                    
                    if phone:
                        # Get country code
                        country_code = self._get_country_code_for_lead(lead)
                        
                        # Generate phone variants
                        phone_variants = self._generate_phone_variants_simple(phone, country_code)
                        
                        _logger.info(
                            "Temer Lead state changed - ID: %s, Phone: %s, Country: %s, Old State: %s, New State: %s",
                            lead.id, phone, country_code, old_state, new_state
                        )
                        
                        # Call API
                        self._call_external_api(lead, phone_variants, new_state)
                    else:
                        _logger.warning("Skipping API call for temer.lead %s: no phone found", lead.id)
            
            return result
        return super(TemerLead, self).write(vals)

    def _extract_phone_from_lead(self, lead):
        """Extract phone number from lead"""
        # Try phone_no field first
        if lead.phone_no:
            return lead.phone_no
            
        # Try phone_ids
        if lead.phone_ids:
            for phone_record in lead.phone_ids:
                if phone_record.phone:
                    return phone_record.phone
                    
        return None

    def _get_country_code_for_lead(self, lead):
        """Determine country code for phone processing"""
        try:
            if lead.country_id and lead.country_id.code:
                return lead.country_id.code.upper()
            
            company = self.env.company
            if company and company.country_id and company.country_id.code:
                return company.country_id.code.upper()
            
            return 'ET'  # Default to Ethiopia
            
        except Exception:
            return 'ET'

    def _generate_phone_variants_simple(self, phone, country_code='ET'):
        """Generate phone variants without external library"""
        if not phone:
            return []
            
        variants = set()
        phone_str = str(phone).strip()
        
        # Always include original
        variants.add(phone_str)
        
        # Extract digits only
        digits = ''.join(filter(str.isdigit, phone_str))
        if not digits:
            return list(variants)
            
        variants.add(digits)
        
        # Country-specific logic
        if country_code == 'ET':
            # Ethiopia logic
            if digits.startswith('251') and len(digits) > 3:
                local = '0' + digits[3:]
                variants.add(local)
                variants.add(digits[3:])  # without 251 or 0
            elif digits.startswith('0'):
                variants.add(digits)
                variants.add(digits[1:])  # without leading 0
                variants.add('251' + digits[1:])  # with 251
                variants.add('+251' + digits[1:])  # with +251
            elif len(digits) == 9 and digits.startswith('9'):
                variants.add('0' + digits)
                variants.add('251' + digits)
                variants.add('+251' + digits)
        else:
            # Generic international logic
            # Try to detect country code from common patterns
            if len(digits) >= 10:
                # Assume this is a full international number
                variants.add(digits)
                
                # Try with + if not already there
                if not phone_str.startswith('+'):
                    variants.add('+' + digits)
                    
                # Try with 00 prefix
                variants.add('00' + digits)
        
        # Clean and return
        return [v for v in variants if v and len(v) >= 5]

    def _call_external_api(self, lead, phone_variants, new_state):
        """Call external API with phone variants"""
        api_url = "http://165.232.70.106:2000/crm/status/phone"

        _logger.debug("Trying API with phone variants: %s", phone_variants)

        for candidate_phone in phone_variants:
            params = {
                'phone': candidate_phone,
                'status': new_state or '',
                'lead_id': lead.id,
            }
            
            try:
                resp = requests.patch(api_url, params=params, timeout=10)
                
                if 200 <= resp.status_code < 300:
                    _logger.info("API success for lead %s. Phone: %s", lead.id, candidate_phone)
                    return True
                    
                elif resp.status_code == 404:
                    _logger.debug("API 404 for phone %s, trying next", candidate_phone)
                    continue
                    
                else:
                    _logger.error("API error %s for phone %s", resp.status_code, candidate_phone)
                    continue
                    
            except RequestException as e:
                _logger.error("API call failed for phone %s: %s", candidate_phone, str(e))
                continue

        _logger.warning("All phone variants failed for lead %s", lead.id)
        return False