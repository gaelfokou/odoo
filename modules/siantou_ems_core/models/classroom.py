# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import unique
import logging

_logger = logging.getLogger(__name__)

class Campus(models.Model):
    _name = 'siantou.ems.core.campus'
    _description = 'Campus'

    # Code
    code = fields.Char(
        'Code',
        required=True
    )

    # Nom
    name = fields.Char(
        string="Nom du campus",
        required=True
    )

    # Université à laquelle appartient ce bâtiment
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company
    )

class Building(models.Model):
    _name = 'siantou.ems.core.building'
    _description = 'Bâtiment'

    # Code du bâtiment
    code = fields.Char(
        'Code',
        required=True
    )

    # Nom du bâtiment
    name = fields.Char(
        string="Nom du bâtiment",
        required=True
    )

    address_id = fields.Many2one(
        'siantou.ems.core.campus',
        required=True,
        string="Campus",
    )

    school_ids = fields.Many2many('siantou.ems.core.school', 'school_building_rel', 'building_id', 'school_id', string='Écoles')

    is_active = fields.Boolean('Actif', default=True)

class Classroom(models.Model):
    _name = 'siantou.ems.core.building.classroom'
    _description = 'Salles de classe'

    # Code de la salle de classe
    code = fields.Char(
        string='Code',
        required=True,
        help="Code unique pour identifier la salle de classe."
    )

    # Nom de la salle de classe
    name = fields.Char(
        string='Nom',
        required=True,
        index=True,
        translate=True,
        help="Nom descriptif de la salle de classe."
    )

    # Bâtiment auquel appartient la salle de classe
    building_id = fields.Many2one(
        'siantou.ems.core.building',
        string='Bâtiment',
        required=True,
        index=True,
        help="Bâtiment auquel cette salle de classe est associée."
    )

    # Capacité de la salle de classe
    capacity = fields.Integer(
        string='Capacité',
        required=True,
        default=60,
        help="Nombre maximal d'étudiants pouvant être accueillis dans cette salle."
    )

    # Relation avec les emplois du temps
    timetable_ids = fields.One2many(
        'siantou.ems.timetable.timetable',
        string='Emplois du temps',
        compute='_compute_timetables',
        store=False
    )

    is_cours_active = fields.Boolean(string='Actif pour les cours ?', default=False)

    is_examen_active = fields.Boolean(string='Actif pour les examens ?', default=False)

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code de la salle de classe doit être unique.'),
    ]

    @api.constrains('capacity')
    def _check_capacity(self):
        for record in self:
            if record.capacity <= 0:
                raise ValidationError('La capacité doit être supérieure à 0')

    @api.depends('is_cours_active')
    def _compute_timetables(self):
        # Recherche des emplois du temps qui correspondent à la salle de classe
        for record in self:
            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('classroom_id', '=', record.id),
                '|',
                '&',
                ('group_id.is_active', '=', True),
                ('group_id.is_submit', '=', False),
                '&',
                ('group_parent_id.is_active', '=', True),
                ('group_parent_id.is_submit', '=', False),
            ])

            # Affecter les emplois du temps trouvés à l'attribut timetable_ids
            record.timetable_ids = timetables

    @api.onchange('is_cours_active')
    def _onchange_timetables(self):
        # Recherche des emplois du temps qui correspondent à la salle de classe
        for record in self:
            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('classroom_id', '=', record.id),
                '|',
                '&',
                ('group_id.is_active', '=', True),
                ('group_id.is_submit', '=', False),
                '&',
                ('group_parent_id.is_active', '=', True),
                ('group_parent_id.is_submit', '=', False),
            ])

            # Affecter les emplois du temps trouvés à l'attribut timetable_ids
            record.timetable_ids = timetables

    def action_open_filter(self):
        view_id = self.env.ref('siantou_ems_core.classroom_filter_wizard').id
        return {
            'name': 'Filtre des salles de classe',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'classroom.filter.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_status': None,
            },
        }

    def action_reset_filter(self):
        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', '')
        action = self.env.ref('siantou_ems_core.action_show_classroom').read()[0]
        action.update({
            'target': 'main',
        })
        return action

    def action_print_pdf(self):
        active_ids = self.env.context.get('active_ids', [])
        classrooms = self.env['siantou.ems.core.building.classroom'].browse(active_ids)
        classrooms = list(classrooms)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        report_data = self.env['classroom.print.wizard'].create({})
        domains = [
            ('id', 'in', active_ids)
        ]
        data = report_data.print_classroom_report_data(domains=domains)

        # Appeler le rapport PDF
        if len(data['docdata']['classroom_data']) == 0:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_classroom')
        report_action.update({
            'name': 'Salles de classe PDF',
        })
        return report_action.report_action(self, data=data)
