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
        The device sends its Serial Number (SN) in the URL parameters.
        """
        sn = kwargs.get('SN')
        if not sn:
            return "ERROR: No Serial Number provided\n"

        # Find the machine in Odoo using the Serial Number
        machine = request.env['biometric.config'].sudo().search([('serial_number', '=', sn)], limit=1)
        if not machine:
            _logger.warning(f"ADMS Request from Unknown Device SN: {sn}")
            return "ERROR: Unknown Device\n"

        # The device sends a GET request to initialize or check for pending commands
        if request.httprequest.method == 'GET':
            return "OK\n"

        # The device sends a POST request to push Attendance Data
        if request.httprequest.method == 'POST':
            raw_data = request.httprequest.data.decode('utf-8')
            
            # The data looks like: 101\t2026-09-03 14:30:00\t0\t1\n
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
                        # Localize to machine's timezone, then convert to UTC for Odoo
                        local_dt = local_tz.localize(local_dt_naive, is_dst=None)
                        utc_dt = local_dt.astimezone(pytz.utc).replace(tzinfo=None)

                        logs_to_create.append({
                            'bio_id': bio_id,
                            'machine_id': machine.id,
                            'timestamp': utc_dt,
                            'read_by': bot_user,
                        })
                    except Exception as e:
                        _logger.error(f"ADMS Parse Error for SN {sn}: {e} on line {line}")

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