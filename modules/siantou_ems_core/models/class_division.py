# -*- coding: utf-8 -*-

import re
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import unique
import logging

_logger = logging.getLogger(__name__)

class EducationClass(models.Model):
    _name = 'siantou.ems.core.class'
    _description = "Classe Standard"
    _inherit = ['mail.thread']

    # _sql_constraints = [
    #     ('unique_class',
    #      'unique(field_of_study_id,level_id,school_id)',
    #      'Classe unique par school_id'),
    # ]

    name = fields.Char(string='Nom',
                       compute='_compute_name', store=True,
                       help="Entrer le nom de la Classe")

    field_of_study_id = fields.Many2one('siantou.ems.core.field_of_study', string='Filière',
                                 required=True, help="Filière")

    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cursus ou Cycle',
        related='field_of_study_id.cycle_id',
        store=True
    )

    supervision_id = fields.Many2one('oe.school.course.supervision', string='Tutelle académique',
                                 help="Tutelle académique")

    student_ids = fields.One2many(
        'oe.school.student',
        'class_id',
        string='Liste des étudiants'
    )

    number_of_student = fields.Integer(
        string='Nombre d\'étudiants',
        compute='_compute_student', store=True,
    )

    timetable_ids = fields.One2many(
        'siantou.ems.timetable.timetable',
        'class_id',
        string='Liste des emplois du temps'
    )

    specialty_id = fields.Many2one('siantou.ems.core.specialty', string='Spécialité',
                                 required=True, help="Spécialité")

    option_id = fields.Many2one('siantou.ems.core.option', string='Option',
                                 help="Option")

    level_id = fields.Many2one('siantou.ems.core.level', string='Niveau',
                                 required=True, help="Niveau")

    school_id = fields.Many2one('siantou.ems.core.school', string='Ecole', required=True)

    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année Académique',
        required=True,
        default=lambda self: self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1)
    )

    ue_ids = fields.Many2many('siantou.ems.core.unite.enseignement', 'class_ue_rel', 'class_id', 'ue_id', string='Unités d\'enseignement')

    type_cour = fields.Selection([
            ('cj', 'Cours du jour'),
            ('cs', 'Cours du soir'),
        ],
        string='Type de cours',
        default='cj',
    )

    group_ids = fields.One2many(
        'siantou.ems.core.class.group',
        'class_id',
        string='Liste des groupes'
    )

    _sql_constraints = [
        ('unique_year_specialty_option_level_type_cour', 'unique(year_id,specialty_id,option_id,level_id,type_cour)', 'L\'année académique, la spécialité, l\'option, le niveau, et le type de cours doivent être uniques.'),
    ]

    @api.depends('specialty_id', 'option_id', 'level_id', 'type_cour')
    def _compute_name(self):
        for record in self:
            specialty_name = record.specialty_id.name if record.specialty_id.id else ''
            option_name = record.option_id.name if record.option_id.id else ''
            if option_name != '':
                option_name = f'- {option_name}'
            niveau_name = record.level_id.name if record.level_id.id else ''
            niveau_name = re.sub(r'Niveau ', '', niveau_name)
            type_cour_name = record.type_cour if record.type_cour == 'cs' else ''
            name = '{} {} {} {}'.format(specialty_name, option_name, niveau_name, type_cour_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.onchange('specialty_id', 'option_id', 'level_id', 'type_cour')
    def _onchange_name(self):
        for record in self:
            specialty_name = record.specialty_id.name if record.specialty_id.id else ''
            option_name = record.option_id.name if record.option_id.id else ''
            if option_name != '':
                option_name = f'- {option_name}'
            niveau_name = record.level_id.name if record.level_id.id else ''
            niveau_name = re.sub(r'Niveau ', '', niveau_name)
            type_cour_name = record.type_cour if record.type_cour == 'cs' else ''
            name = '{} {} {} {}'.format(specialty_name, option_name, niveau_name, type_cour_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.depends('student_ids')
    def _compute_student(self):
        for record in self:
            record.number_of_student = len(record.student_ids.ids)

    @api.depends('student_ids')
    def _onchange_student(self):
        for record in self:
            record.number_of_student = len(record.student_ids.ids)

    @api.onchange('school_id')
    def _onchange_school(self):
        for record in self:
            record.field_of_study_id = None
            record.specialty_id = None
            record.option_id = None

    @api.onchange('field_of_study_id')
    def _onchange_filiere(self):
        for record in self:
            record.specialty_id = None
            record.option_id = None

    @api.onchange('specialty_id')
    def _onchange_specialty(self):
        for record in self:
            record.option_id = None

    def action_open_filter(self):
        view_id = self.env.ref('siantou_ems_core.class_filter_wizard').id
        return {
            'name': 'Filtre des étudiants',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'class.filter.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
        }

    def action_reset_filter(self):
        self.env['ir.config_parameter'].sudo().set_param(f'filter.{self.env.user.id}', '')
        action = self.env.ref('siantou_ems_core.action_show_class').read()[0]
        action.update({
            'target': 'main',
        })
        return action

    def action_print_pdf(self):
        active_ids = self.env.context.get('active_ids', [])
        classes = self.env['siantou.ems.core.class'].browse(active_ids)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        report_data = self.env['class.print.wizard'].create({})
        domain = [('id', 'in', active_ids)]
        data = report_data.print_class_report_data(domain)

        # Appeler le rapport PDF
        if not data['docdata']['class_data']:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_class')
        return report_action.report_action(self, data=data)

class EducationClassGroup(models.Model):
    _name = 'siantou.ems.core.class.group'
    _description = "Groupe de classe"

    name = fields.Char(string='Nom', required=True,
                       help="Entrer le nom du groupe")

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
        ondelete='cascade'
    )
