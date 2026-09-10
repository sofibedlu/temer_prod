# -*- coding: utf-8 -*-
# Requires ahadubit_property_base_custom (adds project_number to property.site) so @api.depends('site.project_number') works.
from odoo import api, fields, models, _
import re
import logging

_logger = logging.getLogger(__name__)


class PropertyProperty(models.Model):
    """Extend property model to compute reference based on site data"""

    _inherit = "property.property"

    # NEW FIELD: Unit number for each property
    unit_number = fields.Char(
        string='Unit Number',
        tracking=True,
        store=True,
        help="Unit/House number for this specific property"
    )

    commercial_location = fields.Selection(
        [
            ('inside', 'Inside'),
            ('outside', 'Outside'),
        ],
        string='Site Location',
        tracking=True,
        help="Select Inside (I) or Outside (O) for commercial units"
    )

    # Read-only computed field; project_number comes from property.site (ahadubit_property_base_custom)
    site_project_number = fields.Char(
        string='Project Number',
        compute='_compute_site_project_number',
        store=True,
        readonly=True
    )

    company_abbreviation = fields.Char(
        string='Company Abbreviation',
        compute='_compute_company_abbreviation',
        store=False,
        readonly=True
    )

    computed_reference = fields.Char(
        string='Reference Number',
        compute='_compute_property_reference',
        store=True,
        readonly=True,
        tracking=True,
        default=''
    )

    @api.depends('site', 'site.project_number')
    def _compute_site_project_number(self):
        """Get project number from site (project_number is on property.site from ahadubit_property_base_custom)."""
        for prop in self:
            if prop.site and prop.site.project_number:
                prop.site_project_number = str(prop.site.project_number).strip()
            else:
                prop.site_project_number = ''

    @api.depends('site')
    def _compute_company_abbreviation(self):
        """Get company abbreviation from site's company"""
        for prop in self:
            if prop.site and hasattr(prop.site, 'company_id') and prop.site.company_id:
                company = prop.site.company_id
                if hasattr(company, 'abbreviation') and company.abbreviation and company.abbreviation.strip():
                    prop.company_abbreviation = company.abbreviation.strip().upper()
                else:
                    prop.company_abbreviation = ''
            else:
                prop.company_abbreviation = ''

    @api.depends(
        'site.name',
        'site',
        'site.project_number',
        'block',
        'floor_ids',
        'property_type',
        'commercial_location',
        'unit_number',
    )
    def _compute_property_reference(self):
        """Generate property reference in format:
        SiteCode-OwnerCodeProjectNumber/BlockNumber/FloorNumber-UnitNumber[Suffix]
        """
        for prop in self:
            # Start with empty string
            ref = ''

            # Check minimum required fields
            if not prop.site or not prop.unit_number or not prop.unit_number.strip():
                prop.computed_reference = ''
                continue

            try:
                # 1. Site Code (first 3 letters of site name, remove spaces/special chars)
                site_name = prop.site.name or ''
                site_code = ''
                if site_name:
                    # Remove spaces and special characters, take first 3 letters
                    clean_name = re.sub(r'[^A-Za-z0-9]', '', site_name.strip())
                    if clean_name:
                        site_code = clean_name[:3].upper()

                if not site_code:  # If no site code, skip
                    prop.computed_reference = ''
                    continue

                # 2. Owner Code (from company abbreviation)
                owner_code = ''
                if prop.site and hasattr(prop.site, 'company_id') and prop.site.company_id:
                    company = prop.site.company_id
                    if hasattr(company, 'abbreviation') and company.abbreviation and company.abbreviation.strip():
                        # Remove spaces and special characters from abbreviation
                        owner_code = re.sub(r'[^A-Za-z0-9]', '', company.abbreviation.strip().upper())
                    elif hasattr(company, 'name') and company.name:
                        company_name = company.name.strip()
                        clean_company = re.sub(r'[^A-Za-z0-9]', '', company_name)
                        if clean_company:
                            owner_code = clean_company[:3].upper()

                # 3. Project Number (from site - ahadubit_property_base_custom)
                project_no = ''
                if prop.site.project_number:
                    project_str = str(prop.site.project_number).strip()
                    if project_str:
                        project_no = project_str

                # 4. Block Number - clean and format
                block_no = ''
                if prop.block:
                    if hasattr(prop.block, 'name') and prop.block.name:
                        block_str = str(prop.block.name).strip()
                        if block_str:
                            # Extract numbers from block name
                            numbers = re.findall(r'\d+', block_str)
                            if numbers:
                                block_no = numbers[0].zfill(2)
                            else:
                                # If no numbers, use first 2 characters
                                block_no = block_str[:2].upper()
                    else:
                        block_str = str(prop.block).strip()
                        if block_str:
                            numbers = re.findall(r'\d+', block_str)
                            if numbers:
                                block_no = numbers[0].zfill(2)
                            else:
                                block_no = block_str[:2].upper()

                # 5. Floor Number - from floor_ids (many2many)
                floor_no = ''
                if prop.floor_ids:
                    floor = prop.floor_ids[0]
                    if hasattr(floor, 'name') and floor.name:
                        floor_str = str(floor.name).strip().upper()
                        if floor_str:
                            # Extract numbers from floor name
                            numbers = re.findall(r'\d+', floor_str)
                            if numbers:
                                floor_no = f'F{numbers[0]}'
                            else:
                                # If no numbers, check for common floor names
                                if floor_str.startswith(('F', 'FL', 'FLR', 'FLOOR')):
                                    # Remove floor prefixes and take first character
                                    clean_floor = re.sub(r'^(F|FL|FLR|FLOOR)\s*', '', floor_str, flags=re.IGNORECASE)
                                    if clean_floor and clean_floor[0].isdigit():
                                        floor_no = f'F{clean_floor[0]}'
                                    else:
                                        floor_no = floor_str[:3]
                                else:
                                    floor_no = floor_str[:3]

                # 6. Unit Number - clean and format
                unit_no = ''
                if prop.unit_number and prop.unit_number.strip():
                    unit_str = prop.unit_number.strip()
                    # Extract numbers from unit number
                    numbers = re.findall(r'\d+', unit_str)
                    if numbers:
                        unit_no = numbers[0].zfill(2)
                    else:
                        # If no numbers, use the string as is
                        unit_no = unit_str.upper()[:3]

                # Build reference step by step
                ref_parts = []

                # SiteCode
                ref_parts.append(site_code)

                # -OwnerCodeProjectNumber
                if owner_code:
                    ref_parts.append(f'-{owner_code}')
                    if project_no:
                        ref_parts.append(project_no)

                # /BlockNumber/FloorNumber (only if we have at least one)
                if block_no or floor_no:
                    location_parts = []
                    if block_no:
                        location_parts.append(block_no)
                    if floor_no:
                        location_parts.append(floor_no)
                    if location_parts:
                        ref_parts.append(f"/{'/'.join(location_parts)}")

                # -UnitNumber[Suffix]
                if unit_no:
                    suffix = ''
                    if prop.property_type == 'commercial' and prop.commercial_location:
                        suffix = 'I' if prop.commercial_location == 'inside' else 'O'
                    ref_parts.append(f'-{unit_no}{suffix}')

                # Join all parts
                ref = ''.join(ref_parts)

                # Final validation: reference should have at least site code and unit number
                if ref and len(ref) > 5:  # Minimum reasonable length
                    prop.computed_reference = ref
                else:
                    prop.computed_reference = ''

            except Exception as e:
                _logger.error(f"Error computing reference for property {prop.id}: {e}")
                prop.computed_reference = ''

    @api.onchange('unit_number')
    def _onchange_unit_number(self):
        """Trigger reference computation when unit number changes"""
        if self.unit_number:
            self._compute_property_reference()

    @api.onchange('site', 'block', 'floor_ids', 'commercial_location')
    def _onchange_reference_fields(self):
        """Trigger reference computation when related fields change"""
        if self.unit_number:
            self._compute_property_reference()
