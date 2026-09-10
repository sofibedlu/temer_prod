# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo import fields
import logging
import subprocess
import sys
from datetime import datetime, timedelta
import urllib.request
import urllib.error
import json

_logger = logging.getLogger(__name__)


def _fetch_exchange_rate_from_api():
    """
    Fetch the latest ETB to USD exchange rate from external free APIs.
    Returns the rate (1 ETB = X USD) or None if all APIs fail.
    """
    # Free API endpoints (no API key required)
    apis = [
        {
            'url': 'https://api.exchangerate-api.com/v4/latest/ETB',
            'parser': lambda data: data.get('rates', {}).get('USD')
        },
        {
            'url': 'https://open.er-api.com/v6/latest/ETB',
            'parser': lambda data: data.get('rates', {}).get('USD')
        },
        {
            'url': 'https://api.fixer.io/latest?base=ETB&symbols=USD',
            'parser': lambda data: data.get('rates', {}).get('USD')
        }
    ]
    
    for api in apis:
        try:
            req = urllib.request.Request(api['url'])
            req.add_header('User-Agent', 'Mozilla/5.0')
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                rate = api['parser'](data)
                if rate and 0.001 <= rate <= 0.1:  # Validate rate is reasonable
                    _logger.info(f"Fetched exchange rate from external API: 1 ETB = {rate} USD")
                    return float(rate)
        except Exception as e:
            _logger.debug(f"Failed to fetch from {api['url']}: {str(e)}")
            continue
    
    _logger.warning("All external APIs failed, using default rate")
    return None


class SalesReportController(http.Controller):
    
    @http.route('/collection_reports/api/get_sites', type='json', auth='user', methods=['POST'], csrf=False)
    def api_get_sites(self, **kwargs):
        """API endpoint to get all sites that have properties or collections"""
        try:
            # Get all sites that have at least one property OR collection
            properties = request.env['property.property'].search([])
            collection_orders = request.env['collection.order'].search([])
            
            sites_with_data = set()
            
            # Get sites from properties
            for prop in properties:
                try:
                    # Try 'site' field first (correct field name)
                    if hasattr(prop, 'site') and prop.site:
                        sites_with_data.add(prop.site.id)
                    # Fallback: try 'site_id'
                    elif hasattr(prop, 'site_id') and prop.site_id:
                        sites_with_data.add(prop.site_id.id)
                except Exception as e:
                    _logger.warning(f"Error processing property {prop.id}: {e}")
                    continue
            
            # Get sites from collections (through property)
            for coll in collection_orders:
                try:
                    if coll.property_id:
                        # Try 'site' field first
                        if hasattr(coll.property_id, 'site') and coll.property_id.site:
                            sites_with_data.add(coll.property_id.site.id)
                        # Fallback: try 'site_id'
                        elif hasattr(coll.property_id, 'site_id') and coll.property_id.site_id:
                            sites_with_data.add(coll.property_id.site_id.id)
                except Exception as e:
                    _logger.warning(f"Error processing collection {coll.id}: {e}")
                    continue
            
            # If no sites found from properties/collections, get ALL sites from property.site
            if not sites_with_data:
                _logger.warning("No sites found from properties/collections, getting all sites from property.site")
                try:
                    all_sites = request.env['property.site'].search([])
                    for site in all_sites:
                        sites_with_data.add(site.id)
                    _logger.info(f"Found {len(sites_with_data)} sites from property.site")
                except Exception as e:
                    _logger.error(f"Error getting all sites: {e}")
            
            # Get site details
            sites_data = []
            for site_id in sites_with_data:
                try:
                    site = request.env['property.site'].browse(site_id)
                    if site.exists():
                        sites_data.append({
                            'id': site.id,
                            'name': site.name or f'Site {site.id}',
                        })
                except Exception as e:
                    _logger.warning(f"Error getting site {site_id}: {e}")
                    continue
            
            # Sort by name
            sites_data.sort(key=lambda x: x['name'])
            
            _logger.info(f"Get Sites API: Returning {len(sites_data)} sites: {[s['name'] for s in sites_data[:10]]}")
            
            return {
                'success': True,
                'sites': sites_data,
            }
        except Exception as e:
            _logger.error(f"Error in get_sites API: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'sites': [],
            }

    @http.route('/collection_reports/api/general_info', type='json', auth='user', methods=['POST'], csrf=False)
    def api_general_info(self, **kwargs):
        """
        API endpoint for General Information Report data.
        Returns summary format: S.NO, DESCRIPTION, AMOUNT IN NUMBER, REMARK
        Aggregated across all sites - 10 specific items
        """
        try:
            # Get filters from request - handle both JSON-RPC format and direct params
            # Odoo's type='json' automatically extracts JSON-RPC params into kwargs
            # So check kwargs directly first, then check nested params
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            
            # If not in kwargs directly, check nested params (for direct JSON requests)
            if date_from is None and 'params' in kwargs and isinstance(kwargs.get('params'), dict):
                params = kwargs.get('params', {})
                date_from = params.get('date_from')
                date_to = params.get('date_to')
            
            # Handle None/null values from JavaScript
            if date_from == 'null' or date_from is None:
                date_from = None
            if date_to == 'null' or date_to is None:
                date_to = None
            
            # Convert date strings to datetime objects
            date_from_obj = None
            date_to_obj = None
            if date_from and date_from != 'null' and date_from != '' and date_from is not None:
                try:
                    date_from_obj = fields.Date.from_string(date_from)
                except:
                    date_from_obj = None
            if date_to and date_to != 'null' and date_to != '' and date_to is not None:
                try:
                    date_to_obj = fields.Date.from_string(date_to)
                except:
                    date_to_obj = None
            
            # Get all properties
            properties = request.env['property.property'].search([])
            
            # Apply date filter to properties if provided
            if date_from_obj or date_to_obj:
                filtered_properties = []
                for prop in properties:
                    include = True
                    prop_date = None
                    if hasattr(prop, 'create_date') and prop.create_date:
                        prop_date = fields.Date.from_string(prop.create_date.strftime('%Y-%m-%d')) if hasattr(prop.create_date, 'strftime') else None
                    if prop.state == 'sold' and hasattr(prop, 'sale_ids') and prop.sale_ids:
                        sale = prop.sale_ids[0] if prop.sale_ids else None
                        if sale and hasattr(sale, 'create_date') and sale.create_date:
                            sale_date = fields.Date.from_string(sale.create_date.strftime('%Y-%m-%d')) if hasattr(sale.create_date, 'strftime') else None
                            if sale_date:
                                prop_date = sale_date
                    if prop_date:
                        if date_from_obj and prop_date < date_from_obj:
                            include = False
                        if date_to_obj and prop_date > date_to_obj:
                            include = False
                    if include:
                        filtered_properties.append(prop)
                properties = filtered_properties
            
            # 1. TOTAL STOCK - All properties
            total_stock = len(properties)
            
            # 2. SOLD STOCK - Properties with state='sold'
            sold_properties = [p for p in properties if hasattr(p, 'state') and getattr(p, 'state', None) == 'sold']
            sold_stock = len(sold_properties)
            
            # 3. ACTIVE IN COLLECTION MASTER DOCUMENT - All collection orders
            collection_orders = request.env['collection.order'].search([])
            if date_from_obj or date_to_obj:
                filtered_collections = []
                for coll in collection_orders:
                    include = True
                    if coll.create_date:
                        coll_date = fields.Date.from_string(coll.create_date.strftime('%Y-%m-%d')) if hasattr(coll.create_date, 'strftime') else None
                        if coll_date:
                            if date_from_obj and coll_date < date_from_obj:
                                include = False
                            if date_to_obj and coll_date > date_to_obj:
                                include = False
                    if include:
                        filtered_collections.append(coll)
                collection_orders = filtered_collections
            active_master_document = len(collection_orders)
            
            # 4. MERGE CONTRACT - Count of merged contracts (if model exists)
            merge_contract = 0
            if 'property.contract' in request.env:
                contracts = request.env['property.contract'].search([])
                if date_from_obj or date_to_obj:
                    filtered_contracts = []
                    for contract in contracts:
                        include = True
                        if contract.create_date:
                            contract_date = fields.Date.from_string(contract.create_date.strftime('%Y-%m-%d')) if hasattr(contract.create_date, 'strftime') else None
                            if contract_date:
                                if date_from_obj and contract_date < date_from_obj:
                                    include = False
                                if date_to_obj and contract_date > date_to_obj:
                                    include = False
                        if include:
                            filtered_contracts.append(contract)
                    contracts = filtered_contracts
                # Check for merged contracts (adjust based on your model)
                merge_contract = len([c for c in contracts if hasattr(c, 'is_merged') and getattr(c, 'is_merged', False)])
            
            # 5. SITE SHIFT - Count of site shifts (if model exists)
            site_shift = 0
            # This would need to be implemented based on your site shift model
            
            # 6. FULLY PAID ALL THE CONTRACTED AMOUNT (100% PAID)
            fully_paid = len([c for c in collection_orders if hasattr(c, 'amount_remaining') and getattr(c, 'amount_remaining', 999) <= 0])
            
            # 7. NUMBER OF CUSTOMERS WHO HAVE DHL CASE
            dhl_customers = set()
            installments = request.env['collection.installment'].search([])
            if date_from_obj or date_to_obj:
                filtered_installments = []
                for inst in installments:
                    include = True
                    if inst.create_date:
                        inst_date = fields.Date.from_string(inst.create_date.strftime('%Y-%m-%d')) if hasattr(inst.create_date, 'strftime') else None
                        if inst_date:
                            if date_from_obj and inst_date < date_from_obj:
                                include = False
                            if date_to_obj and inst_date > date_to_obj:
                                include = False
                    if include:
                        filtered_installments.append(inst)
                installments = filtered_installments
            
            for inst in installments:
                if inst.collection_id:
                    coll = inst.collection_id
                    if hasattr(coll, 'installment_ids') and coll.installment_ids:
                        for inst_line in coll.installment_ids:
                            if hasattr(inst_line, 'payment_ids') and inst_line.payment_ids:
                                for payment in inst_line.payment_ids:
                                    if hasattr(payment, 'fs_number') and payment.fs_number:
                                        if date_from_obj or date_to_obj:
                                            payment_date = None
                                            if hasattr(payment, 'create_date') and payment.create_date:
                                                payment_date = fields.Date.from_string(payment.create_date.strftime('%Y-%m-%d')) if hasattr(payment.create_date, 'strftime') else None
                                            if payment_date:
                                                if date_from_obj and payment_date < date_from_obj:
                                                    continue
                                                if date_to_obj and payment_date > date_to_obj:
                                                    continue
                                        if coll.partner_id:
                                            dhl_customers.add(coll.partner_id.id)
            dhl_customer_count = len(dhl_customers)
            
            # 8. ARRIVED PAYMENT ROUND NUMBER
            payment_rounds = set()
            for inst in installments:
                if inst.collection_id:
                    coll = inst.collection_id
                    if hasattr(coll, 'installment_ids') and coll.installment_ids:
                        for inst_line in coll.installment_ids:
                            if hasattr(inst_line, 'payment_ids') and inst_line.payment_ids:
                                for payment in inst_line.payment_ids:
                                    if hasattr(payment, 'round_number') and payment.round_number:
                                        if date_from_obj or date_to_obj:
                                            payment_date = None
                                            if hasattr(payment, 'create_date') and payment.create_date:
                                                payment_date = fields.Date.from_string(payment.create_date.strftime('%Y-%m-%d')) if hasattr(payment.create_date, 'strftime') else None
                                            if payment_date:
                                                if date_from_obj and payment_date < date_from_obj:
                                                    continue
                                                if date_to_obj and payment_date > date_to_obj:
                                                    continue
                                        payment_rounds.add(payment.round_number)
            payment_round_number = len(payment_rounds)
            
            # 9. NUMBER OF CUSTOMERS ON REFUND OR ON REFUND PROCESS
            refund_count = 0
            if 'account.move' in request.env:
                property_sales = request.env['property.sale'].search([])
                if date_from_obj or date_to_obj:
                    filtered_sales = []
                    for sale in property_sales:
                        include = True
                        if sale.create_date:
                            sale_date = fields.Date.from_string(sale.create_date.strftime('%Y-%m-%d')) if hasattr(sale.create_date, 'strftime') else None
                            if sale_date:
                                if date_from_obj and sale_date < date_from_obj:
                                    include = False
                                if date_to_obj and sale_date > date_to_obj:
                                    include = False
                        if include:
                            filtered_sales.append(sale)
                    property_sales = filtered_sales
                
                refund_customers = set()
                for sale in property_sales:
                    if sale.property_id and sale.property_id.state == 'sold':
                        partner_id = sale.partner_id.id if sale.partner_id else False
                        if partner_id:
                            refund_moves = request.env['account.move'].search([
                                ('partner_id', '=', partner_id),
                                ('move_type', '=', 'out_refund'),
                                ('state', '!=', 'cancel'),
                            ])
                            if date_from_obj:
                                refund_moves = refund_moves.filtered(lambda m: not m.date or m.date >= date_from_obj)
                            if date_to_obj:
                                refund_moves = refund_moves.filtered(lambda m: not m.date or m.date <= date_to_obj)
                            if refund_moves:
                                refund_customers.add(partner_id)
                refund_count = len(refund_customers)
            
            # 10. NUMBER OF INCOMPLETE CONTRACT
            incomplete_contract = 0
            active_collections = [c for c in collection_orders if hasattr(c, 'state') and getattr(c, 'state', None) == 'active']
            incomplete_contract = len([c for c in active_collections if hasattr(c, 'amount_remaining') and getattr(c, 'amount_remaining', 999) > 0])
            
            # Build report data in the exact format from the image
            report_data = [
                {
                    'sno': 1,
                    'description': 'TOTAL STOCK',
                    'amount_in_number': total_stock,
                    'remark': ''
                },
                {
                    'sno': 2,
                    'description': 'SOLD STOCK',
                    'amount_in_number': sold_stock,
                    'remark': ''
                },
                {
                    'sno': 3,
                    'description': 'ACTIVE IN COLLECTION MASTER DOCUMENT',
                    'amount_in_number': active_master_document,
                    'remark': ''
                },
                {
                    'sno': 4,
                    'description': 'MERGE CONTRACT',
                    'amount_in_number': merge_contract,
                    'remark': ''
                },
                {
                    'sno': 5,
                    'description': 'SITE SHIFT',
                    'amount_in_number': site_shift,
                    'remark': ''
                },
                {
                    'sno': 6,
                    'description': 'FULLY PAID ALL THE CONTRACTED AMOUNT (100% PAID)',
                    'amount_in_number': fully_paid,
                    'remark': ''
                },
                {
                    'sno': 7,
                    'description': 'NUMBER OF CUSTOMERS WHO HAVE DHL CASE',
                    'amount_in_number': dhl_customer_count,
                    'remark': ''
                },
                {
                    'sno': 8,
                    'description': 'ARRIVED PAYMENT ROUND NUMBER',
                    'amount_in_number': payment_round_number,
                    'remark': ''
                },
                {
                    'sno': 9,
                    'description': 'NUMBER OF CUSTOMERS ON REFUND OR ON REFUND PROCESS',
                    'amount_in_number': refund_count,
                    'remark': ''
                },
                {
                    'sno': 10,
                    'description': 'NUMBER OF INCOMPLETE CONTRACT',
                    'amount_in_number': incomplete_contract,
                    'remark': ''
                },
            ]
            
            # Calculate totals
            total_amount = sum(d['amount_in_number'] for d in report_data)
            
            return {
                'success': True,
                'data': report_data,
                'totals': {
                    'total_amount_in_number': total_amount
                }
            }
            
        except Exception as e:
            _logger.error(f"Error in general_info API: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'totals': {}
            }

    @http.route('/collection_reports/api/general_info_detailed', type='json', auth='user', methods=['POST'], csrf=False)
    def api_general_info_detailed(self, **kwargs):
        """
        API endpoint for General Information Report (Old Format - Detailed by Site/Project).
        Returns data by site/project with columns: PROJECT NAME, TOTAL STOCK, SOLD STOCK, etc.
        """
        try:
            # Get filters from request - handle both JSON-RPC format and direct params
            params = {}
            if 'params' in kwargs and isinstance(kwargs.get('params'), dict):
                params = kwargs.get('params', {})
            elif isinstance(kwargs, dict):
                params = kwargs
            
            date_from = params.get('date_from') or kwargs.get('date_from')
            date_to = params.get('date_to') or kwargs.get('date_to')
            
            # Handle None values from JavaScript
            if date_from == 'null' or date_from is None:
                date_from = None
            if date_to == 'null' or date_to is None:
                date_to = None
            
            date_from_obj = None
            date_to_obj = None
            if date_from and date_from != 'null' and date_from != '' and date_from is not None:
                try:
                    date_from_obj = fields.Date.from_string(date_from)
                except:
                    date_from_obj = None
            if date_to and date_to != 'null' and date_to != '' and date_to is not None:
                try:
                    date_to_obj = fields.Date.from_string(date_to)
                except:
                    date_to_obj = None
            
            # Get all sites
            properties = request.env['property.property'].search([])
            site_dict = {}
            
            for prop in properties:
                try:
                    site_id = None
                    site_name = None
                    if hasattr(prop, 'site') and prop.site:
                        site_id = prop.site.id
                        site_name = prop.site.name
                    elif hasattr(prop, 'site_id') and prop.site_id:
                        site_id = prop.site_id.id
                        site_name = prop.site_id.name
                    
                    if site_id and site_name:
                        if site_id not in site_dict:
                            site_dict[site_id] = {
                                'name': site_name,
                                'properties': [],
                                'collections': []
                            }
                        site_dict[site_id]['properties'].append(prop)
                except:
                    continue
            
            # Get collections
            collection_orders = request.env['collection.order'].search([])
            for coll in collection_orders:
                try:
                    if coll.property_id:
                        site_id = None
                        if hasattr(coll.property_id, 'site') and coll.property_id.site:
                            site_id = coll.property_id.site.id
                        elif hasattr(coll.property_id, 'site_id') and coll.property_id.site_id:
                            site_id = coll.property_id.site_id.id
                        
                        if site_id and site_id in site_dict:
                            site_dict[site_id]['collections'].append(coll)
                except:
                    continue
            
            report_data = []
            
            for site_id, site_data in site_dict.items():
                site_name = site_data['name']
                site_properties = site_data['properties']
                site_collections = site_data['collections']
                
                # Apply date filters
                if date_from_obj or date_to_obj:
                    filtered_properties = []
                    for prop in site_properties:
                        include = True
                        prop_date = None
                        if hasattr(prop, 'create_date') and prop.create_date:
                            prop_date = fields.Date.from_string(prop.create_date.strftime('%Y-%m-%d')) if hasattr(prop.create_date, 'strftime') else None
                        if prop.state == 'sold' and hasattr(prop, 'sale_ids') and prop.sale_ids:
                            sale = prop.sale_ids[0] if prop.sale_ids else None
                            if sale and hasattr(sale, 'create_date') and sale.create_date:
                                sale_date = fields.Date.from_string(sale.create_date.strftime('%Y-%m-%d')) if hasattr(sale.create_date, 'strftime') else None
                                if sale_date:
                                    prop_date = sale_date
                        if prop_date:
                            if date_from_obj and prop_date < date_from_obj:
                                include = False
                            if date_to_obj and prop_date > date_to_obj:
                                include = False
                        if include:
                            filtered_properties.append(prop)
                    site_properties = filtered_properties
                    
                    filtered_collections = []
                    for coll in site_collections:
                        include = True
                        if coll.create_date:
                            coll_date = fields.Date.from_string(coll.create_date.strftime('%Y-%m-%d')) if hasattr(coll.create_date, 'strftime') else None
                            if coll_date:
                                if date_from_obj and coll_date < date_from_obj:
                                    include = False
                                if date_to_obj and coll_date > date_to_obj:
                                    include = False
                        if include:
                            filtered_collections.append(coll)
                    site_collections = filtered_collections
                
                # Calculate metrics for this site
                total_stock = len(site_properties)
                sold_stock = len([p for p in site_properties if hasattr(p, 'state') and getattr(p, 'state', None) == 'sold'])
                active_master_document = len(site_collections)
                active_in_collection = len([c for c in site_collections if hasattr(c, 'state') and getattr(c, 'state', None) == 'active'])
                
                # Merge contract
                merge_contract = 0
                try:
                    if 'property.contract' in request.env:
                        property_ids = [p.id for p in site_properties]
                        if property_ids:
                            contracts = request.env['property.contract'].search([
                                ('property_id', 'in', property_ids)
                            ])
                            merge_contract = len([c for c in contracts if hasattr(c, 'is_merged') and getattr(c, 'is_merged', False)])
                except Exception as e:
                    _logger.warning(f"Error calculating merge_contract for site {site_name}: {str(e)}")
                    merge_contract = 0
                
                site_shift = 0  # Placeholder
                
                # Fully paid
                fully_paid = len([c for c in site_collections if hasattr(c, 'amount_remaining') and getattr(c, 'amount_remaining', 999) <= 0])
                
                # DHL customers
                dhl_customers = set()
                try:
                    collection_ids = [c.id for c in site_collections]
                    if collection_ids:
                        installments = request.env['collection.installment'].search([
                            ('collection_id', 'in', collection_ids)
                        ])
                        for inst in installments:
                            try:
                                if inst.collection_id:
                                    if hasattr(inst, 'payment_ids') and inst.payment_ids:
                                        for payment in inst.payment_ids:
                                            try:
                                                if hasattr(payment, 'fs_number') and payment.fs_number:
                                                    if inst.collection_id.partner_id:
                                                        dhl_customers.add(inst.collection_id.partner_id.id)
                                            except:
                                                continue
                            except:
                                continue
                except Exception as e:
                    _logger.warning(f"Error calculating DHL customers for site {site_name}: {str(e)}")
                dhl_number = len(dhl_customers)
                
                # Payment round number
                payment_rounds = set()
                try:
                    collection_ids = [c.id for c in site_collections]
                    if collection_ids:
                        installments = request.env['collection.installment'].search([
                            ('collection_id', 'in', collection_ids)
                        ])
                        for inst in installments:
                            try:
                                if inst.collection_id:
                                    if hasattr(inst, 'payment_ids') and inst.payment_ids:
                                        for payment in inst.payment_ids:
                                            try:
                                                if hasattr(payment, 'round_number') and payment.round_number:
                                                    payment_rounds.add(payment.round_number)
                                            except:
                                                continue
                            except:
                                continue
                except Exception as e:
                    _logger.warning(f"Error calculating payment rounds for site {site_name}: {str(e)}")
                payment_round_number = len(payment_rounds)
                
                # Refund
                refund_count = 0
                try:
                    if 'account.move' in request.env:
                        sold_property_ids = [p.id for p in site_properties if hasattr(p, 'state') and getattr(p, 'state', None) == 'sold']
                        if sold_property_ids:
                            property_sales = request.env['property.sale'].search([
                                ('property_id', 'in', sold_property_ids)
                            ])
                            refund_customers = set()
                            for sale in property_sales:
                                try:
                                    if sale.partner_id:
                                        refund_moves = request.env['account.move'].search([
                                            ('partner_id', '=', sale.partner_id.id),
                                            ('move_type', '=', 'out_refund'),
                                            ('state', '!=', 'cancel'),
                                        ], limit=1)  # Limit to 1 for performance
                                        if refund_moves:
                                            refund_customers.add(sale.partner_id.id)
                                except:
                                    continue
                            refund_count = len(refund_customers)
                except Exception as e:
                    _logger.warning(f"Error calculating refund count for site {site_name}: {str(e)}")
                    refund_count = 0
                
                # Incomplete contract
                incomplete_contract = len([c for c in site_collections if hasattr(c, 'state') and getattr(c, 'state', None) == 'active' and hasattr(c, 'amount_remaining') and getattr(c, 'amount_remaining', 999) > 0])
                
                # Income contract (placeholder)
                income_contract = 0
                
                report_data.append({
                    'sno': len(report_data) + 1,
                    'project_name': site_name,
                    'total_stock': total_stock,
                    'sold_stock': sold_stock,
                    'active_in_master_document': active_master_document,
                    'active_in_collection': active_in_collection,
                    'merged_contract': merge_contract,
                    'site_shift': site_shift,
                    'fully_paid': fully_paid,
                    'dhl_number': dhl_number,
                    'payment_round_number': payment_round_number,
                    'refund': refund_count,
                    'contract_not_complete': incomplete_contract,
                    'income_contract': income_contract,
                })
            
            return {
                'success': True,
                'data': report_data,
                'totals': {}
            }
            
        except Exception as e:
            _logger.error(f"Error in general_info_detailed API: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'totals': {}
            }

    @http.route('/collection_reports/api/plan_stage_report', type='json', auth='user', methods=['POST'], csrf=False)
    def api_plan_stage_report(self, **kwargs):
        """
        API endpoint for Plan Based on Collection Stage Report
        This shows PLAN data (what was planned/expected to collect)
        Uses amount_total (planned amounts), not amount_collected (actual execution)
        Returns data grouped by site with:
        - EXPECTED: Planned amounts (amount_total) from active/draft collections
        - PLAN - PENALITY: Planned penalty amounts
        - PLAN - TERMINATION: Planned amounts from terminated collections
        - TOTAL COLLECTION PLAN: Total planned amounts
        """
        try:
            # Get filters from request - handle both JSON-RPC format and direct params
            params = {}
            if 'params' in kwargs and isinstance(kwargs.get('params'), dict):
                params = kwargs.get('params', {})
            elif isinstance(kwargs, dict):
                params = kwargs
            
            site_id = params.get('site_id') or kwargs.get('site_id')
            date_from = params.get('date_from') or kwargs.get('date_from')
            date_to = params.get('date_to') or kwargs.get('date_to')
            
            # Handle None values from JavaScript
            if date_from == 'null' or date_from is None:
                date_from = None
            if date_to == 'null' or date_to is None:
                date_to = None
            
            # Convert site_id to integer if provided
            site_id_int = None
            if site_id and site_id != '' and site_id != 'null':
                try:
                    site_id_int = int(site_id)
                except:
                    site_id_int = None
            
            # Convert date strings to datetime objects
            date_from_obj = None
            date_to_obj = None
            if date_from and date_from != 'null' and date_from != '':
                try:
                    date_from_obj = fields.Date.from_string(date_from)
                except:
                    date_from_obj = None
            if date_to and date_to != 'null' and date_to != '':
                try:
                    date_to_obj = fields.Date.from_string(date_to)
                except:
                    date_to_obj = None
            
            # Get exchange rate
            exchange_rate = _fetch_exchange_rate_from_api()
            if not exchange_rate or exchange_rate <= 0 or exchange_rate > 0.1:
                exchange_rate = 0.0064  # Default fallback
            _logger.info(f"Plan Stage Report: Using exchange rate {exchange_rate} (1 ETB = {exchange_rate} USD)")
            
            # Get all sites
            properties = request.env['property.property'].search([])
            site_dict = {}
            
            for prop in properties:
                try:
                    if hasattr(prop, 'site') and prop.site:
                        site_id = prop.site.id
                        site_name = prop.site.name
                        if site_id not in site_dict:
                            site_dict[site_id] = {
                                'name': site_name,
                                'properties': set(),
                                'collections': set()
                            }
                        site_dict[site_id]['properties'].add(prop.id)
                    elif hasattr(prop, 'site_id') and prop.site_id:
                        site_id = prop.site_id.id
                        site_name = prop.site_id.name
                        if site_id not in site_dict:
                            site_dict[site_id] = {
                                'name': site_name,
                                'properties': set(),
                                'collections': set()
                            }
                        site_dict[site_id]['properties'].add(prop.id)
                except:
                    continue
            
            # Get collections
            collection_orders = request.env['collection.order'].search([])
            for coll in collection_orders:
                try:
                    if coll.property_id:
                        if hasattr(coll.property_id, 'site') and coll.property_id.site:
                            site_id = coll.property_id.site.id
                            if site_id in site_dict:
                                site_dict[site_id]['collections'].add(coll.id)
                        elif hasattr(coll.property_id, 'site_id') and coll.property_id.site_id:
                            site_id = coll.property_id.site_id.id
                            if site_id in site_dict:
                                site_dict[site_id]['collections'].add(coll.id)
                except:
                    continue
            
            # Get all active plans, filtered by date range if provided
            plan_domain = [('active', '=', True)]
            if site_id_int is not None:
                plan_domain.append(('site_id', '=', site_id_int))
            
            # Filter by date range if provided
            if date_from_obj or date_to_obj:
                # Find plans where the plan's date range overlaps with the requested date range
                # Plan is valid if: plan.date_from <= date_to AND plan.date_to >= date_from
                if date_from_obj:
                    plan_domain.append(('date_to', '>=', date_from_obj))
                if date_to_obj:
                    plan_domain.append(('date_from', '<=', date_to_obj))
            
            collection_plans = request.env['collection.plan.stage'].search(plan_domain)
            plans_by_site = {plan.site_id.id: plan for plan in collection_plans}
            
            _logger.info(f"Plan Stage Report: Found {len(collection_plans)} active plans")
            
            report_data = []
            
            for site_id, site_data in site_dict.items():
                # Filter by site_id if provided
                if site_id_int is not None and site_id != site_id_int:
                    continue
                
                site_name = site_data['name']
                site_collection_ids = list(site_data['collections'])
                site_collections = request.env['collection.order'].browse(site_collection_ids)
                
                # Filter collections by date if provided
                if date_from_obj or date_to_obj:
                    filtered_collections = []
                    for coll in site_collections:
                        include = True
                        if date_from_obj and coll.create_date:
                            coll_date = fields.Date.from_string(coll.create_date.strftime('%Y-%m-%d')) if hasattr(coll.create_date, 'strftime') else None
                            if coll_date and coll_date < date_from_obj:
                                include = False
                        if date_to_obj and coll.create_date:
                            coll_date = fields.Date.from_string(coll.create_date.strftime('%Y-%m-%d')) if hasattr(coll.create_date, 'strftime') else None
                            if coll_date and coll_date > date_to_obj:
                                include = False
                        if include:
                            filtered_collections.append(coll)
                    site_collections = filtered_collections
                
                # Calculate EXPECTED from sold leads in date range
                # Get properties for this site
                site_property_ids = list(site_data.get('properties', []))
                property_sales = request.env['property.sale'].search([
                    ('property_id', 'in', site_property_ids),
                    ('property_id.state', '=', 'sold')
                ])
                
                # Filter by date if provided
                if date_from_obj or date_to_obj:
                    filtered_sales = []
                    for sale in property_sales:
                        include = True
                        if date_from_obj and sale.create_date:
                            sale_date = fields.Date.from_string(sale.create_date.strftime('%Y-%m-%d')) if hasattr(sale.create_date, 'strftime') else None
                            if sale_date and sale_date < date_from_obj:
                                include = False
                        if date_to_obj and sale.create_date:
                            sale_date = fields.Date.from_string(sale.create_date.strftime('%Y-%m-%d')) if hasattr(sale.create_date, 'strftime') else None
                            if sale_date and sale_date > date_to_obj:
                                include = False
                        if include:
                            filtered_sales.append(sale)
                    property_sales = filtered_sales
                
                # EXPECTED: Calculate from sold leads
                expected_customers = len(property_sales)
                expected_amount_birr = sum(sale.sale_price for sale in property_sales if not sale.currency_id or sale.currency_id.name == 'ETB')
                expected_amount_dollar = sum(sale.sale_price for sale in property_sales if sale.currency_id and sale.currency_id.name == 'USD')
                expected_amount_dollar += (expected_amount_birr * exchange_rate) if exchange_rate > 0 else 0
                
                # Calculate ACTUAL data from collections
                # PLAN (EXPECTED): Actual collections (active/draft) - normal flow
                actual_expected_collections = [c for c in site_collections if c.state in ('active', 'draft')]
                actual_expected_customers = len(actual_expected_collections)
                actual_expected_amount_birr = sum(c.amount_collected for c in actual_expected_collections if not c.currency_id or c.currency_id.name == 'ETB')
                actual_expected_amount_dollar = sum(c.amount_collected for c in actual_expected_collections if c.currency_id and c.currency_id.name == 'USD')
                actual_expected_amount_dollar += (actual_expected_amount_birr * exchange_rate) if exchange_rate > 0 else 0
                
                # PENALTY: Actual penalty amounts
                actual_penalty_collections = []
                for c in site_collections:
                    has_penalty = False
                    if c.total_penalty and c.total_penalty > 0:
                        has_penalty = True
                    elif c.installment_ids:
                        for inst in c.installment_ids:
                            if inst.penalty_applied and inst.penalty_amount and inst.penalty_amount > 0:
                                has_penalty = True
                                break
                    if has_penalty:
                        actual_penalty_collections.append(c)
                
                actual_penalty_customers = len(actual_penalty_collections)
                actual_penalty_amount_birr = 0.0
                actual_penalty_amount_dollar = 0.0
                for c in actual_penalty_collections:
                    if c.total_penalty and c.total_penalty > 0:
                        if not c.currency_id or c.currency_id.name == 'ETB':
                            actual_penalty_amount_birr += c.total_penalty
                        elif c.currency_id.name == 'USD':
                            actual_penalty_amount_dollar += c.total_penalty
                    else:
                        for inst in c.installment_ids:
                            if inst.penalty_applied and inst.penalty_amount and inst.penalty_amount > 0:
                                if not inst.currency_id or inst.currency_id.name == 'ETB':
                                    actual_penalty_amount_birr += inst.penalty_amount
                                elif inst.currency_id and inst.currency_id.name == 'USD':
                                    actual_penalty_amount_dollar += inst.penalty_amount
                
                actual_penalty_amount_dollar += (actual_penalty_amount_birr * exchange_rate) if exchange_rate > 0 else 0
                
                # TERMINATION: Actual terminated collections
                actual_termination_collections = [c for c in site_collections if c.state == 'terminated']
                actual_termination_customers = len(actual_termination_collections)
                actual_termination_amount_birr = sum(c.amount_collected for c in actual_termination_collections if not c.currency_id or c.currency_id.name == 'ETB')
                actual_termination_amount_dollar = sum(c.amount_collected for c in actual_termination_collections if c.currency_id and c.currency_id.name == 'USD')
                actual_termination_amount_dollar += (actual_termination_amount_birr * exchange_rate) if exchange_rate > 0 else 0
                
                # TOTAL: Actual total
                actual_total_customers = len([c for c in site_collections if c.amount_collected > 0])
                actual_total_amount_birr = sum(c.amount_collected for c in site_collections if not c.currency_id or c.currency_id.name == 'ETB')
                actual_total_amount_dollar = sum(c.amount_collected for c in site_collections if c.currency_id and c.currency_id.name == 'USD')
                actual_total_amount_dollar += (actual_total_amount_birr * exchange_rate) if exchange_rate > 0 else 0
                
                # Check if there's a plan for this site
                plan = plans_by_site.get(site_id)
                
                if plan:
                    # Use plan data for PLAN (normal plan), PENALTY and TERMINATION
                    _logger.info(f"Site {site_name}: Using plan data from plan '{plan.name}'")
                    plan_plan_customers = plan.plan_customers
                    plan_plan_amount_birr = plan.plan_amount_birr
                    plan_plan_amount_dollar = plan.plan_amount_dollar
                    
                    plan_penalty_customers = plan.penalty_customers
                    plan_penalty_amount_birr = plan.penalty_amount_birr
                    plan_penalty_amount_dollar = plan.penalty_amount_dollar
                    
                    plan_termination_customers = plan.termination_customers
                    plan_termination_amount_birr = plan.termination_amount_birr
                    plan_termination_amount_dollar = plan.termination_amount_dollar
                else:
                    # No plan exists - show 0 for plan, penalty and termination plans
                    _logger.info(f"Site {site_name}: No plan found, showing 0 for plan, penalty and termination plans")
                    plan_plan_customers = 0
                    plan_plan_amount_birr = 0.0
                    plan_plan_amount_dollar = 0.0
                    
                    plan_penalty_customers = 0
                    plan_penalty_amount_birr = 0.0
                    plan_penalty_amount_dollar = 0.0
                    
                    plan_termination_customers = 0
                    plan_termination_amount_birr = 0.0
                    plan_termination_amount_dollar = 0.0
                
                # Calculate totals (TOTAL = PLAN + PENALTY + TERMINATION)
                plan_total_customers = plan_plan_customers + plan_penalty_customers + plan_termination_customers
                plan_total_amount_birr = plan_plan_amount_birr + plan_penalty_amount_birr + plan_termination_amount_birr
                plan_total_amount_dollar = plan_plan_amount_dollar + plan_penalty_amount_dollar + plan_termination_amount_dollar
                
                # Calculate differences (Plan - Actual)
                # For PLAN (normal plan)
                diff_plan_customers = plan_plan_customers - actual_expected_customers
                diff_plan_amount_birr = plan_plan_amount_birr - actual_expected_amount_birr
                diff_plan_amount_dollar = plan_plan_amount_dollar - actual_expected_amount_dollar
                
                # For EXPECTED (from sold leads)
                diff_expected_customers = expected_customers - actual_expected_customers
                diff_expected_amount_birr = expected_amount_birr - actual_expected_amount_birr
                diff_expected_amount_dollar = expected_amount_dollar - actual_expected_amount_dollar
                
                diff_penalty_customers = plan_penalty_customers - actual_penalty_customers
                diff_penalty_amount_birr = plan_penalty_amount_birr - actual_penalty_amount_birr
                diff_penalty_amount_dollar = plan_penalty_amount_dollar - actual_penalty_amount_dollar
                
                diff_termination_customers = plan_termination_customers - actual_termination_customers
                diff_termination_amount_birr = plan_termination_amount_birr - actual_termination_amount_birr
                diff_termination_amount_dollar = plan_termination_amount_dollar - actual_termination_amount_dollar
                
                diff_total_customers = plan_total_customers - actual_total_customers
                diff_total_amount_birr = plan_total_amount_birr - actual_total_amount_birr
                diff_total_amount_dollar = plan_total_amount_dollar - actual_total_amount_dollar
                
                report_data.append({
                    'sno': len(report_data) + 1,
                    'item_name': site_name or '',
                    # PLAN data (from plan model)
                    'plan_customers': plan_plan_customers,
                    'plan_amount_birr': round(plan_plan_amount_birr, 2),
                    'plan_amount_dollar': round(plan_plan_amount_dollar, 2),
                    # EXPECTED data (from sold leads)
                    'expected_customers': expected_customers,
                    'expected_amount_birr': round(expected_amount_birr, 2),
                    'expected_amount_dollar': round(expected_amount_dollar, 2),
                    'penalty_customers': plan_penalty_customers,
                    'penalty_amount_birr': round(plan_penalty_amount_birr, 2),
                    'penalty_amount_dollar': round(plan_penalty_amount_dollar, 2),
                    'termination_customers': plan_termination_customers,
                    'termination_amount_birr': round(plan_termination_amount_birr, 2),
                    'termination_amount_dollar': round(plan_termination_amount_dollar, 2),
                    'total_customers': plan_total_customers,
                    'total_amount_birr': round(plan_total_amount_birr, 2),
                    'total_amount_dollar': round(plan_total_amount_dollar, 2),
                    # ACTUAL data
                    'actual_expected_customers': actual_expected_customers,
                    'actual_expected_amount_birr': round(actual_expected_amount_birr, 2),
                    'actual_expected_amount_dollar': round(actual_expected_amount_dollar, 2),
                    'actual_penalty_customers': actual_penalty_customers,
                    'actual_penalty_amount_birr': round(actual_penalty_amount_birr, 2),
                    'actual_penalty_amount_dollar': round(actual_penalty_amount_dollar, 2),
                    'actual_termination_customers': actual_termination_customers,
                    'actual_termination_amount_birr': round(actual_termination_amount_birr, 2),
                    'actual_termination_amount_dollar': round(actual_termination_amount_dollar, 2),
                    'actual_total_customers': actual_total_customers,
                    'actual_total_amount_birr': round(actual_total_amount_birr, 2),
                    'actual_total_amount_dollar': round(actual_total_amount_dollar, 2),
                    # DIFFERENCE data (Plan - Actual)
                    'diff_plan_customers': diff_plan_customers,
                    'diff_plan_amount_birr': round(diff_plan_amount_birr, 2),
                    'diff_plan_amount_dollar': round(diff_plan_amount_dollar, 2),
                    'diff_expected_customers': diff_expected_customers,
                    'diff_expected_amount_birr': round(diff_expected_amount_birr, 2),
                    'diff_expected_amount_dollar': round(diff_expected_amount_dollar, 2),
                    'diff_penalty_customers': diff_penalty_customers,
                    'diff_penalty_amount_birr': round(diff_penalty_amount_birr, 2),
                    'diff_penalty_amount_dollar': round(diff_penalty_amount_dollar, 2),
                    'diff_termination_customers': diff_termination_customers,
                    'diff_termination_amount_birr': round(diff_termination_amount_birr, 2),
                    'diff_termination_amount_dollar': round(diff_termination_amount_dollar, 2),
                    'diff_total_customers': diff_total_customers,
                    'diff_total_amount_birr': round(diff_total_amount_birr, 2),
                    'diff_total_amount_dollar': round(diff_total_amount_dollar, 2),
                    'is_total': False
                })
            
            # Calculate totals
            totals = {
                # PLAN totals (from plan model)
                'plan_customers': sum(d.get('plan_customers', 0) for d in report_data),
                'plan_amount_birr': sum(d.get('plan_amount_birr', 0) for d in report_data),
                'plan_amount_dollar': sum(d.get('plan_amount_dollar', 0) for d in report_data),
                # EXPECTED totals (from sold leads)
                'expected_customers': sum(d.get('expected_customers', 0) for d in report_data),
                'expected_amount_birr': sum(d.get('expected_amount_birr', 0) for d in report_data),
                'expected_amount_dollar': sum(d.get('expected_amount_dollar', 0) for d in report_data),
                'penalty_customers': sum(d['penalty_customers'] for d in report_data),
                'penalty_amount_birr': sum(d['penalty_amount_birr'] for d in report_data),
                'penalty_amount_dollar': sum(d['penalty_amount_dollar'] for d in report_data),
                'termination_customers': sum(d['termination_customers'] for d in report_data),
                'termination_amount_birr': sum(d['termination_amount_birr'] for d in report_data),
                'termination_amount_dollar': sum(d['termination_amount_dollar'] for d in report_data),
                'total_customers': sum(d['total_customers'] for d in report_data),
                'total_amount_birr': sum(d['total_amount_birr'] for d in report_data),
                'total_amount_dollar': sum(d['total_amount_dollar'] for d in report_data),
                # ACTUAL totals
                'actual_expected_customers': sum(d.get('actual_expected_customers', 0) for d in report_data),
                'actual_expected_amount_birr': sum(d.get('actual_expected_amount_birr', 0) for d in report_data),
                'actual_expected_amount_dollar': sum(d.get('actual_expected_amount_dollar', 0) for d in report_data),
                'actual_penalty_customers': sum(d.get('actual_penalty_customers', 0) for d in report_data),
                'actual_penalty_amount_birr': sum(d.get('actual_penalty_amount_birr', 0) for d in report_data),
                'actual_penalty_amount_dollar': sum(d.get('actual_penalty_amount_dollar', 0) for d in report_data),
                'actual_termination_customers': sum(d.get('actual_termination_customers', 0) for d in report_data),
                'actual_termination_amount_birr': sum(d.get('actual_termination_amount_birr', 0) for d in report_data),
                'actual_termination_amount_dollar': sum(d.get('actual_termination_amount_dollar', 0) for d in report_data),
                'actual_total_customers': sum(d.get('actual_total_customers', 0) for d in report_data),
                'actual_total_amount_birr': sum(d.get('actual_total_amount_birr', 0) for d in report_data),
                'actual_total_amount_dollar': sum(d.get('actual_total_amount_dollar', 0) for d in report_data),
                # DIFFERENCE totals
                'diff_plan_customers': sum(d.get('diff_plan_customers', 0) for d in report_data),
                'diff_plan_amount_birr': sum(d.get('diff_plan_amount_birr', 0) for d in report_data),
                'diff_plan_amount_dollar': sum(d.get('diff_plan_amount_dollar', 0) for d in report_data),
                'diff_expected_customers': sum(d.get('diff_expected_customers', 0) for d in report_data),
                'diff_expected_amount_birr': sum(d.get('diff_expected_amount_birr', 0) for d in report_data),
                'diff_expected_amount_dollar': sum(d.get('diff_expected_amount_dollar', 0) for d in report_data),
                'diff_penalty_customers': sum(d.get('diff_penalty_customers', 0) for d in report_data),
                'diff_penalty_amount_birr': sum(d.get('diff_penalty_amount_birr', 0) for d in report_data),
                'diff_penalty_amount_dollar': sum(d.get('diff_penalty_amount_dollar', 0) for d in report_data),
                'diff_termination_customers': sum(d.get('diff_termination_customers', 0) for d in report_data),
                'diff_termination_amount_birr': sum(d.get('diff_termination_amount_birr', 0) for d in report_data),
                'diff_termination_amount_dollar': sum(d.get('diff_termination_amount_dollar', 0) for d in report_data),
                'diff_total_customers': sum(d.get('diff_total_customers', 0) for d in report_data),
                'diff_total_amount_birr': sum(d.get('diff_total_amount_birr', 0) for d in report_data),
                'diff_total_amount_dollar': sum(d.get('diff_total_amount_dollar', 0) for d in report_data),
            }
            
            # Add total row
            report_data.append({
                'sno': '',
                'item_name': 'TOTAL',
                # PLAN (from plan model)
                'plan_customers': totals['plan_customers'],
                'plan_amount_birr': round(totals['plan_amount_birr'], 2),
                'plan_amount_dollar': round(totals['plan_amount_dollar'], 2),
                # EXPECTED (from sold leads)
                'expected_customers': totals['expected_customers'],
                'expected_amount_birr': round(totals['expected_amount_birr'], 2),
                'expected_amount_dollar': round(totals['expected_amount_dollar'], 2),
                'penalty_customers': totals['penalty_customers'],
                'penalty_amount_birr': round(totals['penalty_amount_birr'], 2),
                'penalty_amount_dollar': round(totals['penalty_amount_dollar'], 2),
                'termination_customers': totals['termination_customers'],
                'termination_amount_birr': round(totals['termination_amount_birr'], 2),
                'termination_amount_dollar': round(totals['termination_amount_dollar'], 2),
                'total_customers': totals['total_customers'],
                'total_amount_birr': round(totals['total_amount_birr'], 2),
                'total_amount_dollar': round(totals['total_amount_dollar'], 2),
                # ACTUAL
                'actual_expected_customers': totals['actual_expected_customers'],
                'actual_expected_amount_birr': round(totals['actual_expected_amount_birr'], 2),
                'actual_expected_amount_dollar': round(totals['actual_expected_amount_dollar'], 2),
                'actual_penalty_customers': totals['actual_penalty_customers'],
                'actual_penalty_amount_birr': round(totals['actual_penalty_amount_birr'], 2),
                'actual_penalty_amount_dollar': round(totals['actual_penalty_amount_dollar'], 2),
                'actual_termination_customers': totals['actual_termination_customers'],
                'actual_termination_amount_birr': round(totals['actual_termination_amount_birr'], 2),
                'actual_termination_amount_dollar': round(totals['actual_termination_amount_dollar'], 2),
                'actual_total_customers': totals['actual_total_customers'],
                'actual_total_amount_birr': round(totals['actual_total_amount_birr'], 2),
                'actual_total_amount_dollar': round(totals['actual_total_amount_dollar'], 2),
                # DIFFERENCE
                'diff_plan_customers': totals['diff_plan_customers'],
                'diff_plan_amount_birr': round(totals['diff_plan_amount_birr'], 2),
                'diff_plan_amount_dollar': round(totals['diff_plan_amount_dollar'], 2),
                'diff_expected_customers': totals['diff_expected_customers'],
                'diff_expected_amount_birr': round(totals['diff_expected_amount_birr'], 2),
                'diff_expected_amount_dollar': round(totals['diff_expected_amount_dollar'], 2),
                'diff_penalty_customers': totals['diff_penalty_customers'],
                'diff_penalty_amount_birr': round(totals['diff_penalty_amount_birr'], 2),
                'diff_penalty_amount_dollar': round(totals['diff_penalty_amount_dollar'], 2),
                'diff_termination_customers': totals['diff_termination_customers'],
                'diff_termination_amount_birr': round(totals['diff_termination_amount_birr'], 2),
                'diff_termination_amount_dollar': round(totals['diff_termination_amount_dollar'], 2),
                'diff_total_customers': totals['diff_total_customers'],
                'diff_total_amount_birr': round(totals['diff_total_amount_birr'], 2),
                'diff_total_amount_dollar': round(totals['diff_total_amount_dollar'], 2),
                'is_total': True
            })
            
            return {
                'success': True,
                'data': report_data,
                'totals': totals
            }
            
        except Exception as e:
            _logger.error(f"Error in plan_stage_report API: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'totals': {}
            }
    
    @http.route('/collection_reports/api/report_stage_report', type='json', auth='user', methods=['POST'], csrf=False)
    def api_report_stage_report(self, **kwargs):
        """
        API endpoint for Report Based on Collection Stage
        This shows ACTUAL EXECUTION data compared against the PLAN
        Returns data grouped by site with:
        - EXPECTED: Actual collected amounts (amount_collected) from active/draft collections
        - PENALITY: Actual penalty amounts collected
        - TERMINATION: Actual collected amounts from terminated collections
        - OTHER COLLECTION: Other collections collected (not in plan)
        - TOTAL COLLECTION REPORT: Total actual collected amounts (execution vs plan comparison)
        """
        try:
            # Get filters from request - handle both JSON-RPC format and direct params
            params = {}
            if 'params' in kwargs and isinstance(kwargs.get('params'), dict):
                params = kwargs.get('params', {})
            elif isinstance(kwargs, dict):
                params = kwargs
            
            site_id = params.get('site_id') or kwargs.get('site_id')
            date_from = params.get('date_from') or kwargs.get('date_from')
            date_to = params.get('date_to') or kwargs.get('date_to')
            
            # Handle None values from JavaScript
            if date_from == 'null' or date_from is None:
                date_from = None
            if date_to == 'null' or date_to is None:
                date_to = None
            
            # Convert site_id to integer if provided
            site_id_int = None
            if site_id and site_id != '' and site_id != 'null':
                try:
                    site_id_int = int(site_id)
                except:
                    site_id_int = None
            
            # Convert date strings to datetime objects
            date_from_obj = None
            date_to_obj = None
            if date_from and date_from != 'null' and date_from != '':
                try:
                    date_from_obj = fields.Date.from_string(date_from)
                except:
                    date_from_obj = None
            if date_to and date_to != 'null' and date_to != '':
                try:
                    date_to_obj = fields.Date.from_string(date_to)
                except:
                    date_to_obj = None
            
            # Get exchange rate
            exchange_rate = _fetch_exchange_rate_from_api()
            if not exchange_rate or exchange_rate <= 0 or exchange_rate > 0.1:
                exchange_rate = 0.0064  # Default fallback
            _logger.info(f"Report Stage Report: Using exchange rate {exchange_rate} (1 ETB = {exchange_rate} USD)")
            
            # Get collection plans for PLAN data (same logic as api_plan_stage_report)
            plan_domain = [('active', '=', True)]
            if site_id_int is not None:
                plan_domain.append(('site_id', '=', site_id_int))
            
            # Filter plans by date range if provided (same as api_plan_stage_report)
            # When "Show All" is selected, date_from_obj and date_to_obj will be None, so we get all active plans
            if date_from_obj or date_to_obj:
                # Find plans where the plan's date range overlaps with the requested date range
                # Plan is valid if: plan.date_from <= date_to AND plan.date_to >= date_from
                if date_from_obj:
                    plan_domain.append(('date_to', '>=', date_from_obj))
                if date_to_obj:
                    plan_domain.append(('date_from', '<=', date_to_obj))
            
            collection_plans = request.env['collection.plan.stage'].search(plan_domain)
            plans_by_site = {plan.site_id.id: plan for plan in collection_plans}
            _logger.info(f"Report Stage Report: Found {len(collection_plans)} active plans (date_from={date_from_obj}, date_to={date_to_obj})")
            
            # Get all sites
            properties = request.env['property.property'].search([])
            site_dict = {}
            
            for prop in properties:
                try:
                    if hasattr(prop, 'site') and prop.site:
                        site_id = prop.site.id
                        site_name = prop.site.name
                        if site_id not in site_dict:
                            site_dict[site_id] = {
                                'name': site_name,
                                'properties': set(),
                                'collections': set()
                            }
                        site_dict[site_id]['properties'].add(prop.id)
                    elif hasattr(prop, 'site_id') and prop.site_id:
                        site_id = prop.site_id.id
                        site_name = prop.site_id.name
                        if site_id not in site_dict:
                            site_dict[site_id] = {
                                'name': site_name,
                                'properties': set(),
                                'collections': set()
                            }
                        site_dict[site_id]['properties'].add(prop.id)
                except:
                    continue
            
            # Get collections
            collection_orders = request.env['collection.order'].search([])
            for coll in collection_orders:
                try:
                    if coll.property_id:
                        if hasattr(coll.property_id, 'site') and coll.property_id.site:
                            site_id = coll.property_id.site.id
                            if site_id in site_dict:
                                site_dict[site_id]['collections'].add(coll.id)
                        elif hasattr(coll.property_id, 'site_id') and coll.property_id.site_id:
                            site_id = coll.property_id.site_id.id
                            if site_id in site_dict:
                                site_dict[site_id]['collections'].add(coll.id)
                except:
                    continue
            
            report_data = []
            
            for site_id, site_data in site_dict.items():
                # Filter by site_id if provided
                if site_id_int is not None and site_id != site_id_int:
                    continue
                
                site_name = site_data['name']
                site_collection_ids = list(site_data['collections'])
                site_collections = request.env['collection.order'].browse(site_collection_ids)
                
                # Filter by date if provided
                if date_from_obj or date_to_obj:
                    filtered_collections = []
                    for coll in site_collections:
                        include = True
                        if date_from_obj and coll.create_date:
                            coll_date = fields.Date.from_string(coll.create_date.strftime('%Y-%m-%d')) if hasattr(coll.create_date, 'strftime') else None
                            if coll_date and coll_date < date_from_obj:
                                include = False
                        if date_to_obj and coll.create_date:
                            coll_date = fields.Date.from_string(coll.create_date.strftime('%Y-%m-%d')) if hasattr(coll.create_date, 'strftime') else None
                            if coll_date and coll_date > date_to_obj:
                                include = False
                        if include:
                            filtered_collections.append(coll)
                    site_collections = filtered_collections
                
                # EXPECTED: Actual collected amounts (EXECUTION - uses amount_collected, not amount_total)
                expected_collections = [c for c in site_collections if c.state in ('active', 'draft')]
                expected_customers = len(expected_collections)
                # Use amount_collected (EXECUTION) not amount_total (PLAN)
                expected_amount_birr = sum(c.amount_collected for c in expected_collections if not c.currency_id or c.currency_id.name == 'ETB')
                expected_amount_dollar = sum(c.amount_collected for c in expected_collections if c.currency_id and c.currency_id.name == 'USD')
                expected_amount_dollar += (expected_amount_birr * exchange_rate) if exchange_rate > 0 else 0
                
                # PENALITY: Actual penalty amounts collected (EXECUTION)
                penalty_collections = []
                for c in site_collections:
                    has_penalty = False
                    if c.total_penalty and c.total_penalty > 0:
                        has_penalty = True
                    elif c.installment_ids:
                        for inst in c.installment_ids:
                            if inst.penalty_applied and inst.penalty_amount and inst.penalty_amount > 0:
                                has_penalty = True
                                break
                    if has_penalty:
                        penalty_collections.append(c)
                
                penalty_customers = len(penalty_collections)
                penalty_amount_birr = 0.0
                penalty_amount_dollar = 0.0
                for c in penalty_collections:
                    if c.total_penalty and c.total_penalty > 0:
                        if not c.currency_id or c.currency_id.name == 'ETB':
                            penalty_amount_birr += c.total_penalty
                        elif c.currency_id.name == 'USD':
                            penalty_amount_dollar += c.total_penalty
                    else:
                        for inst in c.installment_ids:
                            if inst.penalty_applied and inst.penalty_amount and inst.penalty_amount > 0:
                                if not inst.currency_id or inst.currency_id.name == 'ETB':
                                    penalty_amount_birr += inst.penalty_amount
                                elif inst.currency_id and inst.currency_id.name == 'USD':
                                    penalty_amount_dollar += inst.penalty_amount
                
                penalty_amount_dollar += (penalty_amount_birr * exchange_rate) if exchange_rate > 0 else 0
                
                # TERMINATION: Actual collected amounts from terminated collections (EXECUTION)
                termination_collections = [c for c in site_collections if c.state == 'terminated']
                termination_customers = len(termination_collections)
                # Use amount_collected (actual execution) not amount_total (plan)
                termination_amount_birr = sum(c.amount_collected for c in termination_collections if not c.currency_id or c.currency_id.name == 'ETB')
                termination_amount_dollar = sum(c.amount_collected for c in termination_collections if c.currency_id and c.currency_id.name == 'USD')
                termination_amount_dollar += (termination_amount_birr * exchange_rate) if exchange_rate > 0 else 0
                
                # OTHER COLLECTION: Other collections collected (not in plan) - EXECUTION
                other_collections = [c for c in site_collections 
                                   if c.state == 'active' and (not c.sale_id or c.sale_id.property_id.state != 'sold')]
                other_customers = len(other_collections)
                # Use amount_collected (actual execution)
                other_amount_birr = sum(c.amount_collected for c in other_collections if not c.currency_id or c.currency_id.name == 'ETB')
                other_amount_dollar = sum(c.amount_collected for c in other_collections if c.currency_id and c.currency_id.name == 'USD')
                other_amount_dollar += (other_amount_birr * exchange_rate) if exchange_rate > 0 else 0
                
                # TOTAL COLLECTION REPORT: Total actual collected amounts (EXECUTION vs PLAN comparison)
                # This shows actual execution (amount_collected) - what was actually collected
                total_customers = len([c for c in site_collections if c.amount_collected > 0])
                total_amount_birr = sum(c.amount_collected for c in site_collections if not c.currency_id or c.currency_id.name == 'ETB')
                total_amount_dollar = sum(c.amount_collected for c in site_collections if c.currency_id and c.currency_id.name == 'USD')
                total_amount_dollar += (total_amount_birr * exchange_rate) if exchange_rate > 0 else 0
                
                # Get PLAN data from collection.plan.stage
                plan = plans_by_site.get(site_id)
                
                if plan:
                    # Use plan data for PLAN (normal plan), PENALTY and TERMINATION
                    _logger.info(f"Site {site_name}: Using plan data from plan '{plan.name}' - plan_customers={plan.plan_customers}, penalty_customers={plan.penalty_customers}, termination_customers={plan.termination_customers}")
                    plan_plan_customers = plan.plan_customers
                    plan_plan_amount_birr = plan.plan_amount_birr
                    plan_plan_amount_dollar = plan.plan_amount_dollar
                    
                    plan_penalty_customers = plan.penalty_customers
                    plan_penalty_amount_birr = plan.penalty_amount_birr
                    plan_penalty_amount_dollar = plan.penalty_amount_dollar
                    
                    plan_termination_customers = plan.termination_customers
                    plan_termination_amount_birr = plan.termination_amount_birr
                    plan_termination_amount_dollar = plan.termination_amount_dollar
                else:
                    # No plan exists - show 0 for plan, penalty and termination plans
                    _logger.warning(f"Site {site_name}: No plan found for site_id={site_id}, showing 0 for plan data")
                    plan_plan_customers = 0
                    plan_plan_amount_birr = 0.0
                    plan_plan_amount_dollar = 0.0
                    
                    plan_penalty_customers = 0
                    plan_penalty_amount_birr = 0.0
                    plan_penalty_amount_dollar = 0.0
                    
                    plan_termination_customers = 0
                    plan_termination_amount_birr = 0.0
                    plan_termination_amount_dollar = 0.0
                
                row_data = {
                    'sno': len(report_data) + 1,
                    'project_name': site_name or '',
                    # PLAN data (from collection.plan.stage)
                    'plan_customers': plan_plan_customers,
                    'plan_amount_birr': round(plan_plan_amount_birr, 2),
                    'plan_amount_dollar': round(plan_plan_amount_dollar, 2),
                    'penalty_customers': plan_penalty_customers,
                    'penalty_amount_birr': round(plan_penalty_amount_birr, 2),
                    'penalty_amount_dollar': round(plan_penalty_amount_dollar, 2),
                    'termination_customers': plan_termination_customers,
                    'termination_amount_birr': round(plan_termination_amount_birr, 2),
                    'termination_amount_dollar': round(plan_termination_amount_dollar, 2),
                    # REPORT data (actual collections - EXECUTION)
                    # These are the actual counts/amounts from collections (same as "Plan Based on Collection Stage" shows)
                    'actual_expected_customers': expected_customers,
                    'actual_expected_amount_birr': round(expected_amount_birr, 2),
                    'actual_expected_amount_dollar': round(expected_amount_dollar, 2),
                    'actual_penalty_customers': penalty_customers,
                    'actual_penalty_amount_birr': round(penalty_amount_birr, 2),
                    'actual_penalty_amount_dollar': round(penalty_amount_dollar, 2),
                    'actual_termination_customers': termination_customers,
                    'actual_termination_amount_birr': round(termination_amount_birr, 2),
                    'actual_termination_amount_dollar': round(termination_amount_dollar, 2),
                    'other_customers': other_customers,
                    'other_amount_birr': round(other_amount_birr, 2),
                    'other_amount_dollar': round(other_amount_dollar, 2),
                    'actual_total_customers': total_customers,
                    'actual_total_amount_birr': round(total_amount_birr, 2),
                    'actual_total_amount_dollar': round(total_amount_dollar, 2),
                    'is_total': False
                }
                _logger.info(f"Site {site_name}: Returning row data - plan_customers={row_data['plan_customers']}, actual_expected_customers={row_data['actual_expected_customers']}")
                report_data.append(row_data)
            
            # Calculate totals - using the new field names
            totals = {
                # PLAN totals
                'plan_customers': sum(d.get('plan_customers', 0) for d in report_data),
                'plan_amount_birr': sum(d.get('plan_amount_birr', 0) for d in report_data),
                'plan_amount_dollar': sum(d.get('plan_amount_dollar', 0) for d in report_data),
                'penalty_customers': sum(d.get('penalty_customers', 0) for d in report_data),
                'penalty_amount_birr': sum(d.get('penalty_amount_birr', 0) for d in report_data),
                'penalty_amount_dollar': sum(d.get('penalty_amount_dollar', 0) for d in report_data),
                'termination_customers': sum(d.get('termination_customers', 0) for d in report_data),
                'termination_amount_birr': sum(d.get('termination_amount_birr', 0) for d in report_data),
                'termination_amount_dollar': sum(d.get('termination_amount_dollar', 0) for d in report_data),
                # REPORT totals (actual collections)
                'actual_expected_customers': sum(d.get('actual_expected_customers', 0) for d in report_data),
                'actual_expected_amount_birr': sum(d.get('actual_expected_amount_birr', 0) for d in report_data),
                'actual_expected_amount_dollar': sum(d.get('actual_expected_amount_dollar', 0) for d in report_data),
                'actual_penalty_customers': sum(d.get('actual_penalty_customers', 0) for d in report_data),
                'actual_penalty_amount_birr': sum(d.get('actual_penalty_amount_birr', 0) for d in report_data),
                'actual_penalty_amount_dollar': sum(d.get('actual_penalty_amount_dollar', 0) for d in report_data),
                'actual_termination_customers': sum(d.get('actual_termination_customers', 0) for d in report_data),
                'actual_termination_amount_birr': sum(d.get('actual_termination_amount_birr', 0) for d in report_data),
                'actual_termination_amount_dollar': sum(d.get('actual_termination_amount_dollar', 0) for d in report_data),
                'other_customers': sum(d.get('other_customers', 0) for d in report_data),
                'other_amount_birr': sum(d.get('other_amount_birr', 0) for d in report_data),
                'other_amount_dollar': sum(d.get('other_amount_dollar', 0) for d in report_data),
                'actual_total_customers': sum(d.get('actual_total_customers', 0) for d in report_data),
                'actual_total_amount_birr': sum(d.get('actual_total_amount_birr', 0) for d in report_data),
                'actual_total_amount_dollar': sum(d.get('actual_total_amount_dollar', 0) for d in report_data),
            }
            
            # Add total row - using the new field names
            report_data.append({
                'sno': '',
                'project_name': 'TOTAL',
                # PLAN data
                'plan_customers': totals['plan_customers'],
                'plan_amount_birr': round(totals['plan_amount_birr'], 2),
                'plan_amount_dollar': round(totals['plan_amount_dollar'], 2),
                'penalty_customers': totals['penalty_customers'],
                'penalty_amount_birr': round(totals['penalty_amount_birr'], 2),
                'penalty_amount_dollar': round(totals['penalty_amount_dollar'], 2),
                'termination_customers': totals['termination_customers'],
                'termination_amount_birr': round(totals['termination_amount_birr'], 2),
                'termination_amount_dollar': round(totals['termination_amount_dollar'], 2),
                # REPORT data (actual collections)
                'actual_expected_customers': totals['actual_expected_customers'],
                'actual_expected_amount_birr': round(totals['actual_expected_amount_birr'], 2),
                'actual_expected_amount_dollar': round(totals['actual_expected_amount_dollar'], 2),
                'actual_penalty_customers': totals['actual_penalty_customers'],
                'actual_penalty_amount_birr': round(totals['actual_penalty_amount_birr'], 2),
                'actual_penalty_amount_dollar': round(totals['actual_penalty_amount_dollar'], 2),
                'actual_termination_customers': totals['actual_termination_customers'],
                'actual_termination_amount_birr': round(totals['actual_termination_amount_birr'], 2),
                'actual_termination_amount_dollar': round(totals['actual_termination_amount_dollar'], 2),
                'other_customers': totals['other_customers'],
                'other_amount_birr': round(totals['other_amount_birr'], 2),
                'other_amount_dollar': round(totals['other_amount_dollar'], 2),
                'actual_total_customers': totals['actual_total_customers'],
                'actual_total_amount_birr': round(totals['actual_total_amount_birr'], 2),
                'actual_total_amount_dollar': round(totals['actual_total_amount_dollar'], 2),
                'is_total': True
            })
            
            return {
                'success': True,
                'data': report_data,
                'totals': totals
            }
            
        except Exception as e:
            _logger.error(f"Error in report_stage_report API: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'totals': {}
            }
    
    @http.route('/collection_reports/api/summarized_report', type='json', auth='user', methods=['POST'], csrf=False)
    def api_summarized_report(self, **kwargs):
        """API endpoint for Summarized Report data
        
        Requirements:
        - PROJECT NAME = Sites
        - COLLECTION PLAN: Number of customers = Sold leads in that site, Amount in Birr, Amount in Dollar (convert ETB to USD)
        - COLLECTION REPORT (EXECUTION): Number of customers in collection, Amount collected, Dollar equivalent
        - OTHER COLLECTION: Other collections
        - TOTAL COLLECTION: Execution + Other
        - PAYMENT EXTENSION: Collections with payment extensions (extended_date on installments), customer count, amount
        - TOTAL AMOUNT REMAINED UNCOLLECTED: Customer count, amount in Birr, Dollar equivalent
        - COMMUNICATION REPORT: Text, Phone, Letter, Difficulty, Service customers, S.NO
        - SEMI/PARTIAL PAID: Customer count, amount in Birr, Dollar equivalent, Letter not delivered, Remark
        - All must consider date range if provided, otherwise show all
        """
        try:
            # Get filters from request - handle both JSON-RPC format and direct params
            params = {}
            if 'params' in kwargs and isinstance(kwargs.get('params'), dict):
                params = kwargs.get('params', {})
            elif isinstance(kwargs, dict):
                params = kwargs
            
            site_id = params.get('site_id') or kwargs.get('site_id')
            date_from = params.get('date_from') or kwargs.get('date_from')
            date_to = params.get('date_to') or kwargs.get('date_to')
            
            # Handle None values from JavaScript
            if date_from == 'null' or date_from is None:
                date_from = None
            if date_to == 'null' or date_to is None:
                date_to = None
            
            # Convert site_id to integer if provided
            site_id_int = None
            if site_id and site_id != '' and site_id != 'null':
                try:
                    site_id_int = int(site_id)
                except:
                    site_id_int = None
            
            # Convert date strings to datetime objects
            date_from_obj = None
            date_to_obj = None
            if date_from and date_from != 'null' and date_from != '':
                try:
                    date_from_obj = fields.Date.from_string(date_from)
                except:
                    date_from_obj = None
            if date_to and date_to != 'null' and date_to != '':
                try:
                    date_to_obj = fields.Date.from_string(date_to)
                except:
                    date_to_obj = None
            
            # Get latest exchange rate from external API (for Odoo Community Edition)
            # Exchange rate: 1 ETB = X USD (fetched from latest external API)
            default_etb_to_usd_rate = 0.0064  # Fallback rate
            exchange_rate = default_etb_to_usd_rate
            
            # Try to fetch from external API first
            try:
                api_rate = _fetch_exchange_rate_from_api()
                if api_rate and 0.001 <= api_rate <= 0.1:
                    exchange_rate = api_rate
                    _logger.info(f"Summarized Report: Using external API rate {exchange_rate} (1 ETB = {exchange_rate} USD)")
                else:
                    _logger.warning(f"Summarized Report: External API rate {api_rate} invalid, trying Odoo system")
                    raise ValueError("Invalid API rate")
            except Exception as e:
                _logger.debug(f"External API failed: {str(e)}, trying Odoo currency system")
                
                # Fallback: Try Odoo's currency system (if available in Enterprise)
                usd_currency = request.env['res.currency'].search([('name', '=', 'USD')], limit=1)
                etb_currency = request.env['res.currency'].search([('name', '=', 'ETB')], limit=1)
                
                if etb_currency and usd_currency:
                    try:
                        today = fields.Date.today()
                        company = request.env.user.company_id
                        rate = etb_currency._get_conversion_rate(etb_currency, usd_currency, company, today)
                        if rate and 0.001 <= rate <= 0.1:
                            exchange_rate = rate
                            _logger.info(f"Summarized Report: Using Odoo currency rate {exchange_rate} (1 ETB = {exchange_rate} USD)")
                        else:
                            _logger.warning(f"Summarized Report: Odoo rate {rate} invalid, using default {default_etb_to_usd_rate}")
                            exchange_rate = default_etb_to_usd_rate
                    except Exception as e2:
                        _logger.debug(f"Odoo currency system failed: {str(e2)}, using default rate")
                        exchange_rate = default_etb_to_usd_rate
            
            # Final validation
            if exchange_rate <= 0 or exchange_rate > 0.1:
                _logger.warning(f"Summarized Report: Exchange rate {exchange_rate} is invalid, forcing to default {default_etb_to_usd_rate}")
                exchange_rate = default_etb_to_usd_rate
            
            _logger.info(f"Summarized Report: Final exchange rate {exchange_rate} (1 ETB = {exchange_rate} USD) - Example: 10,000,000 ETB = {10000000 * exchange_rate:,.2f} USD")
            
            # Get all active plans, filtered by date range if provided
            plan_domain = [('active', '=', True)]
            if site_id_int is not None:
                plan_domain.append(('site_id', '=', site_id_int))
            
            # Filter by date range if provided
            if date_from_obj or date_to_obj:
                # Find plans where the plan's date range overlaps with the requested date range
                if date_from_obj:
                    plan_domain.append(('date_to', '>=', date_from_obj))
                if date_to_obj:
                    plan_domain.append(('date_from', '<=', date_to_obj))
            
            collection_plans = request.env['collection.plan.stage'].search(plan_domain)
            plans_by_site = {plan.site_id.id: plan for plan in collection_plans}
            _logger.info(f"Summarized Report: Found {len(collection_plans)} active plans")
            
            # Get all sites from properties
            properties = request.env['property.property'].search([])
            site_dict = {}
            
            # Group by site
            for prop in properties:
                try:
                    # Try 'site' field first
                    if hasattr(prop, 'site') and prop.site:
                        site_id = prop.site.id
                        site_name = prop.site.name
                        if site_id not in site_dict:
                            site_dict[site_id] = {
                                'name': site_name,
                                'properties': set(),
                                'collections': set(),
                                'installments': []
                            }
                        site_dict[site_id]['properties'].add(prop.id)
                    # Fallback: try 'site_id'
                    elif hasattr(prop, 'site_id') and prop.site_id:
                        site_id = prop.site_id.id
                        site_name = prop.site_id.name
                        if site_id not in site_dict:
                            site_dict[site_id] = {
                                'name': site_name,
                                'properties': set(),
                                'collections': set(),
                                'installments': []
                            }
                        site_dict[site_id]['properties'].add(prop.id)
                except:
                    continue
            
            # Get collections and installments
            collection_orders = request.env['collection.order'].search([])
            installments = request.env['collection.installment'].search([])
            
            # Get property sales for sold properties
            property_sales = request.env['property.sale'].search([])
            
            for coll in collection_orders:
                try:
                    if coll.property_id:
                        # Try 'site' field first
                        if hasattr(coll.property_id, 'site') and coll.property_id.site:
                            site_id = coll.property_id.site.id
                            if site_id in site_dict:
                                site_dict[site_id]['collections'].add(coll.id)
                        # Fallback: try 'site_id'
                        elif hasattr(coll.property_id, 'site_id') and coll.property_id.site_id:
                            site_id = coll.property_id.site_id.id
                            if site_id in site_dict:
                                site_dict[site_id]['collections'].add(coll.id)
                except:
                    continue
            
            for inst in installments:
                try:
                    if inst.site_id:
                        site_id = inst.site_id.id
                        if site_id not in site_dict:
                            site_dict[site_id] = {
                                'name': inst.site_id.name,
                                'properties': set(),
                                'collections': set(),
                                'installments': []
                            }
                        site_dict[site_id]['installments'].append(inst)
                        if inst.collection_id:
                            site_dict[site_id]['collections'].add(inst.collection_id.id)
                except:
                    continue
            
            report_data = []
            
            for site_id, site_data in site_dict.items():
                # Filter by site_id if provided
                if site_id_int is not None and site_id != site_id_int:
                    continue
                
                site_name = site_data['name']
                site_property_ids = list(site_data['properties'])
                site_collection_ids = list(site_data['collections'])
                site_installments = site_data['installments']
                
                # Get collections for this site
                site_collections = request.env['collection.order'].browse(site_collection_ids)
                
                # Filter by date if provided
                if date_from_obj or date_to_obj:
                    # Filter collections based on creation date or sale date
                    filtered_collections = []
                    for coll in site_collections:
                        include = True
                        if date_from_obj and coll.create_date:
                            coll_date = fields.Date.from_string(coll.create_date.strftime('%Y-%m-%d')) if hasattr(coll.create_date, 'strftime') else None
                            if coll_date and coll_date < date_from_obj:
                                include = False
                        if date_to_obj and coll.create_date:
                            coll_date = fields.Date.from_string(coll.create_date.strftime('%Y-%m-%d')) if hasattr(coll.create_date, 'strftime') else None
                            if coll_date and coll_date > date_to_obj:
                                include = False
                        if include:
                            filtered_collections.append(coll)
                    site_collections = filtered_collections
                
                # COLLECTION PLAN: Get from plan model if available, otherwise calculate from sold sales
                plan = plans_by_site.get(site_id)
                
                if plan:
                    # Use plan data from collection.plan.stage
                    _logger.info(f"Site {site_name}: Using plan data from plan '{plan.name}'")
                    plan_customers = plan.total_customers
                    plan_amount_birr = plan.total_amount_birr
                    plan_amount_dollar = plan.total_amount_dollar
                else:
                    # Fallback: Calculate from sold properties/leads
                    _logger.info(f"Site {site_name}: No plan found, calculating from sold sales")
                    sold_sales = property_sales.filtered(lambda s: s.property_id and s.property_id.id in site_property_ids 
                                                          and s.property_id.state == 'sold')
                    # Filter by date if provided
                    if date_from_obj or date_to_obj:
                        filtered_sales = []
                        for sale in sold_sales:
                            include = True
                            if date_from_obj and sale.create_date:
                                sale_date = fields.Date.from_string(sale.create_date.strftime('%Y-%m-%d')) if hasattr(sale.create_date, 'strftime') else None
                                if sale_date and sale_date < date_from_obj:
                                    include = False
                            if date_to_obj and sale.create_date:
                                sale_date = fields.Date.from_string(sale.create_date.strftime('%Y-%m-%d')) if hasattr(sale.create_date, 'strftime') else None
                                if sale_date and sale_date > date_to_obj:
                                    include = False
                            if include:
                                filtered_sales.append(sale)
                        sold_sales = filtered_sales
                    
                    plan_customers = len(sold_sales)
                    # If currency_id is not set or is None, assume ETB (default currency)
                    plan_amount_birr = sum(sale.sale_price for sale in sold_sales 
                                         if not sale.currency_id or sale.currency_id.name == 'ETB')
                    plan_amount_dollar = sum(sale.sale_price for sale in sold_sales 
                                           if sale.currency_id and sale.currency_id.name == 'USD')
                    # Convert ETB to USD for plan (1 ETB = exchange_rate USD)
                    etb_to_usd_converted = (plan_amount_birr * exchange_rate) if exchange_rate > 0 else 0
                    plan_amount_dollar += etb_to_usd_converted
                    if plan_amount_birr > 0:
                        _logger.info(f"Site {site_name} PLAN: {plan_amount_birr:,.2f} ETB × {exchange_rate} = {etb_to_usd_converted:,.2f} USD (Total USD: {plan_amount_dollar:,.2f})")
                
                # COLLECTION REPORT (EXECUTION): Active collections
                active_collections = [c for c in site_collections if c.state == 'active']
                execution_customers = len(active_collections)
                
                # Get collected amounts from active collections
                # If currency_id is not set or is None, assume ETB (default currency)
                execution_amount_birr = sum(c.amount_collected for c in active_collections 
                                         if not c.currency_id or c.currency_id.name == 'ETB')
                execution_amount_dollar = sum(c.amount_collected for c in active_collections 
                                            if c.currency_id and c.currency_id.name == 'USD')
                # Convert ETB to USD (1 ETB = exchange_rate USD)
                etb_converted = (execution_amount_birr * exchange_rate) if exchange_rate > 0 else 0
                execution_amount_dollar += etb_converted
                if execution_amount_birr > 0:
                    _logger.info(f"Site {site_name} EXECUTION: {execution_amount_birr:,.2f} ETB × {exchange_rate} = {etb_converted:,.2f} USD (Total USD: {execution_amount_dollar:,.2f})")
                
                # Calculate difference (Plan - Actual Execution) - AFTER execution is calculated
                plan_vs_execution_diff_customers = plan_customers - execution_customers
                plan_vs_execution_diff_birr = plan_amount_birr - execution_amount_birr
                plan_vs_execution_diff_dollar = plan_amount_dollar - execution_amount_dollar
                
                # OTHER COLLECTION: Collections not from plan (collections without sales or in different state)
                other_collections = [c for c in site_collections 
                                   if c.state == 'active' and (not c.sale_id or c.sale_id.property_id.state != 'sold')]
                other_customers = len(other_collections)
                # If currency_id is not set or is None, assume ETB (default currency)
                other_amount_birr = sum(c.amount_collected for c in other_collections 
                                      if not c.currency_id or c.currency_id.name == 'ETB')
                other_amount_dollar = sum(c.amount_collected for c in other_collections 
                                        if c.currency_id and c.currency_id.name == 'USD')
                # Convert ETB to USD (1 ETB = 0.0064 USD)
                other_amount_dollar += (other_amount_birr * exchange_rate) if exchange_rate > 0 else 0
                
                # TOTAL COLLECTION (execution + other)
                total_customers = execution_customers + other_customers
                total_amount_birr = execution_amount_birr + other_amount_birr
                total_amount_dollar = execution_amount_dollar + other_amount_dollar
                
                # PAYMENT EXTENSION: Collections with installments that have extended_date
                extension_collections = set()
                extension_amount_birr = 0.0
                for inst in site_installments:
                    if inst.extended_date and inst.collection_id and inst.collection_id.state == 'active':
                        extension_collections.add(inst.collection_id.id)
                        if inst.currency_id.name == 'ETB':
                            extension_amount_birr += inst.amount_total if hasattr(inst, 'amount_total') else 0.0
                extension_customers = len(extension_collections)
                
                # TOTAL AMOUNT REMAINED UNCOLLECTED
                remaining_collections = [c for c in site_collections if c.amount_remaining > 0]
                remaining_customers = len(remaining_collections)
                # If currency_id is not set or is None, assume ETB (default currency)
                remaining_amount_birr = sum(c.amount_remaining for c in remaining_collections 
                                          if not c.currency_id or c.currency_id.name == 'ETB')
                remaining_amount_dollar = sum(c.amount_remaining for c in remaining_collections 
                                             if c.currency_id and c.currency_id.name == 'USD')
                # Convert ETB to USD (1 ETB = 0.0064 USD)
                remaining_amount_dollar += (remaining_amount_birr * exchange_rate) if exchange_rate > 0 else 0
                
                # COMMUNICATION REPORT: TODO - Need to check if there's a communication model
                comm_text = 0
                comm_phone = 0
                comm_letter = 0
                comm_difficulty = 0
                comm_service_customers = 0
                comm_sno = 0
                
                # SEMI/PARTIAL PAID: Collections with partial payment (amount_collected > 0 but amount_remaining > 0)
                partial_collections = [c for c in site_collections 
                                    if c.amount_collected > 0 and c.amount_remaining > 0]
                partial_customers = len(partial_collections)
                # If currency_id is not set or is None, assume ETB (default currency)
                partial_amount_birr = sum(c.amount_remaining for c in partial_collections 
                                       if not c.currency_id or c.currency_id.name == 'ETB')
                partial_amount_dollar = sum(c.amount_remaining for c in partial_collections 
                                          if c.currency_id and c.currency_id.name == 'USD')
                # Convert ETB to USD (1 ETB = 0.0064 USD)
                partial_amount_dollar += (partial_amount_birr * exchange_rate) if exchange_rate > 0 else 0
                partial_letter_not_delivered = 0  # TODO: Need to check if there's a letter delivery tracking
                partial_remark = ''
                
                report_data.append({
                    'sno': len(report_data) + 1,
                    'project_name': site_name or '',
                    'plan_customers': plan_customers,
                    'plan_amount_birr': round(plan_amount_birr, 2),
                    'plan_amount_dollar': round(plan_amount_dollar, 2),
                    'execution_customers': execution_customers,
                    'execution_amount_birr': round(execution_amount_birr, 2),
                    'execution_amount_dollar': round(execution_amount_dollar, 2),
                    # Difference (Plan - Execution)
                    'plan_vs_execution_diff_customers': plan_vs_execution_diff_customers,
                    'plan_vs_execution_diff_birr': round(plan_vs_execution_diff_birr, 2),
                    'plan_vs_execution_diff_dollar': round(plan_vs_execution_diff_dollar, 2),
                    'other_customers': other_customers,
                    'other_amount_birr': round(other_amount_birr, 2),
                    'other_amount_dollar': round(other_amount_dollar, 2),
                    'total_customers': total_customers,
                    'total_amount_birr': round(total_amount_birr, 2),
                    'total_amount_dollar': round(total_amount_dollar, 2),
                    'extension_customers': extension_customers,
                    'extension_amount_birr': round(extension_amount_birr, 2),
                    'remaining_customers': remaining_customers,
                    'remaining_amount_birr': round(remaining_amount_birr, 2),
                    'remaining_amount_dollar': round(remaining_amount_dollar, 2),
                    'comm_text': comm_text,
                    'comm_phone': comm_phone,
                    'comm_letter': comm_letter,
                    'comm_difficulty': comm_difficulty,
                    'comm_service_customers': comm_service_customers,
                    'comm_sno': comm_sno,
                    'partial_letter_not_delivered': partial_letter_not_delivered,
                    'partial_customers': partial_customers,
                    'partial_amount_birr': round(partial_amount_birr, 2),
                    'partial_amount_dollar': round(partial_amount_dollar, 2),
                    'partial_remark': partial_remark,
                })
            
            # Calculate totals
            totals = {
                'plan_customers': sum(d['plan_customers'] for d in report_data),
                'plan_amount_birr': round(sum(d['plan_amount_birr'] for d in report_data), 2),
                'plan_amount_dollar': round(sum(d['plan_amount_dollar'] for d in report_data), 2),
                'execution_customers': sum(d['execution_customers'] for d in report_data),
                'execution_amount_birr': round(sum(d['execution_amount_birr'] for d in report_data), 2),
                'execution_amount_dollar': round(sum(d['execution_amount_dollar'] for d in report_data), 2),
                'plan_vs_execution_diff_customers': sum(d.get('plan_vs_execution_diff_customers', 0) for d in report_data),
                'plan_vs_execution_diff_birr': round(sum(d.get('plan_vs_execution_diff_birr', 0) for d in report_data), 2),
                'plan_vs_execution_diff_dollar': round(sum(d.get('plan_vs_execution_diff_dollar', 0) for d in report_data), 2),
                'other_customers': sum(d['other_customers'] for d in report_data),
                'other_amount_birr': round(sum(d['other_amount_birr'] for d in report_data), 2),
                'other_amount_dollar': round(sum(d['other_amount_dollar'] for d in report_data), 2),
                'total_customers': sum(d['total_customers'] for d in report_data),
                'total_amount_birr': round(sum(d['total_amount_birr'] for d in report_data), 2),
                'total_amount_dollar': round(sum(d['total_amount_dollar'] for d in report_data), 2),
                'extension_customers': sum(d['extension_customers'] for d in report_data),
                'extension_amount_birr': round(sum(d['extension_amount_birr'] for d in report_data), 2),
                'remaining_customers': sum(d['remaining_customers'] for d in report_data),
                'remaining_amount_birr': round(sum(d['remaining_amount_birr'] for d in report_data), 2),
                'remaining_amount_dollar': round(sum(d['remaining_amount_dollar'] for d in report_data), 2),
                'comm_text': sum(d['comm_text'] for d in report_data),
                'comm_phone': sum(d['comm_phone'] for d in report_data),
                'comm_letter': sum(d['comm_letter'] for d in report_data),
                'comm_difficulty': sum(d['comm_difficulty'] for d in report_data),
                'comm_service_customers': sum(d['comm_service_customers'] for d in report_data),
                'comm_sno': sum(d['comm_sno'] for d in report_data),
                'partial_letter_not_delivered': sum(d['partial_letter_not_delivered'] for d in report_data),
                'partial_customers': sum(d['partial_customers'] for d in report_data),
                'partial_amount_birr': round(sum(d['partial_amount_birr'] for d in report_data), 2),
                'partial_amount_dollar': round(sum(d['partial_amount_dollar'] for d in report_data), 2),
            }
            
            _logger.info(f"Summarized Report: Returning {len(report_data)} rows")
            
            return {
                'success': True,
                'data': report_data,
                'totals': totals,
            }
            
        except Exception as e:
            _logger.error(f"Error in summarized_report API: {str(e)}", exc_info=True)
            import traceback
            _logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'totals': {},
            }

    @http.route('/collection_reports/api/export_excel', type='http', auth='user', methods=['POST'], csrf=False)
    def api_export_excel(self, **kwargs):
        """Export report to Excel with proper headers and titles matching the image format"""
        try:
            import io
            from odoo.http import Response
            from datetime import datetime
            
            # Try to use xlsxwriter for proper Excel formatting
            try:
                import xlsxwriter
                use_xlsx = True
            except ImportError:
                # Fallback to CSV if xlsxwriter not available
                import csv
                use_xlsx = False
            
            report_type = kwargs.get('report_type', 'general_info')
            site_id = kwargs.get('site_id')
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            
            # Get report data by calling the appropriate API method
            if report_type == 'general_info':
                params = {
                    'site_id': site_id,
                    'date_from': date_from if date_from else None,
                    'date_to': date_to if date_to else None,
                }
                result = self.api_general_info(params=params)
                section_title = "1. GENERAL INFORMATION"
            elif report_type == 'summarized_report':
                params = {
                    'date_from': date_from if date_from else None,
                    'date_to': date_to if date_to else None,
                }
                result = self.api_summarized_report(params=params)
                section_title = "2. COLLECTION REPORT BASED THE ACTUAL PAID AMOUNT"
            elif report_type == 'plan_stage_report':
                params = {
                    'date_from': date_from if date_from else None,
                    'date_to': date_to if date_to else None,
                }
                result = self.api_plan_stage_report(params=params)
                section_title = "2.1. PLAN BASED ON COLLECTION STAGE"
            elif report_type == 'report_stage_report':
                params = {
                    'date_from': date_from if date_from else None,
                    'date_to': date_to if date_to else None,
                }
                result = self.api_report_stage_report(params=params)
                section_title = "2.2. COLLECTION REPORT BASED ON COLLECTION STAGE"
            else:
                return request.not_found("Invalid report type")
            
            if not result.get('success'):
                return request.not_found(f"Error generating report: {result.get('error', 'Unknown error')}")
            
            report_data = result.get('data', [])
            totals = result.get('totals', {})
            
            # Format date period
            date_period = ""
            if date_from and date_to:
                try:
                    from_date = fields.Date.from_string(date_from)
                    to_date = fields.Date.from_string(date_to)
                    date_period = f"FOR {from_date.strftime('%B %Y')} E.C"
                except:
                    date_period = f"FOR {date_from} TO {date_to}"
            elif date_from:
                try:
                    from_date = fields.Date.from_string(date_from)
                    date_period = f"FOR {from_date.strftime('%B %Y')} E.C"
                except:
                    date_period = f"FOR {date_from}"
            elif date_to:
                try:
                    to_date = fields.Date.from_string(date_to)
                    date_period = f"FOR {to_date.strftime('%B %Y')} E.C"
                except:
                    date_period = f"FOR {date_to}"
            else:
                date_period = "FOR ALL PERIODS"
            
            # Create Excel file with proper formatting
            if use_xlsx:
                # Use xlsxwriter for proper Excel formatting
                output = io.BytesIO()
                workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                worksheet = workbook.add_worksheet()
                
                # Define formats
                title_format = workbook.add_format({
                    'bold': True,
                    'font_size': 14,
                    'align': 'center',
                    'valign': 'vcenter',
                })
                section_format = workbook.add_format({
                    'bold': True,
                    'font_size': 12,
                    'align': 'left',
                })
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#D3D3D3',
                    'border': 1,
                    'align': 'center',
                    'valign': 'vcenter',
                    'text_wrap': True,
                })
                cell_format = workbook.add_format({
                    'border': 1,
                    'align': 'left',
                    'valign': 'vcenter',
                })
                number_format = workbook.add_format({
                    'border': 1,
                    'align': 'right',
                    'valign': 'vcenter',
                })
                center_format = workbook.add_format({
                    'border': 1,
                    'align': 'center',
                    'valign': 'vcenter',
                })
                
                row = 0
                
                # Title: "TEMER PROPERTIES COLLECTION DEPARTMENT MONTHLY REPORT SUMMARY FOR NEHASE 2017 E.C"
                full_title = f"TEMER PROPERTIES COLLECTION DEPARTMENT MONTHLY REPORT SUMMARY {date_period}"
                worksheet.merge_range(row, 0, row, 9, full_title, title_format)
                row += 2  # Empty row for spacing
            
                if report_type == 'general_info':
                    # Section title
                    worksheet.write(row, 0, section_title, section_format)
                    row += 2
                    
                    # Headers
                    headers = ['S,NO', 'SITE', 'PROJECT NAME', 'TOTAL STOCK', 'SOLD STOCK', 
                              'ACTIVE IN MASTER DOCUMENT', 'ACTIVE IN COLLECTION', 'MERGED CONTRACT',
                              'SITE SHIFT', 'FULLY PAID (100%)', 'DHL NUMBER', 'PAYMENT ROUND NUMBER',
                              'REFUND', 'CONTRACT/NOT COMPLETE', 'INCOME CONTRACT']
                    col = 0
                    for header in headers:
                        worksheet.write(row, col, header, header_format)
                        col += 1
                    row += 1
                    
                    # Set column widths
                    worksheet.set_column(0, 0, 8)
                    worksheet.set_column(1, 1, 20)
                    worksheet.set_column(2, 2, 25)
                    worksheet.set_column(3, 14, 15)
                    
                    # Data rows
                    for data_row in report_data:
                        worksheet.write(row, 0, data_row.get('sno', ''), center_format)
                        worksheet.write(row, 1, data_row.get('site_name', '') or data_row.get('project_name', ''), cell_format)
                        worksheet.write(row, 2, data_row.get('project_name', ''), cell_format)
                        worksheet.write(row, 3, data_row.get('total_stock', 0), number_format)
                        worksheet.write(row, 4, data_row.get('sold_stock', 0), number_format)
                        worksheet.write(row, 5, data_row.get('active_master_document', 0), number_format)
                        worksheet.write(row, 6, data_row.get('active_collection', 0), number_format)
                        worksheet.write(row, 7, data_row.get('merged_contract', 0), number_format)
                        worksheet.write(row, 8, data_row.get('site_shift', 0), number_format)
                        worksheet.write(row, 9, data_row.get('fully_paid', 0), number_format)
                        worksheet.write(row, 10, data_row.get('dhl_number', ''), cell_format)
                        worksheet.write(row, 11, data_row.get('payment_round_number', 0), number_format)
                        worksheet.write(row, 12, data_row.get('refund', 0), number_format)
                        worksheet.write(row, 13, data_row.get('contract_not_complete', 0), number_format)
                        worksheet.write(row, 14, data_row.get('income_contract', 0), number_format)
                        row += 1
                    
                    # Total row
                    worksheet.write(row, 0, 'TOTAL', header_format)
                    worksheet.write(row, 1, '', cell_format)
                    worksheet.write(row, 2, '', cell_format)
                    worksheet.write(row, 3, totals.get('total_stock', 0), number_format)
                    worksheet.write(row, 4, totals.get('sold_stock', 0), number_format)
                    worksheet.write(row, 5, totals.get('active_master_document', 0), number_format)
                    worksheet.write(row, 6, totals.get('active_collection', 0), number_format)
                    worksheet.write(row, 7, totals.get('merged_contract', 0), number_format)
                    worksheet.write(row, 8, totals.get('site_shift', 0), number_format)
                    worksheet.write(row, 9, totals.get('fully_paid', 0), number_format)
                    worksheet.write(row, 10, '', cell_format)
                    worksheet.write(row, 11, totals.get('payment_round_number', 0), number_format)
                    worksheet.write(row, 12, totals.get('refund', 0), number_format)
                    worksheet.write(row, 13, totals.get('contract_not_complete', 0), number_format)
                    worksheet.write(row, 14, totals.get('income_contract', 0), number_format)
                    filename = f'general_info_report_{date_from or "all"}_{date_to or "all"}.xlsx'
                
                elif report_type == 'plan_stage_report':
                    # Section title
                    worksheet.write(row, 0, section_title, section_format)
                    row += 2
                    
                    # Headers - multi-row
                    headers_row1 = ['S,NO', 'PROJECT NAME', 'EXPECTED', '', '', 'PLAN', '', '', '', '', '', 'TOTAL COLLECTION PLAN', '', '']
                    headers_row2 = ['', '', 'NO OF CUSTOMERS', 'AMOUNT IN BIRR', 'AMOUNT IN DOLLAR', 
                                    'PENALITY', '', '', 'TERMINATION', '', '', 'NO OF CUSTOMERS', 'AMOUNT IN BIRR', 'AMOUNT IN DOLLAR']
                    headers_row3 = ['', '', '', '', '', 'NO OF CUSTOMERS', 'AMOUNT IN BIRR', 'AMOUNT IN DOLLAR',
                                    'NO OF CUSTOMERS', 'AMOUNT IN BIRR', 'AMOUNT IN DOLLAR', '', '', '']
                    
                    col = 0
                    for header in headers_row1:
                        if header:
                            worksheet.write(row, col, header, header_format)
                        col += 1
                    row += 1
                    col = 0
                    for header in headers_row2:
                        if header:
                            worksheet.write(row, col, header, header_format)
                        col += 1
                    row += 1
                    col = 0
                    for header in headers_row3:
                        if header:
                            worksheet.write(row, col, header, header_format)
                        col += 1
                    row += 1
                    
                    # Set column widths
                    worksheet.set_column(0, 0, 8)
                    worksheet.set_column(1, 1, 25)
                    worksheet.set_column(2, 13, 15)
                    
                    # Data rows
                    for data_row in report_data:
                        worksheet.write(row, 0, data_row.get('sno', ''), center_format)
                        worksheet.write(row, 1, data_row.get('item_name', ''), cell_format)
                        worksheet.write(row, 2, data_row.get('expected_customers', 0), number_format)
                        worksheet.write(row, 3, data_row.get('expected_amount_birr', 0), number_format)
                        worksheet.write(row, 4, data_row.get('expected_amount_dollar', 0), number_format)
                        worksheet.write(row, 5, data_row.get('penalty_customers', 0), number_format)
                        worksheet.write(row, 6, data_row.get('penalty_amount_birr', 0), number_format)
                        worksheet.write(row, 7, data_row.get('penalty_amount_dollar', 0), number_format)
                        worksheet.write(row, 8, data_row.get('termination_customers', 0), number_format)
                        worksheet.write(row, 9, data_row.get('termination_amount_birr', 0), number_format)
                        worksheet.write(row, 10, data_row.get('termination_amount_dollar', 0), number_format)
                        worksheet.write(row, 11, data_row.get('total_customers', 0), number_format)
                        worksheet.write(row, 12, data_row.get('total_amount_birr', 0), number_format)
                        worksheet.write(row, 13, data_row.get('total_amount_dollar', 0), number_format)
                        row += 1
                    
                    filename = f'plan_stage_report_{date_from or "all"}_{date_to or "all"}.xlsx'
                
                elif report_type == 'report_stage_report':
                    # Section title
                    worksheet.write(row, 0, section_title, section_format)
                    row += 2
                    
                    # Headers - multi-row
                    headers_row1 = ['S,NO', 'PROJECT NAME', 'EXPECTED', '', 'PENALITY', '', '', 'TERMINATION', '', 
                                    'OTHER COLLECTION', '', '', 'TOTAL COLLECTION REPORT', '', '']
                    headers_row2 = ['', '', 'NO OF CUSTOMERS', 'AMOUNT IN BIRR', 'NO OF CUSTOMERS', 'AMOUNT IN BIRR', 'AMOUNT IN DOLLAR',
                                    'NO OF CUSTOMERS', 'AMOUNT IN BIRR', 'NO OF CUSTOMERS', 'AMOUNT IN BIRR', 'AMOUNT IN DOLLAR',
                                    'NO OF CUSTOMERS', 'AMOUNT IN BIRR', 'AMOUNT IN DOLLAR']
                    
                    col = 0
                    for header in headers_row1:
                        if header:
                            worksheet.write(row, col, header, header_format)
                        col += 1
                    row += 1
                    col = 0
                    for header in headers_row2:
                        if header:
                            worksheet.write(row, col, header, header_format)
                        col += 1
                    row += 1
                    
                    # Set column widths
                    worksheet.set_column(0, 0, 8)
                    worksheet.set_column(1, 1, 25)
                    worksheet.set_column(2, 14, 15)
                    
                    # Data rows
                    for data_row in report_data:
                        if not data_row.get('is_total', False):
                            worksheet.write(row, 0, data_row.get('sno', ''), center_format)
                            worksheet.write(row, 1, data_row.get('project_name', ''), cell_format)
                            worksheet.write(row, 2, data_row.get('expected_customers', 0), number_format)
                            worksheet.write(row, 3, data_row.get('expected_amount_birr', 0), number_format)
                            worksheet.write(row, 4, data_row.get('penalty_customers', 0), number_format)
                            worksheet.write(row, 5, data_row.get('penalty_amount_birr', 0), number_format)
                            worksheet.write(row, 6, data_row.get('penalty_amount_dollar', 0), number_format)
                            worksheet.write(row, 7, data_row.get('termination_customers', 0), number_format)
                            worksheet.write(row, 8, data_row.get('termination_amount_birr', 0), number_format)
                            worksheet.write(row, 9, data_row.get('other_customers', 0), number_format)
                            worksheet.write(row, 10, data_row.get('other_amount_birr', 0), number_format)
                            worksheet.write(row, 11, data_row.get('other_amount_dollar', 0), number_format)
                            worksheet.write(row, 12, data_row.get('total_customers', 0), number_format)
                            worksheet.write(row, 13, data_row.get('total_amount_birr', 0), number_format)
                            worksheet.write(row, 14, data_row.get('total_amount_dollar', 0), number_format)
                            row += 1
                    
                    filename = f'report_stage_report_{date_from or "all"}_{date_to or "all"}.xlsx'
                
                elif report_type == 'summarized_report':
                    # Section title
                    worksheet.write(row, 0, section_title, section_format)
                    row += 2
                    
                    # Headers - multi-row (complex structure)
                    headers_row1 = ['S,NO', 'PROJECT NAME', 'COLLECTION PLAN', '', '', 'COLLECTION REPORT (EXECUTION)', '', '', 
                                    'OTHER COLLECTION', '', '', 'TOTAL COLLECTION (EXECUTION) REPORT(INCLUDING OTHER COLLECTION)', '', '',
                                    'PAYMENT EXTENSION', '', 'TOTAL AMOUNT REMAINED UNCOLLECTED', '', '',
                                    'COMMUNICATION REPORT', '', '', '', '', '', 'SEMI /PARTIAL PAID', '', '', '', '']
                    headers_row2 = ['', '', '', '', '', 'FROM PLAN', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
                    headers_row3 = ['', '', 'NUMBER OF CUSTOMERS', 'AMOUNT IN BIRR', 'AMOUNT IN DOLLAR',
                                    'NUMBER OF CUSTOMERS', 'AMOUNT IN BIRR', 'COLLECTION IN DOLLAR EQUVALENCE',
                                    'NUMBER OF CUSTOMERS', 'AMOUNT IN BIRR', 'COLLECTION OF IN DOLLAR EQUVALENCE',
                                    'NUMBER OF CUSTOMERS', 'AMOUNT IN BIRR', 'COLLECTION IN DOLLAR EQUVALENCE',
                                    'NUMBER OF CUSTOMERS', 'AMOUNT IN BIRR',
                                    'NUMBER OF CUSTOMERS', 'AMOUNT IN BIRR', 'COLLECTION IN DOLLAR EQUVALENCE',
                                    'TEXT', 'PHONE CALL', 'LETTER', 'COMMUNICATION DIFFICULTY', 'NUMBER OF CUSTOMERS OBTAINED SERVICE IN COLLEC',
                                    'S.NO', 'LETTER NOT DELIVERD TO CUSTOMER', 'NO OF CUSTOMER', 'AMOUNT IN BIRR', 'AMOUNT IN DOLLAR', 'REMARK']
                    
                    col = 0
                    for header in headers_row1:
                        if header:
                            worksheet.write(row, col, header, header_format)
                        col += 1
                    row += 1
                    col = 0
                    for header in headers_row2:
                        if header:
                            worksheet.write(row, col, header, header_format)
                        col += 1
                    row += 1
                    col = 0
                    for header in headers_row3:
                        if header:
                            worksheet.write(row, col, header, header_format)
                        col += 1
                    row += 1
                    
                    # Set column widths
                    worksheet.set_column(0, 0, 8)
                    worksheet.set_column(1, 1, 25)
                    worksheet.set_column(2, 30, 12)
                    
                    # Data rows
                    for data_row in report_data:
                        worksheet.write(row, 0, data_row.get('sno', ''), center_format)
                        worksheet.write(row, 1, data_row.get('project_name', ''), cell_format)
                        worksheet.write(row, 2, data_row.get('plan_customers', 0), number_format)
                        worksheet.write(row, 3, data_row.get('plan_amount_birr', 0), number_format)
                        worksheet.write(row, 4, data_row.get('plan_amount_dollar', 0), number_format)
                        worksheet.write(row, 5, data_row.get('execution_customers', 0), number_format)
                        worksheet.write(row, 6, data_row.get('execution_amount_birr', 0), number_format)
                        worksheet.write(row, 7, data_row.get('execution_amount_dollar', 0), number_format)
                        worksheet.write(row, 8, data_row.get('other_customers', 0), number_format)
                        worksheet.write(row, 9, data_row.get('other_amount_birr', 0), number_format)
                        worksheet.write(row, 10, data_row.get('other_amount_dollar', 0), number_format)
                        worksheet.write(row, 11, data_row.get('total_customers', 0), number_format)
                        worksheet.write(row, 12, data_row.get('total_amount_birr', 0), number_format)
                        worksheet.write(row, 13, data_row.get('total_amount_dollar', 0), number_format)
                        worksheet.write(row, 14, data_row.get('extension_customers', 0), number_format)
                        worksheet.write(row, 15, data_row.get('extension_amount_birr', 0), number_format)
                        worksheet.write(row, 16, data_row.get('remaining_customers', 0), number_format)
                        worksheet.write(row, 17, data_row.get('remaining_amount_birr', 0), number_format)
                        worksheet.write(row, 18, data_row.get('remaining_amount_dollar', 0), number_format)
                        worksheet.write(row, 19, data_row.get('comm_text', 0), number_format)
                        worksheet.write(row, 20, data_row.get('comm_phone', 0), number_format)
                        worksheet.write(row, 21, data_row.get('comm_letter', 0), number_format)
                        worksheet.write(row, 22, data_row.get('comm_difficulty', 0), number_format)
                        worksheet.write(row, 23, data_row.get('comm_service_customers', 0), number_format)
                        worksheet.write(row, 24, data_row.get('comm_sno', ''), center_format)
                        worksheet.write(row, 25, data_row.get('partial_letter_not_delivered', 0), number_format)
                        worksheet.write(row, 26, data_row.get('partial_customers', 0), number_format)
                        worksheet.write(row, 27, data_row.get('partial_amount_birr', 0), number_format)
                        worksheet.write(row, 28, data_row.get('partial_amount_dollar', 0), number_format)
                        worksheet.write(row, 29, data_row.get('partial_remark', ''), cell_format)
                        row += 1
                    
                    # Total row
                    worksheet.write(row, 0, 'TOTAL SUM', header_format)
                    worksheet.write(row, 1, '', cell_format)
                    worksheet.write(row, 2, totals.get('plan_customers', 0), number_format)
                    worksheet.write(row, 3, totals.get('plan_amount_birr', 0), number_format)
                    worksheet.write(row, 4, totals.get('plan_amount_dollar', 0), number_format)
                    worksheet.write(row, 5, totals.get('execution_customers', 0), number_format)
                    worksheet.write(row, 6, totals.get('execution_amount_birr', 0), number_format)
                    worksheet.write(row, 7, totals.get('execution_amount_dollar', 0), number_format)
                    worksheet.write(row, 8, totals.get('other_customers', 0), number_format)
                    worksheet.write(row, 9, totals.get('other_amount_birr', 0), number_format)
                    worksheet.write(row, 10, totals.get('other_amount_dollar', 0), number_format)
                    worksheet.write(row, 11, totals.get('total_customers', 0), number_format)
                    worksheet.write(row, 12, totals.get('total_amount_birr', 0), number_format)
                    worksheet.write(row, 13, totals.get('total_amount_dollar', 0), number_format)
                    worksheet.write(row, 14, totals.get('extension_customers', 0), number_format)
                    worksheet.write(row, 15, totals.get('extension_amount_birr', 0), number_format)
                    worksheet.write(row, 16, totals.get('remaining_customers', 0), number_format)
                    worksheet.write(row, 17, totals.get('remaining_amount_birr', 0), number_format)
                    worksheet.write(row, 18, totals.get('remaining_amount_dollar', 0), number_format)
                    worksheet.write(row, 19, totals.get('comm_text', 0), number_format)
                    worksheet.write(row, 20, totals.get('comm_phone', 0), number_format)
                    worksheet.write(row, 21, totals.get('comm_letter', 0), number_format)
                    worksheet.write(row, 22, totals.get('comm_difficulty', 0), number_format)
                    worksheet.write(row, 23, totals.get('comm_service_customers', 0), number_format)
                    worksheet.write(row, 24, '', cell_format)
                    worksheet.write(row, 25, totals.get('partial_letter_not_delivered', 0), number_format)
                    worksheet.write(row, 26, totals.get('partial_customers', 0), number_format)
                    worksheet.write(row, 27, totals.get('partial_amount_birr', 0), number_format)
                    worksheet.write(row, 28, totals.get('partial_amount_dollar', 0), number_format)
                    worksheet.write(row, 29, '', cell_format)
                    
                    filename = f'summarized_report_{date_from or "all"}_{date_to or "all"}.xlsx'
                
                workbook.close()
                output.seek(0)
                excel_content = output.getvalue()
                output.close()
                
                response = Response(
                    excel_content,
                    headers=[
                        ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                        ('Content-Disposition', f'attachment; filename="{filename}"'),
                    ]
                )
                return response
            else:
                # Fallback to CSV if xlsxwriter not available
                import csv
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Write headers matching the EXACT image format
                full_title = f"TEMER PROPERTIES COLLECTION DEPARTMENT MONTHLY REPORT SUMMARY {date_period}"
                writer.writerow([full_title])
                writer.writerow([])
                
                if report_type == 'general_info':
                    writer.writerow([section_title])
                    writer.writerow([])
                    writer.writerow(['S,NO', 'SITE', 'PROJECT NAME', 'TOTAL STOCK', 'SOLD STOCK', 
                                    'ACTIVE IN MASTER DOCUMENT', 'ACTIVE IN COLLECTION', 'MERGED CONTRACT',
                                    'SITE SHIFT', 'FULLY PAID (100%)', 'DHL NUMBER', 'PAYMENT ROUND NUMBER',
                                    'REFUND', 'CONTRACT/NOT COMPLETE', 'INCOME CONTRACT'])
                    for data_row in report_data:
                        writer.writerow([
                            data_row.get('sno', ''),
                            data_row.get('site_name', '') or data_row.get('project_name', ''),
                            data_row.get('project_name', ''),
                            data_row.get('total_stock', 0),
                            data_row.get('sold_stock', 0),
                            data_row.get('active_master_document', 0),
                            data_row.get('active_collection', 0),
                            data_row.get('merged_contract', 0),
                            data_row.get('site_shift', 0),
                            data_row.get('fully_paid', 0),
                            data_row.get('dhl_number', ''),
                            data_row.get('payment_round_number', 0),
                            data_row.get('refund', 0),
                            data_row.get('contract_not_complete', 0),
                            data_row.get('income_contract', 0),
                        ])
                    writer.writerow(['TOTAL', '', '', 
                                    totals.get('total_stock', 0),
                                    totals.get('sold_stock', 0),
                                    totals.get('active_master_document', 0),
                                    totals.get('active_collection', 0),
                                    totals.get('merged_contract', 0),
                                    totals.get('site_shift', 0),
                                    totals.get('fully_paid', 0),
                                    '',
                                    totals.get('payment_round_number', 0),
                                    totals.get('refund', 0),
                                    totals.get('contract_not_complete', 0),
                                    totals.get('income_contract', 0),
                    ])
                    filename = f'general_info_report_{date_from or "all"}_{date_to or "all"}.csv'
                # Add other report types CSV fallback as needed
                
                output.seek(0)
                csv_content = output.getvalue()
                output.close()
                
                response = Response(
                    csv_content.encode('utf-8-sig'),
                    headers=[
                        ('Content-Type', 'text/csv; charset=utf-8-sig'),
                        ('Content-Disposition', f'attachment; filename="{filename}"'),
                    ]
                )
                return response
        except Exception as e:
            _logger.error(f"Error exporting Excel: {str(e)}", exc_info=True)
            return request.not_found()

    @http.route('/collection_reports/api/export_pdf', type='http', auth='user', methods=['POST'], csrf=False)
    def api_export_pdf(self, **kwargs):
        """Export report to PDF"""
        try:
            report_type = kwargs.get('report_type', 'general_info')
            site_id = kwargs.get('site_id')
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            
            # Get report data by calling the appropriate API method
            if report_type == 'general_info':
                params = {
                    'site_id': site_id,
                    'date_from': date_from if date_from else None,
                    'date_to': date_to if date_to else None,
                }
                result = self.api_general_info(params=params)
            elif report_type == 'summarized_report':
                params = {
                    'date_from': date_from if date_from else None,
                    'date_to': date_to if date_to else None,
                }
                result = self.api_summarized_report(params=params)
            else:
                return request.not_found("Invalid report type")
            
            if not result.get('success'):
                return request.not_found(f"Error generating report: {result.get('error', 'Unknown error')}")
            
            report_data = result.get('data', [])
            totals = result.get('totals', {})
            
            # Generate PDF using weasyprint
            pdf_content = None
            try:
                import weasyprint
                from io import BytesIO
                html_content = self._generate_pdf_html(report_type, report_data, totals, site_id, date_from, date_to)
                pdf_file = BytesIO()
                weasyprint.HTML(string=html_content, base_url=request.httprequest.host_url).write_pdf(pdf_file)
                pdf_content = pdf_file.getvalue()
                pdf_file.close()
                if pdf_content and len(pdf_content) > 100:
                    _logger.info(f"PDF generated successfully using weasyprint ({len(pdf_content)} bytes)")
                else:
                    pdf_content = None
            except ImportError:
                _logger.error("weasyprint not available. Trying to install...")
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "weasyprint"], 
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    _logger.info("weasyprint installed, retrying PDF generation...")
                    html_content = self._generate_pdf_html(report_type, report_data, totals, site_id, date_from, date_to)
                    pdf_file = BytesIO()
                    weasyprint.HTML(string=html_content, base_url=request.httprequest.host_url).write_pdf(pdf_file)
                    pdf_content = pdf_file.getvalue()
                    pdf_file.close()
                    if pdf_content and len(pdf_content) > 100:
                        _logger.info("PDF generated successfully after weasyprint installation")
                    else:
                        pdf_content = None
                except Exception as install_error:
                    _logger.error(f"Failed to install weasyprint: {str(install_error)}")
                    pdf_content = None
            except Exception as e:
                _logger.error(f"Error with weasyprint: {str(e)}", exc_info=True)
                pdf_content = None
            
            # Return PDF if generated
            if pdf_content and isinstance(pdf_content, bytes) and len(pdf_content) > 100:
                filename = f'{report_type}_{date_from or "all"}_{date_to or "all"}.pdf'
                return request.make_response(
                    pdf_content,
                    headers=[
                        ('Content-Type', 'application/pdf'),
                        ('Content-Disposition', f'attachment; filename="{filename}"'),
                    ]
                )
            else:
                error_msg = "PDF generation failed. Please ensure weasyprint is installed: pip install weasyprint"
                _logger.error(error_msg)
                return request.make_response(
                    error_msg.encode('utf-8'),
                    headers=[
                        ('Content-Type', 'text/plain'),
                        ('Content-Disposition', 'inline'),
                    ]
                )
        except Exception as e:
            _logger.error(f"Error exporting PDF: {str(e)}", exc_info=True)
            return request.not_found()
    
    def _generate_pdf_html(self, report_type, report_data, totals, site_id=None, date_from=None, date_to=None):
        """Generate HTML content for PDF"""
        if report_type == 'general_info':
            return self._generate_general_info_pdf_html(report_data, totals, site_id, date_from, date_to)
        elif report_type == 'summarized_report':
            return self._generate_summarized_pdf_html(report_data, totals, date_from, date_to)
        else:
            return "<html><body>Invalid report type</body></html>"
    
    def _generate_general_info_pdf_html(self, report_data, totals, site_id, date_from, date_to):
        """Generate HTML for General Info Report PDF"""
        site_name = ''
        if site_id:
            try:
                site = request.env['property.site'].browse(int(site_id))
                if site.exists():
                    site_name = site.name
            except:
                pass
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; font-size: 10px; }}
                h1 {{ color: #333; text-align: center; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 9px; }}
                th, td {{ border: 1px solid #ddd; padding: 4px; text-align: left; }}
                th {{ background-color: #f2f2f2; font-weight: bold; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .metric {{ font-weight: bold; }}
                .total-row {{ background-color: #e8f4f8; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>General Information Report</h1>
            <div style="margin-bottom: 20px;">
                {f'<p style="margin: 5px 0;"><strong>Site:</strong> {site_name}</p>' if site_name else '<p style="margin: 5px 0;"><strong>Site:</strong> All Sites</p>'}
                <p style="margin: 5px 0;"><strong>Date Range:</strong> {date_from or 'All'} to {date_to or 'All'}</p>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>S.NO</th>
                        <th>SITE</th>
                        <th>PROJECT NAME</th>
                        <th>TOTAL STOCK</th>
                        <th>SOLD STOCK</th>
                        <th>ACTIVE IN MASTER DOCUMENT</th>
                        <th>ACTIVE IN COLLECTION</th>
                        <th>MERGED CONTRACT</th>
                        <th>SITE SHIFT</th>
                        <th>FULLY PAID (100%)</th>
                        <th>DHL NUMBER</th>
                        <th>PAYMENT ROUND NUMBER</th>
                        <th>REFUND</th>
                        <th>CONTRACT/NOT COMPLETE</th>
                        <th>INCOME CONTRACT</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for row in report_data:
            html += f"""
                    <tr>
                        <td>{row.get('sno', '')}</td>
                        <td>{row.get('site_name', '')}</td>
                        <td>{row.get('project_name', '')}</td>
                        <td>{row.get('total_stock', 0)}</td>
                        <td>{row.get('sold_stock', 0)}</td>
                        <td>{row.get('active_master_document', 0)}</td>
                        <td>{row.get('active_collection', 0)}</td>
                        <td>{row.get('merged_contract', 0)}</td>
                        <td>{row.get('site_shift', 0)}</td>
                        <td>{row.get('fully_paid', 0)}</td>
                        <td>{row.get('dhl_number', '')}</td>
                        <td>{row.get('payment_round_number', 0)}</td>
                        <td>{row.get('refund', 0)}</td>
                        <td>{row.get('contract_not_complete', 0)}</td>
                        <td>{row.get('income_contract', 0)}</td>
                    </tr>
            """
        
        html += f"""
                    <tr class="total-row">
                        <td><strong>TOTAL</strong></td>
                        <td></td>
                        <td></td>
                        <td>{totals.get('total_stock', 0)}</td>
                        <td>{totals.get('sold_stock', 0)}</td>
                        <td>{totals.get('active_master_document', 0)}</td>
                        <td>{totals.get('active_collection', 0)}</td>
                        <td>{totals.get('merged_contract', 0)}</td>
                        <td>{totals.get('site_shift', 0)}</td>
                        <td>{totals.get('fully_paid', 0)}</td>
                        <td></td>
                        <td>{totals.get('payment_round_number', 0)}</td>
                        <td>{totals.get('refund', 0)}</td>
                        <td>{totals.get('contract_not_complete', 0)}</td>
                        <td>{totals.get('income_contract', 0)}</td>
                    </tr>
                </tbody>
            </table>
        </body>
        </html>
        """
        return html
    
    def _generate_summarized_pdf_html(self, report_data, totals, date_from, date_to):
        """Generate HTML for Summarized Report PDF"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 10px; font-size: 8px; }}
                h1 {{ color: #333; text-align: center; font-size: 14px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 7px; }}
                th, td {{ border: 1px solid #ddd; padding: 3px; text-align: left; }}
                th {{ background-color: #f2f2f2; font-weight: bold; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .total-row {{ background-color: #e8f4f8; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>Summarized Report</h1>
            <div style="margin-bottom: 10px;">
                <p style="margin: 3px 0;"><strong>Date Range:</strong> {date_from or 'All'} to {date_to or 'All'}</p>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>S.NO</th>
                        <th>PROJECT</th>
                        <th>PLAN-Cust</th>
                        <th>PLAN-Birr</th>
                        <th>PLAN-USD</th>
                        <th>EXEC-Cust</th>
                        <th>EXEC-Birr</th>
                        <th>EXEC-USD</th>
                        <th>OTHER-Cust</th>
                        <th>OTHER-Birr</th>
                        <th>OTHER-USD</th>
                        <th>TOTAL-Cust</th>
                        <th>TOTAL-Birr</th>
                        <th>TOTAL-USD</th>
                        <th>EXT-Cust</th>
                        <th>EXT-Birr</th>
                        <th>REM-Cust</th>
                        <th>REM-Birr</th>
                        <th>REM-USD</th>
                        <th>PART-Cust</th>
                        <th>PART-Birr</th>
                        <th>PART-USD</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for row in report_data:
            html += f"""
                    <tr>
                        <td>{row.get('sno', '')}</td>
                        <td>{row.get('project_name', '')}</td>
                        <td>{row.get('plan_customers', 0)}</td>
                        <td>{row.get('plan_amount_birr', 0):,.2f} Birr</td>
                        <td>${row.get('plan_amount_dollar', 0):,.2f}</td>
                        <td>{row.get('execution_customers', 0)}</td>
                        <td>{row.get('execution_amount_birr', 0):,.2f} Birr</td>
                        <td>${row.get('execution_amount_dollar', 0):,.2f}</td>
                        <td>{row.get('other_customers', 0)}</td>
                        <td>{row.get('other_amount_birr', 0):,.2f} Birr</td>
                        <td>${row.get('other_amount_dollar', 0):,.2f}</td>
                        <td>{row.get('total_customers', 0)}</td>
                        <td>{row.get('total_amount_birr', 0):,.2f} Birr</td>
                        <td>${row.get('total_amount_dollar', 0):,.2f}</td>
                        <td>{row.get('extension_customers', 0)}</td>
                        <td>{row.get('extension_amount_birr', 0):,.2f} Birr</td>
                        <td>{row.get('remaining_customers', 0)}</td>
                        <td>{row.get('remaining_amount_birr', 0):,.2f} Birr</td>
                        <td>${row.get('remaining_amount_dollar', 0):,.2f}</td>
                        <td>{row.get('partial_customers', 0)}</td>
                        <td>{row.get('partial_amount_birr', 0):,.2f} Birr</td>
                        <td>${row.get('partial_amount_dollar', 0):,.2f}</td>
                    </tr>
            """
        
        html += f"""
                    <tr class="total-row">
                        <td><strong>TOTAL</strong></td>
                        <td></td>
                        <td>{totals.get('plan_customers', 0)}</td>
                        <td>{totals.get('plan_amount_birr', 0):,.2f} Birr</td>
                        <td>${totals.get('plan_amount_dollar', 0):,.2f}</td>
                        <td>{totals.get('execution_customers', 0)}</td>
                        <td>{totals.get('execution_amount_birr', 0):,.2f} Birr</td>
                        <td>${totals.get('execution_amount_dollar', 0):,.2f}</td>
                        <td>{totals.get('other_customers', 0)}</td>
                        <td>{totals.get('other_amount_birr', 0):,.2f} Birr</td>
                        <td>${totals.get('other_amount_dollar', 0):,.2f}</td>
                        <td>{totals.get('total_customers', 0)}</td>
                        <td>{totals.get('total_amount_birr', 0):,.2f} Birr</td>
                        <td>${totals.get('total_amount_dollar', 0):,.2f}</td>
                        <td>{totals.get('extension_customers', 0)}</td>
                        <td>{totals.get('extension_amount_birr', 0):,.2f} Birr</td>
                        <td>{totals.get('remaining_customers', 0)}</td>
                        <td>{totals.get('remaining_amount_birr', 0):,.2f} Birr</td>
                        <td>${totals.get('remaining_amount_dollar', 0):,.2f}</td>
                        <td>{totals.get('partial_customers', 0)}</td>
                        <td>{totals.get('partial_amount_birr', 0):,.2f} Birr</td>
                        <td>${totals.get('partial_amount_dollar', 0):,.2f}</td>
                    </tr>
                </tbody>
            </table>
        </body>
        </html>
        """
        return html

    # Additional methods merged from collection_report_2
    @http.route('/collection_reports/api/collection_stage', type='json', auth='user', methods=['POST'], csrf=False)
    def api_collection_stage(self, **kwargs):
        """API endpoint for Collection Stage Report - delegates to api_report_stage_report"""
        try:
            result = self.api_report_stage_report(**kwargs)
            # Ensure result has all required fields
            if not isinstance(result, dict):
                return {'success': False, 'error': 'Invalid response format', 'data': [], 'totals': {}}
            if 'success' not in result:
                result['success'] = True
            if 'data' not in result:
                result['data'] = []
            if 'totals' not in result:
                result['totals'] = {}
            return result
        except Exception as e:
            _logger.error(f"Error in collection_stage API: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e), 'data': [], 'totals': {}}

    @http.route('/collection_reports/api/actual_paid', type='json', auth='user', methods=['POST'], csrf=False)
    def api_actual_paid(self, **kwargs):
        """API endpoint for Actual Paid Report - delegates to api_summarized_report"""
        try:
            result = self.api_summarized_report(**kwargs)
            # Ensure result has all required fields
            if not isinstance(result, dict):
                return {'success': False, 'error': 'Invalid response format', 'data': [], 'totals': {}}
            if 'success' not in result:
                result['success'] = True
            if 'data' not in result:
                result['data'] = []
            if 'totals' not in result:
                result['totals'] = {}
            return result
        except Exception as e:
            _logger.error(f"Error in actual_paid API: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e), 'data': [], 'totals': {}}

    @http.route('/collection_reports/api/communication', type='json', auth='user', methods=['POST'], csrf=False)
    def api_communication(self, **kwargs):
        """API endpoint for Communication Report"""
        try:
            params = kwargs.get('params', {}) if isinstance(kwargs.get('params'), dict) else kwargs
            date_from = params.get('date_from') or kwargs.get('date_from')
            date_to = params.get('date_to') or kwargs.get('date_to')
            return {'success': True, 'data': [], 'totals': {}}
        except Exception as e:
            _logger.error(f"Error in communication report: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e), 'data': [], 'totals': {}}

    @http.route('/collection_reports/api/customer_service', type='json', auth='user', methods=['POST'], csrf=False)
    def api_customer_service(self, **kwargs):
        """API endpoint for Customer Service Report"""
        try:
            params = kwargs.get('params', {}) if isinstance(kwargs.get('params'), dict) else kwargs
            date_from = params.get('date_from') or kwargs.get('date_from')
            date_to = params.get('date_to') or kwargs.get('date_to')
            domain = []
            if date_from:
                try:
                    date_from_obj = fields.Date.from_string(date_from)
                    domain.append(('date', '>=', date_from_obj))
                except:
                    pass
            if date_to:
                try:
                    date_to_obj = fields.Date.from_string(date_to)
                    domain.append(('date', '<=', date_to_obj))
                except:
                    pass
            customer_services = request.env['collection.customer.service'].search(domain)
            report_data = []
            for cs in customer_services:
                report_data.append({
                    'sno': len(report_data) + 1,
                    'date': cs.date.strftime('%Y-%m-%d') if cs.date else '',
                    'customer': cs.partner_id.name if cs.partner_id else '',
                    'collection_order': cs.collection_id.name if cs.collection_id else '',
                    'total_customers': cs.total_customers,
                    'satisfaction_level': dict(cs._fields['satisfaction_level'].selection).get(cs.satisfaction_level, ''),
                    'remark': cs.remark or '',
                })
            return {'success': True, 'data': report_data, 'totals': {'total_customers': sum(cs.total_customers for cs in customer_services)}}
        except Exception as e:
            _logger.error(f"Error in customer service report: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e), 'data': [], 'totals': {}}

    def _get_date_range(self, period_type, date_from_str=None, date_to_str=None):
        """Calculate date range based on period type"""
        from datetime import datetime, timedelta
        today = fields.Date.today()
        if period_type == 'daily':
            date_from = today
            date_to = today
        elif period_type == 'monthly':
            first_day = today.replace(day=1) - timedelta(days=1)
            date_from = first_day.replace(day=1)
            date_to = first_day
        elif period_type == 'yearly':
            date_from = today.replace(year=today.year - 1, month=1, day=1)
            date_to = today.replace(year=today.year - 1, month=12, day=31)
        elif period_type == 'all':
            date_from = today.replace(year=today.year - 10, month=1, day=1)
            date_to = today
        else:
            try:
                date_from = fields.Date.from_string(date_from_str) if date_from_str else today
                date_to = fields.Date.from_string(date_to_str) if date_to_str else today
            except:
                date_from = today
                date_to = today
        return date_from, date_to

    @http.route('/collection_reports/api/collection_plan', type='json', auth='user', methods=['POST'], csrf=False)
    def api_collection_plan(self, **kwargs):
        """API endpoint for Plan for Collection report"""
        try:
            period_type = kwargs.get('period_type', 'daily')
            date_from_str = kwargs.get('date_from')
            date_to_str = kwargs.get('date_to')
            date_from, date_to = self._get_date_range(period_type, date_from_str, date_to_str)
            from datetime import datetime, time
            date_from_dt = datetime.combine(date_from, time.min)
            date_to_dt = datetime.combine(date_to, time.max)
            env = request.env
            total_clients = env['res.partner'].sudo().search_count([('is_company', '=', False), ('customer_rank', '>', 0)])
            no_of_sites = 0
            if 'property.site' in env:
                no_of_sites = env['property.site'].sudo().search_count([])
            stock_residences = 0
            if 'collection.order' in env and 'property.property' in env and 'property.sale' in env:
                collection_orders = env['collection.order'].sudo().search([('state', 'in', ['draft', 'active', 'completed']), ('sale_id.order_date', '>=', date_from), ('sale_id.order_date', '<=', date_to)])
                property_ids = collection_orders.mapped('property_id.id')
                if property_ids:
                    stock_residences = env['property.property'].sudo().search_count([('id', 'in', property_ids), ('property_type', '=', 'residential'), ('state', '=', 'sold')])
            stock_shops = 0
            if 'collection.order' in env and 'property.property' in env and 'property.sale' in env:
                collection_orders = env['collection.order'].sudo().search([('state', 'in', ['draft', 'active', 'completed']), ('sale_id.order_date', '>=', date_from), ('sale_id.order_date', '<=', date_to)])
                property_ids = collection_orders.mapped('property_id.id')
                if property_ids:
                    stock_shops = env['property.property'].sudo().search_count([('id', 'in', property_ids), ('property_type', '=', 'commercial'), ('state', '=', 'sold')])
            stock_mixed_use = 0
            if 'collection.order' in env and 'property.property' in env and 'property.sale' in env:
                collection_orders = env['collection.order'].sudo().search([('state', 'in', ['draft', 'active', 'completed']), ('sale_id.order_date', '>=', date_from), ('sale_id.order_date', '<=', date_to)])
                property_ids = collection_orders.mapped('property_id.id')
                if property_ids:
                    stock_mixed_use = env['property.property'].sudo().search_count([
                        ('id', 'in', property_ids),
                        ('property_type', 'in', ['mixed_use', 'mixed']),
                        ('state', '=', 'sold')
                    ])
            total_receivable = 0.0
            if 'collection.order' in env:
                collection_orders = env['collection.order'].sudo().search([('state', 'in', ['draft', 'active'])])
                total_receivable = sum(collection_orders.mapped('amount_remaining') or [0])
            collected_amount_actual = 0.0
            collected_clients_actual = 0
            if 'collection.installment.payment' in env:
                payments = env['collection.installment.payment'].sudo().search([('payment_date', '>=', date_from), ('payment_date', '<=', date_to), ('status', '=', 'paid')])
                collected_amount_actual = sum(payments.mapped('amount') or [0])
                collected_clients_actual = len(set(payments.mapped('installment_id.collection_id.partner_id.id')))
            collected_amount_plan = 0.0
            collected_clients_plan = 0
            if 'collection.plan.stage' in env:
                plan_domain = [('active', '=', True), ('date_to', '>=', date_from), ('date_from', '<=', date_to)]
                collection_plans = env['collection.plan.stage'].sudo().search(plan_domain)
                collected_amount_plan = sum(collection_plans.mapped('plan_amount_birr') or [0])
                collected_clients_plan = sum(collection_plans.mapped('plan_customers') or [0])
            collected_amount_achievement = 0.0
            if collected_amount_plan > 0:
                collected_amount_achievement = (collected_amount_actual / collected_amount_plan) * 100
            collected_clients_achievement = 0.0
            if collected_clients_plan > 0:
                collected_clients_achievement = (collected_clients_actual / collected_clients_plan) * 100
            discount_amount = 0.0
            discount_percentage = 0.0
            if 'collection.installment' in env:
                installments = env['collection.installment'].sudo().search([('create_date', '>=', date_from_dt), ('create_date', '<=', date_to_dt)])
                discount_amount = sum(installments.mapped('discount_amount') or [0])
                
                # Calculate discount percentage based on total sold properties value (not total_receivable)
                total_sold_properties_value = 0.0
                if 'property.sale' in env:
                    sales_domain = [
                        ('state', 'in', ['signed', 'contract', 'confirmed', 'sold', 'confirm']),
                        ('create_date', '>=', date_from_dt),
                        ('create_date', '<=', date_to_dt)
                    ]
                    sales = env['property.sale'].sudo().search(sales_domain)
                    # Use sale_price instead of total_price
                    total_sold_properties_value = sum(sale.sale_price or 0.0 for sale in sales if hasattr(sale, 'sale_price'))
                
                if total_sold_properties_value > 0:
                    discount_percentage = (discount_amount / total_sold_properties_value) * 100
            return {'success': True, 'data': {'total_clients': total_clients, 'no_of_sites': no_of_sites, 'stock_residences': stock_residences, 'stock_shops': stock_shops, 'stock_mixed_use': stock_mixed_use, 'total_receivable': total_receivable, 'collected_amount_plan': collected_amount_plan, 'collected_amount_actual': collected_amount_actual, 'collected_amount_achievement': collected_amount_achievement, 'collected_clients_plan': collected_clients_plan, 'collected_clients_actual': collected_clients_actual, 'collected_clients_achievement': collected_clients_achievement, 'discount_amount': discount_amount, 'discount_percentage': discount_percentage}}
        except Exception as e:
            _logger.error(f"Error in api_collection_plan: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

