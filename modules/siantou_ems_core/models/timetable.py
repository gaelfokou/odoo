import math
from email.policy import default
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
import psycopg2
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class TimetableSubjectHour(models.Model):
    _name = 'siantou.ems.timetable.subject.day.hour'
    _description = 'Jour et heure du cours'

    def _default_start_date(self):
        group = self.env['siantou.ems.timetable.group'].search([('is_active', '=', True)], limit=1)
        if group:
            return group.semester_id.start_time
        else:
            return None

    # Date du jour où le cours sera programmé
    start_date = fields.Date(
        'Date de début',
        required=True,
        default=_default_start_date,
    )

    def _default_end_date(self):
        group = self.env['siantou.ems.timetable.group'].search([('is_active', '=', True)], limit=1)
        if group:
            return group.semester_id.end_time
        else:
            return None

    # Date du jour où le cours sera programmé
    end_date = fields.Date(
        'Date de fin',
        required=True,
        default=_default_end_date,
    )

    # Jour où le cours est programmé
    day_of_week = fields.Selection([
            ('0', 'Lundi'),
            ('1', 'Mardi'),
            ('2', 'Mercredi'),
            ('3', 'Jeudi'),
            ('4', 'Vendredi'),
            ('5', 'Samedi'),
            ('6', 'Dimanche'),
        ],
        'Jour de la semaine',
        compute='_compute_start_date',
        store=True
    )

    # Heure de début du cours
    start_time = fields.Float(
        'Heure de début',
        required=True,
        default=0,
        ondelete='restrict',
        widget='time'
    )

    # Heure de fin du cours
    end_time = fields.Float(
        'Heure de fin',
        required=True,
        default=0,
        ondelete='restrict',
        widget='time'
    )

    timetable_id = fields.Many2one(
        'siantou.ems.timetable.timetable',
        string='Emplois du temps',
        ondelete='cascade'
    )

    not_active_slotitems = fields.Integer(
        string='Créneau horaire inactif',
        default=0,
    )

    status = fields.Selection([
        ('0', 'En attente'),
        ('1', 'Présent'),
        ('2', 'Absent'),
        ('3', 'Permissionnaire'),
        ('4', 'Exception'),
    ], 'Statut',
        default='0',
    )

    # Contrainte logique pour s'assurer que la date de fin est supérieure à la date de début
    @api.constrains('start_date', 'end_date')
    def _constrains_date(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError('La date de fin doit être supérieure ou égale à la date de début')

    # Méthode pour remplir automatiquement le jour de la semaine
    @api.onchange('start_date')
    def _onchange_start_date(self):
        for record in self:
            if record.start_date:
                record.day_of_week = str(record.start_date.weekday())
            else:
                record.day_of_week = None

    @api.depends('start_date')
    def _compute_start_date(self):
        for record in self:
            if record.start_date:
                record.day_of_week = str(record.start_date.weekday())
            else:
                record.day_of_week = None

    # Contrainte logique pour s'assurer que les heures de début et de fin sont définies et que l'heure de fin est supérieure à l'heure de début
    @api.constrains('start_time', 'end_time')
    def _constrains_time(self):
        for record in self:
            if record.start_time <= 0.0 or record.end_time <= 0.0:
                raise ValidationError("Vous devez définir des heures de début et de fin corrects")
            elif record.end_time <= record.start_time:
                raise ValidationError("L'heure de fin du cours doit être supérieure à l'heure de début du cours")

class Timetable(models.Model):
    _name = 'siantou.ems.timetable.timetable'
    _description = 'Emplois du temps'

    name = fields.Char(
        string='Nom',
        compute='_compute_name', store=True,
    )

    def _default_semester(self):
        group = self.env['siantou.ems.timetable.group'].search([('is_active', '=', True)], limit=1)
        if group:
            return group.semester_id
        else:
            return None

    # Semestre liée à la programmation de cours
    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        string='Semestre',
        # default=_default_semester,
        related='group_id.semester_id',
        store=True
    )

    year_id = fields.Many2one(
        'siantou.ems.core.year',
        'Année académique',
        related='semester_id.year_id',
        store=True
    )

    batch_id = fields.Many2one(
        'siantou.ems.core.student.batch',
        string='Lot d\'étudiants'
    )

    # Ajouter un champ de relation vers hr.department pour lier la filière au département
    department_id = fields.Many2one(
        'hr.department',
        string='Département'
    )

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='Ecole',
        required=True,
        ondelete='restrict'
    )

    # Filière liée à la programmation de cours
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
        related='specialty_id.field_of_study_id',
        store=True
    )

    # Niveau lié à la programmation de cours
    level_id = fields.Many2one(
        'siantou.ems.core.level',
        'Niveau',
        required=True,
        ondelete='restrict'
    )

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
        required=True,
        ondelete='restrict'
    )

    specialty_id = fields.Many2one(
        'siantou.ems.core.specialty',
        string='Spécialité',
        required=True,
        ondelete='restrict'
    )

    option_id = fields.Many2one(
        'siantou.ems.core.option',
        string='Option',
        ondelete='restrict'
    )

    ue_id = fields.Many2one(
        'siantou.ems.core.unite.enseignement',
        string='Unité d\'enseignement',
        # required=True,
        ondelete='restrict'
    )

    subject_id = fields.Many2one(
        'siantou.ems.core.subject',
        'Cours',
        required=True,
        ondelete='restrict'
    )

    # Bâtiment auquel appartient la salle de classe
    building_id = fields.Many2one(
        'siantou.ems.core.building',
        'Bâtiment',
        required=True,
        ondelete='restrict'
    )

    # Salle liée à la programmation de cours
    classroom_id = fields.Many2one(
        'siantou.ems.core.building.classroom',
        'Salle de classe',
        required=True,
        ondelete='restrict'
    )

    # Enseignant lié à la programmation de cours
    employee_id = fields.Many2one(
        'hr.employee',
        'Enseignant',
        ondelete='restrict'
    )

    def _default_date(self):
        group = self.env['siantou.ems.timetable.group'].search([('is_active', '=', True)], limit=1)
        if group:
            return group.semester_id.start_time
        else:
            return None

    # Date du jour où le cours sera programmé
    date = fields.Date(
        'Date du jour',
        required=True,
        default=_default_date,
    )

    # Jour où le cours est programmé
    day_of_week = fields.Selection([
            ('0', 'Lundi'),
            ('1', 'Mardi'),
            ('2', 'Mercredi'),
            ('3', 'Jeudi'),
            ('4', 'Vendredi'),
            ('5', 'Samedi'),
            ('6', 'Dimanche'),
        ],
        'Jour de la semaine',
        compute='_compute_date',
        store=True
    )

    # Heure de début du cours
    start_time = fields.Float(
        'Heure de début',
        required=True,
        default=0,
        ondelete='restrict',
        widget='time'
    )

    # Heure de fin du cours
    end_time = fields.Float(
        'Heure de fin',
        required=True,
        default=0,
        ondelete='restrict',
        widget='time'
    )

    def _default_group(self):
        return self.env['siantou.ems.timetable.group'].search([('is_active', '=', True)], limit=1)

    # Version auquel appartient l'emploi du temps
    group_id = fields.Many2one(
        'siantou.ems.timetable.group',
        'Version',
        required=True,
        default=_default_group,
        ondelete='cascade'
    )

    not_active_slotitems = fields.Integer(
        string='Créneau horaire inactif',
        default=0,
    )

    status = fields.Selection([
        ('0', 'En attente'),
        ('1', 'Présent'),
        ('2', 'Absent'),
        ('3', 'Permissionnaire'),
        ('4', 'Exception'),
    ], 'Statut',
        default='0',
    )

    class_group_id = fields.Many2one(
        'siantou.ems.core.class.group',
        'Groupe',
        ondelete='restrict'
    )

    subject_day_hour_ids = fields.One2many(
        'siantou.ems.timetable.subject.day.hour',
        'timetable_id',
        string='Jours et heures du cours'
    )

    specialty_id_domain = fields.Binary(compute='_compute_school_domain', default=[])

    subject_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    @api.depends('subject_id')
    def _compute_name(self):
        for record in self:
            record.name = record.subject_id.name

    @api.onchange('subject_id')
    def _onchange_name(self):
        for record in self:
            record.name = record.subject_id.name

    @api.depends('school_id')
    def _compute_school_domain(self):
        for record in self:
            domain = []
            if record.school_id.id:
                field_of_study_ids = self.env['siantou.ems.core.field_of_study'].search([('school_id', '=', record.school_id.id)])
                domain = [('field_of_study_id', 'in', field_of_study_ids.ids)]
            record.specialty_id_domain = domain

    @api.onchange('school_id')
    def _onchange_school(self):
        for record in self:
            record.field_of_study_id = None
            record.level_id = None
            record.class_id = None
            record.class_group_id = None
            record.specialty_id = None
            record.option_id = None
            record.ue_id = None
            record.subject_id = None

    # @api.onchange('field_of_study_id')
    # def _onchange_field_of_study(self):
    #     for record in self:
    #         record.level_id = None
    #         record.class_id = None
    #         record.class_group_id = None
    #         record.specialty_id = None
    #         record.option_id = None
    #         record.ue_id = None
    #         record.subject_id = None

    @api.onchange('level_id')
    def _onchange_level(self):
        for record in self:
            record.class_id = None
            record.class_group_id = None
            record.ue_id = None
            record.subject_id = None

    @api.onchange('specialty_id')
    def _onchange_specialty(self):
        for record in self:
            record.class_id = None
            record.class_group_id = None
            record.option_id = None
            record.ue_id = None
            record.subject_id = None

    @api.onchange('option_id')
    def _onchange_option(self):
        for record in self:
            record.class_id = None
            record.class_group_id = None
            record.ue_id = None
            record.subject_id = None

    @api.depends('class_id')
    def _compute_class_domain(self):
        for record in self:
            domain = []
            if record.class_id.id:
                ue_ids = record.class_id.ue_ids
                domain = [('ue_ids', 'in', ue_ids.ids)]
            record.subject_id_domain = domain

    @api.onchange('class_id')
    def _onchange_class(self):
        for record in self:
            record.class_group_id = None
            record.ue_id = None
            record.subject_id = None

    # @api.onchange('ue_id')
    # def _onchange_ue(self):
    #     for record in self:
    #         record.subject_id = None

    # Méthode pour remplir automatiquement le jour de la semaine
    @api.onchange('date')
    def _onchange_date(self):
        for record in self:
            if record.date:
                record.day_of_week = str(record.date.weekday())
            else:
                record.day_of_week = None

    @api.depends('date')
    def _compute_date(self):
        for record in self:
            if record.date:
                record.day_of_week = str(record.date.weekday())
            else:
                record.day_of_week = None

    # Contrainte logique pour se rassurer que deux cours ne sont pas programmés dans la même salle de classe sur des horaires qui se chevauchent le même jour
    @api.constrains('classroom_id', 'date', 'subject_id', 'level_id', 'start_time', 'end_time')
    def _constrains_classroom_is_free(self):
        for record in self:
            timetables = self.search([
                ('id', '!=', record.id),
                ('classroom_id', '=', record.classroom_id.id),
                ('date', '=', record.date),
                '|',
                ('subject_id', '!=', record.subject_id.id),
                ('level_id', '!=', record.level_id.id),
            ]).filtered(lambda rec: not (rec.start_time >= record.end_time or rec.end_time <= record.start_time))
            timetables = list(timetables)
            if len(timetables) > 0:
                raise ValidationError("Deux cours ne doivent pas être programmés dans la même salle de classe sur des horaires qui se chevauchent le même jour")

    # Contrainte logique pour s'assurer que les heures de début et de fin sont définies et que l'heure de fin est supérieure à l'heure de début
    # @api.constrains('start_time', 'end_time')
    # def _constrains_time(self):
    #     for record in self:
    #         if record.start_time <= 0.0 or record.end_time <= 0.0:
    #             raise ValidationError("Vous devez définir des heures de début et de fin corrects")
    #         elif record.end_time <= record.start_time:
    #             raise ValidationError("L'heure de fin du cours doit être supérieure à l'heure de début du cours")

    def create_timetable(self, timetable):
        try:
            timetables = []
            times = [timetable.semester_id.start_time, timetable.semester_id.end_time]
            subject_day_hour_ids = list(timetable.subject_day_hour_ids)
            for i, subject_day_hour_id in enumerate(subject_day_hour_ids):
                if i == 0:
                    timetable.write({
                        'date': subject_day_hour_id.start_date,
                        'start_time': subject_day_hour_id.start_time,
                        'end_time': subject_day_hour_id.end_time,
                    })
                    timetables.append(timetable)
                    times = [subject_day_hour_id.start_date, subject_day_hour_id.end_date]
                else:
                    timetable_id = self.env['siantou.ems.timetable.timetable'].create({
                        'semester_id': timetable.semester_id.id,
                        'school_id': timetable.school_id.id,
                        'field_of_study_id': timetable.field_of_study_id.id,
                        'level_id': timetable.level_id.id,
                        'specialty_id': timetable.specialty_id.id,
                        'class_id': timetable.class_id.id,
                        'class_group_id': timetable.class_group_id.id,
                        'ue_id': timetable.ue_id.id,
                        'subject_id': timetable.subject_id.id,
                        'building_id': timetable.building_id.id,
                        'classroom_id': timetable.classroom_id.id,
                        'employee_id': timetable.employee_id.id,
                        'date': subject_day_hour_id.start_date,
                        'start_time': subject_day_hour_id.start_time,
                        'end_time': subject_day_hour_id.end_time,
                        'group_id': timetable.group_id.id,
                    })
                    timetables.append(timetable_id)
                subject_day_hour_id.unlink()
            if len(timetables) > 0:
                semester_hours_credit = timetable.subject_id.hours_credit
                if times[0] == timetable.ue_id.semestre_id.start_time and times[1] == timetable.ue_id.semestre_id.end_time:
                    number_of_week = timetable.ue_id.semestre_id.number_of_week
                else:
                    start_time = times[0]
                    end_time = times[1]
                    diff_days = (end_time - start_time).days
                    number_of_week = math.ceil(diff_days / 7)
                for week in range(0, number_of_week):
                    if semester_hours_credit <= 0:
                        break
                    for first_timetable in timetables:
                        weekly_hours_credit = first_timetable.end_time - first_timetable.start_time
                        weekly_hours_credit = weekly_hours_credit - first_timetable.not_active_slotitems
                        semester_hours_credit -= weekly_hours_credit
                        if week > 0:
                            target_date = first_timetable.date + timedelta(weeks=week)
                            timetable_id = self.env['siantou.ems.timetable.timetable'].create({
                                'semester_id': first_timetable.semester_id.id,
                                'school_id': first_timetable.school_id.id,
                                'field_of_study_id': first_timetable.field_of_study_id.id,
                                'level_id': first_timetable.level_id.id,
                                'specialty_id': first_timetable.specialty_id.id,
                                'class_id': first_timetable.class_id.id,
                                'class_group_id': first_timetable.class_group_id.id,
                                'ue_id': first_timetable.ue_id.id,
                                'subject_id': first_timetable.subject_id.id,
                                'building_id': first_timetable.building_id.id,
                                'classroom_id': first_timetable.classroom_id.id,
                                'employee_id': first_timetable.employee_id.id,
                                'date': target_date,
                                'start_time': first_timetable.start_time,
                                'end_time': first_timetable.end_time,
                                'group_id': first_timetable.group_id.id,
                            })
            # self.env.cr.commit()
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    @api.model
    def create(self, vals):
        timetable = super(Timetable, self).create(vals)

        self.create_timetable(timetable)

        return timetable

    def action_timetable_automatic(self):
        action = self.env.ref('siantou_ems_core.action_generatetimetable_wizard').read()[0]
        action.update({
            'name': 'Planification automatique',
            'res_model': 'siantou.ems.timetable.timetable_wizard',
            'type': 'ir.actions.act_window',
        })
        return action

    def action_timetable_filter(self):
        action = self.env.ref('siantou_ems_core.action_filter_timetable_wizard').read()[0]
        action.update({
            'name': 'Filtre des emplois du temps',
            'res_model': 'timetable.filter.wizard',
            'type': 'ir.actions.act_window',
            'context': {'no_breadcrumbs': True},
        })
        return action

    # def action_timetable_filter(self):
    #     view_id = self.env.ref('siantou_ems_core.timetable_filter_wizard').id
    #     return {
    #         'name': 'Filtre des emplois du temps',
    #         'type': 'ir.actions.act_window',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'timetable.filter.wizard',
    #         'views': [(view_id, 'form')],
    #         'view_id': view_id,
    #         'target': 'new',
    #         # 'domain' : [('id', 'in', search_ids)],
    #         # 'context': {'no_breadcrumbs': True},
    #         ### in domain pass ids if you want to show only filter data else it will display all data of that model.
    #     }

    def action_timetable_print(self):
        active_ids = self.env.context.get('active_ids', [])
        timetables = self.env['siantou.ems.timetable.timetable'].browse(active_ids)
        if len(active_ids) == 0:
            timetables = self.env['siantou.ems.timetable.timetable'].search([])
            active_ids = timetables.ids
        if len(active_ids) == 0:
            raise UserError('Aucune donnée trouvée')
        report_data = self.env['timetable.print.wizard'].create({
            'semester_id': timetables[0].semester_id.id,
            'group_id': timetables[0].group_id.id,
        })
        domain = [('id', 'in', active_ids)]
        data = report_data.print_timetable_report_data(domain)

        # Appeler le rapport PDF
        if not data['docdata']['timetable_data']:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_timetable')
        return report_action.report_action(self, data=data)

    def action_present_all_timetable_exception(self):
        active_ids = self.env.context.get('active_ids', [])
        timetable_ids = self.env['siantou.ems.timetable.timetable'].browse(active_ids)
        for timetable in timetable_ids:
            timetable.write({
                'status': '1',
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_absent_all_timetable_exception(self):
        active_ids = self.env.context.get('active_ids', [])
        timetable_ids = self.env['siantou.ems.timetable.timetable'].browse(active_ids)
        for timetable in timetable_ids:
            timetable.write({
                'status': '2',
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

class TimetableGroup(models.Model):
    _name = 'siantou.ems.timetable.group'
    _description = 'Version d\'emploi du temps'

    name = fields.Char(string='Nom du groupe', required=True)

    timetables = fields.One2many(
        'siantou.ems.timetable.timetable',
        'group_id',
        string='Emplois du temps'
    )

    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        string='Semestre',
        required=True
    )

    is_active = fields.Boolean(string="Actif", default=False)

    @api.constrains('is_active')
    def _constrains_default(self):
        for record in self:
            if record.is_active:
                slots = self.env['siantou.ems.timetable.group'].search([
                    ('id', '!=', record.id),
                    ('is_active', '=', True),
                ])
                slots = list(slots)
                if len(slots) > 0:
                    raise ValidationError(f"Version active déjà définie")

class TimetableSlotItem(models.Model):
    _name = 'siantou.ems.timetable.slotitem'
    _description = 'Plage horaire'

    slot_id = fields.Many2one(
        'siantou.ems.timetable.slot',
        string='Créneau horaire',
        ondelete='cascade',
    )

    # Heure de début du cours
    start_time = fields.Float(
        string='Heure de début',
        required=True,
        default=0,
        widget='time'
    )

    # Heure de fin du cours
    end_time = fields.Float(
        string='Heure de fin',
        required=True,
        default=0,
        widget='time'
    )

    type = fields.Selection(
        selection=[('0', 'Soir'), ('1', 'Jour')],
        string='Type',
        default='1',
        widget='radio'
    )

    is_active = fields.Boolean(string="Actif", default=True)

    @staticmethod
    def are_almost_equal(a, b, tolerance=1e-9):
        return abs(a - b) < tolerance

    @api.constrains('start_time', 'end_time')
    def _constrains_time(self):
        for record in self:
            if record.start_time > record.end_time:
                raise ValidationError(f"L'heure de début ne doit pas être supérieure à l'heure de fin")
            elif not TimetableSlotItem.are_almost_equal(round((record.end_time - record.start_time), 2), round(1.00, 2)):
                raise ValidationError(f"La plage horaire entre l'heure de début et l'heure de fin ne doit pas être supérieure ou inférieure 1")
            else:
                slotitems = self.env['siantou.ems.timetable.slotitem'].search([
                    ('id', '!=', record.id),
                    ('slot_id', '=', record.slot_id.id),
                ]).filtered(lambda rec: not (rec.start_time >= record.end_time or rec.end_time <= record.start_time))
                slotitems = list(slotitems)
                if len(slotitems) > 0:
                    raise ValidationError(f"La plage horaire entre l'heure de début et l'heure de fin n'est pas disponible")

class TimetableSlot(models.Model):
    _name = 'siantou.ems.timetable.slot'
    _description = 'Créneau horaire'

    name = fields.Char(
        string="Nom",
        required=True
    )

    slotitem_day_ids = fields.One2many(
        'siantou.ems.timetable.slotitem',
        'slot_id',
        string='Plages horaires jour',
        domain=[('type', '=', '1')]
    )

    slotitem_night_ids = fields.One2many(
        'siantou.ems.timetable.slotitem',
        'slot_id',
        string='Plages horaires soir',
        domain=[('type', '=', '0')]
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Département'
    )

    field_of_study_ids = fields.One2many(
        'siantou.ems.core.field_of_study',
        'slot_id',
        string='Filières'
    )

    is_active = fields.Boolean(string="Actif", default=False)

    @api.constrains('is_active')
    def _constrains_default(self):
        for record in self:
            if record.is_active:
                slots = self.env['siantou.ems.timetable.slot'].search([
                    ('id', '!=', record.id),
                    ('is_active', '=', True),
                ])
                slots = list(slots)
                if len(slots) > 0:
                    raise ValidationError(f"Créneau horaire actif déjà défini")

    @api.onchange('department_id')
    def _onchange_department(self):
        for record in self:
            if record.department_id.id:
                record.field_of_study_ids = self.env['siantou.ems.core.field_of_study'].search([
                    ('department_id', '=', record.department_id.id),
                ])
            else:
                record.field_of_study_ids = []
