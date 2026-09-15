import pytz
import logging
from datetime import datetime
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class ADMSController(http.Controller):

    @http.route(['/iclock/cdata', '/iclock/getrequest', '/iclock/devicecmd'], type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def iclock_endpoint(self, **kwargs):
        """ 
        The ZKTeco ADMS Endpoint. 
        """
        endpoint = request.httprequest.path
        method = request.httprequest.method
        sn = kwargs.get('SN')


        if not sn:
            _logger.warning("ERROR: ADMS Request received without SN (Serial Number) parameter.")
            return "ERROR: No Serial Number provided\n"

        # Find the machine in Odoo using the Serial Number
        machine = request.env['biometric.config'].sudo().search([('serial_number', '=', sn)], limit=1)
        if not machine:
            _logger.warning(f"ERROR: ADMS Request from Unknown Device SN: {sn}")
            return "ERROR: Unknown Device\n"

        if method == 'GET':
            return "OK\n"


        if method == 'POST':
            raw_data = request.httprequest.data.decode('utf-8', errors='ignore')

            # Only process attendance records (table=ATTLOG or missing table param depending on firmware)
            table_name = kwargs.get('table', 'ATTLOG')

            if endpoint == '/iclock/cdata' and table_name == 'ATTLOG':
                
                lines = raw_data.strip().split('\n')
                logs_to_create = []
                local_tz = pytz.timezone(machine.time_zone or 'GMT')
                bot_user = request.env.ref('base.user_root').id

                for line in lines:
                    if not line.strip():
                        continue
                    
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        bio_id = parts[0].strip()
                        timestamp_str = parts[1].strip()

                        try:
                            # Convert string to datetime
                            local_dt_naive = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            local_dt = local_tz.localize(local_dt_naive, is_dst=None)
                            utc_dt = local_dt.astimezone(pytz.utc).replace(tzinfo=None)

                            logs_to_create.append({
                                'bio_id': bio_id,
                                'machine_id': machine.id,
                                'timestamp': utc_dt,
                                'read_by': bot_user,
                            })
                        except Exception as e:
                            _logger.error(f"ADMS Parse Error for SN {sn}: {e} on line: {line}")

                if logs_to_create:
                    request.env['attendance.log.analysis'].sudo().create(logs_to_create)
                    
                    # Update Last Read Time
                    last_timestamp = logs_to_create[-1]['timestamp']
                    last_read = request.env['attendance.last.read'].sudo().search([('machine_id', '=', machine.id)], limit=1)
                    if last_read:
                        last_read.write({'last_read_time': last_timestamp})
                    else:
                        request.env['attendance.last.read'].sudo().create({
                            'machine_id': machine.id,
                            'last_read_time': last_timestamp
                        })

            return "OK\n"