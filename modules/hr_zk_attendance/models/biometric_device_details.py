# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Ammu Raj (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
import datetime
import logging
import pytz
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)
try:
    from zk import ZK, const
except ImportError:
    _logger.error("Please Install pyzk library.")


class BiometricDeviceDetails(models.Model):
    """Model for configuring and connect the biometric device with odoo"""
    _name = 'biometric.device.details'
    _description = 'Biometric Device Details'

    name = fields.Char(string='Name', required=True, help='Record Name')
    device_ip = fields.Char(string='Device IP', required=True,
                            help='The IP address of the Device')
    port_number = fields.Integer(string='Port Number', required=True,
                                 help="The Port Number of the Device")
    address_id = fields.Many2one('res.partner', string='Working Address',
                                 help='Working address of the partner')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda
                                     self: self.env.user.company_id.id,
                                 help='Current Company')

    def device_connect(self, zk):
        """Function for connecting the device with Odoo"""
        try:
            conn = zk.connect()
            return conn
        except Exception:
            return False

    def action_test_connection(self):
        """Checking the connection status"""
        zk = ZK(self.device_ip, port=self.port_number, timeout=30,
                password=False, ommit_ping=False)
        try:
            if zk.connect():
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Successfully Connected',
                        'type': 'success',
                        'sticky': False
                    }
                }
        except Exception as error:
            raise ValidationError(f'{error}')

    def action_set_timezone(self):
        """Function to set user's timezone to device"""
        for info in self:
            machine_ip = info.device_ip
            zk_port = info.port_number
            try:
                # Connecting with the device with the ip and port provided
                zk = ZK(machine_ip, port=zk_port, timeout=15,
                        password=0,
                        force_udp=False, ommit_ping=False)
            except NameError:
                raise UserError(
                    _("Pyzk module not Found. Please install it"
                      "with 'pip3 install pyzk'."))
            conn = self.device_connect(zk)
            if conn:
                user_tz = self.env.context.get(
                    'tz') or self.env.user.tz or 'UTC'
                user_timezone_time = pytz.utc.localize(fields.Datetime.now())
                user_timezone_time = user_timezone_time.astimezone(
                    pytz.timezone(user_tz))
                conn.set_time(user_timezone_time)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Successfully Set the Time',
                        'type': 'success',
                        'sticky': False
                    }
                }
            else:
                raise UserError(_(
                    "Please Check the Connection"))

    def action_clear_attendance(self):
        """Methode to clear record from the zk.machine.attendance model and
        from the device"""
        for info in self:
            try:
                machine_ip = info.device_ip
                zk_port = info.port_number
                try:
                    # Connecting with the device
                    zk = ZK(machine_ip, port=zk_port, timeout=30,
                            password=0, force_udp=False, ommit_ping=False)
                except NameError:
                    raise UserError(_(
                        "Please install it with 'pip3 install pyzk'."))
                conn = self.device_connect(zk)
                if conn:
                    conn.enable_device()
                    clear_data = zk.get_attendance()
                    if clear_data:
                        # Clearing data in the device
                        conn.clear_attendance()
                        # Clearing data from attendance log
                        self._cr.execute(
                            """delete from zk_machine_attendance""")
                        conn.disconnect()
                    else:
                        raise UserError(
                            _('Unable to clear Attendance log.Are you sure '
                              'attendance log is not empty.'))
                else:
                    raise UserError(
                        _('Unable to connect to Attendance Device. Please use '
                          'Test Connection button to verify.'))
            except Exception as error:
                raise ValidationError(f'{error}')

    def run_next_execution(self, machine):
        order = 'id asc'
        next_machines = self.env['biometric.device.details'].search([], order=order).sorted(lambda rec: rec.id)
        next_machines = list(next_machines)
        if len(next_machines) > 0:
            next_machine_ids = [next_machine.id for next_machine in next_machines]
            machine_index = next_machine_ids.index(machine.id)
            try:
                next_machine = next_machines[machine_index + 1]
                next_machine.write({
                    'is_next_execution': True
                })
            except IndexError :
                next_machine = next_machines[0]
                next_machine.write({
                    'is_next_execution': True
                })
        machine.write({
            'is_next_execution': False
        })

    @api.model
    def cron_download(self):
        # machines = self.env['biometric.device.details'].search([('is_next_execution', '=', True)])
        # machines = list(machines)
        # if len(machines) > 0:
        #     for machine in machines:
        machine = self.env['biometric.device.details'].search([('is_next_execution', '=', True)], limit=1)
        if machine:
            try:
                machine.action_download_attendance()
            except UserError as error:
                _logger.info(f'----------- tititititititi UserError {error} -----------')
            except ValidationError as error:
                _logger.info(f'----------- tititititititi ValidationError {error} -----------')
            except Exception as error:
                _logger.info(f'----------- tititititititi Exception {error} -----------')

            self.run_next_execution(machine)
        else:
            machine = self.env['biometric.device.details'].search([('is_next_execution', '=', False)], limit=1)
            if machine:
                try:
                    machine.action_download_attendance()
                except UserError as error:
                    _logger.info(f'----------- tititititititi UserError {error} -----------')
                except ValidationError as error:
                    _logger.info(f'----------- tititititititi ValidationError {error} -----------')
                except Exception as error:
                    _logger.info(f'----------- tititititititi Exception {error} -----------')

                self.run_next_execution(machine)

    def action_download_attendance(self):
        """Function to download attendance records from the device"""
        _logger.info(f'+++++++++++ Cron Download Attendance Executed +++++++++++')
        zk_attendance = self.env['zk.machine.attendance']
        hr_attendance = self.env['hr.attendance']
        for info in self:
            _logger.info(f'----------- tititititititi machine name {info.name} -----------')
            _logger.info(f'----------- tititititititi machine device_ip {info.device_ip} -----------')
            _logger.info(f'----------- tititititititi machine port_number {info.port_number} -----------')
            machine_ip = info.device_ip
            zk_port = info.port_number
            try:
                # Connecting with the device with the ip and port provided
                zk = ZK(machine_ip, port=zk_port, timeout=15,
                        password=0,
                        force_udp=False, ommit_ping=False)
            except NameError:
                raise UserError(
                    _("Pyzk module not Found. Please install it"
                      "with 'pip3 install pyzk'."))
            conn = self.device_connect(zk)
            self.action_set_timezone()
            if conn:
                conn.disable_device()  # Device Cannot be used during this time.
                user = conn.get_users()
                attendance = conn.get_attendance()
                if attendance:
                    for each in attendance:
                        try:
                            atten_time = each.timestamp
                            local_tz = pytz.timezone(
                                self.env.user.partner_id.tz or 'GMT')
                            local_dt = local_tz.localize(atten_time, is_dst=None)
                            utc_dt = local_dt.astimezone(pytz.utc)
                            utc_dt = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                            atten_time = datetime.datetime.strptime(
                                utc_dt, "%Y-%m-%d %H:%M:%S")
                            atten_time = fields.Datetime.to_string(atten_time)
                            for uid in user:
                                if uid.user_id == each.user_id:
                                    get_user_id = self.env['hr.employee'].search(
                                        [('device_id_num', '=', each.user_id)], limit=1)
                                    if get_user_id:
                                        duplicate_attens = zk_attendance.search(
                                            [('device_id_num', '=', each.user_id),
                                            ('punching_time', '=', atten_time)])
                                        duplicate_atten_ids = duplicate_attens.ids
                                        if len(duplicate_atten_ids) == 0:
                                            zk_attendance.create({
                                                'employee_id': get_user_id.id,
                                                'device_id_num': each.user_id,
                                                'attendance_type': str(each.status),
                                                'punch_type': str(each.punch),
                                                'punching_time': atten_time,
                                                'address_id': info.address_id.id,
                                                'device_id': info.id,
                                            })
                                            att_var = hr_attendance.search([(
                                                'employee_id', '=', get_user_id.id),
                                                ('check_out', '=', False)])
                                            att_var = list(att_var)
                                            if each.punch == 0:  # check-in
                                                if len(att_var) == 0:
                                                    hr_attendance.create({
                                                        'employee_id':
                                                            get_user_id.id,
                                                        'check_in': atten_time
                                                    })
                                            if each.punch == 1:  # check-out
                                                if len(att_var) > 0:
                                                    att_var[0].write({
                                                        'check_out': atten_time
                                                    })
                                                else:
                                                    att_var1 = hr_attendance.search(
                                                        [('employee_id', '=',
                                                        get_user_id.id)])
                                                    att_var1 = list(att_var1)
                                                    if len(att_var1) > 0:
                                                        att_var1[-1].write({
                                                            'check_out': atten_time
                                                        })
                                    else:
                                        employee = self.env['hr.employee'].create({
                                            'device_id_num': each.user_id,
                                            'name': uid.name
                                        })
                                        zk_attendance.create({
                                            'employee_id': employee.id,
                                            'device_id_num': each.user_id,
                                            'attendance_type': str(each.status),
                                            'punch_type': str(each.punch),
                                            'punching_time': atten_time,
                                            'address_id': info.address_id.id,
                                            'device_id': info.id,
                                        })
                                        hr_attendance.create({
                                            'employee_id': employee.id,
                                            'check_in': atten_time
                                        })
                        except UserError as error:
                            _logger.info(f'----------- tititititititi UserError {error} -----------')
                        except ValidationError as error:
                            _logger.info(f'----------- tititititititi ValidationError {error} -----------')
                        except Exception as error:
                            _logger.info(f'----------- tititititititi Exception {error} -----------')
                    conn.disconnect
                    return True
                else:
                    raise UserError(_('Unable to get the attendance log, please'
                                      'try again later.'))
            else:
                raise UserError(_('Unable to connect, please check the'
                                  'parameters and network connections.'))

    def action_restart_device(self):
        """For restarting the device"""
        zk = ZK(self.device_ip, port=self.port_number, timeout=15,
                password=0,
                force_udp=False, ommit_ping=False)
        self.device_connect(zk).restart()
