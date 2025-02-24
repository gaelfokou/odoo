from email.policy import default

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class Timetable(models.Model):
    _name = 'siantou.ems.timetable.timetable'
    _description = 'Emplois du temps'

    # Semestre liée à la programmation de cours
    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        'Semestre',
        required=True,
        ondelete='restrict'
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

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
        required=True,
        ondelete='restrict'
    )

    # Filière liée à la programmation de cours
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        'Filière',
        required=True,
        related='class_id.filiere_id',
        ondelete='restrict'
    )

    # Niveau lié à la programmation de cours
    level_id = fields.Many2one(
        'siantou.ems.core.level',
        'Niveau',
        required=True,
        related='class_id.niveau_id',
        ondelete='restrict'
    )

    specialty_id = fields.Many2one(
        'siantou.ems.core.specialty',
        string='Spécialité',
        compute="_compute_class", 
        store=False
    )

    # Cours programmé
    subject_id = fields.Many2one(
        'siantou.ems.core.subject',
        'Cours',
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

    # Date du jour où le cours sera programmé
    date = fields.Date(
        'Date du jour',
        required=True
    )

    # Jour où le cours est programmé
    day_of_week = fields.Selection([
        ('0', 'Lundi'),
        ('1', 'Mardi'),
        ('2', 'Mercredi'),
        ('3', 'Jeudi'),
        ('4', 'Vendredi'),
        ('5', 'Samedi'),
    ], 'Jour de la semaine',
        readonly=True, store=True,
        compute='_onchange_date',
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

    # Groupe auquel appartient l'emploi du temps
    group_id = fields.Many2one(
        'siantou.ems.timetable.group',
        'Version',
        required=True,
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

    @api.depends('class_id')
    def _compute_class(self):
        for record in self:
            if record.class_id.id:
                specialty_ids = list(record.class_id.specialty_ids)
                if len(specialty_ids) > 0:
                    record.specialty_id = specialty_ids[0]
                else:
                    record.specialty_id = None

    @api.onchange('class_id')
    def _onchange_class(self):
        for record in self:
            if record.class_id.id:
                record.field_of_study_id = record.class_id.filiere_id
                record.level_id = record.class_id.niveau_id

    # Méthode pour remplir automatiquement le jour de la semaine
    @api.depends('date')
    def _onchange_date(self):
        for record in self:
            if record.date:
                # Calculer le jour de la semaine (0 = lundi, 1 = mardi, ...)
                day_of_week = datetime.strptime(str(record.date), '%Y-%m-%d').weekday()
                record.day_of_week = str(day_of_week)  # Assurez-vous que le jour soit un string (0-6)

    # Contrainte logique pour se rassurer qu'on a pas deux enregistrements identiques
    @api.constrains('class_id', 'subject_id', 'classroom_id', 'employee_id', 'day_of_week', 'start_time', 'end_time')
    def _check_duplicate(self):
        for record in self:
            if self.search([
                ('class_id', '=', record.class_id.id),
                ('subject_id', '=', record.subject_id.id),
                ('classroom_id', '=', record.classroom_id.id),
                ('employee_id', '=', record.employee_id.id),
                ('day_of_week', '=', record.day_of_week),
                ('start_time', '=', record.end_time),
                ('end_time', '=', record.start_time),
            ]):
                raise ValidationError("Cet enregistrement existe déjà")

    # Contrainte logique pour se rassurer que deux cours ne sont pas programmés dans la même salle de classe sur des horaires qui se chevauchent le même jour
    @api.constrains('classroom_id', 'date', 'start_time', 'end_time')
    def _check_classroom_is_free(self):
        for record in self:
            timetable = self.search([
                ('id', '!=', record.id),
                ('classroom_id', '=', record.classroom_id.id),
                ('date', '=', record.date),
                ('start_time', '<', record.end_time),
                ('end_time', '>', record.start_time),
            ], limit=1)
            if timetable:
                raise ValidationError("Deux cours ne doivent pas être programmés dans la même salle de classe sur des horaires qui se chevauchent le même jour")

    # Contrainte logique pour s'assurer que l'heure de fin est supérieure à l'heure de début
    @api.constrains('start_time', 'end_time')
    def _check_time(self):
        for record in self:
            if record.end_time <= record.start_time:
                raise ValidationError("L'heure de fin du cours doit être supérieure à l'heure de début du cours")

    # Contrainte logique pour s'assurer que les heures de début et de fin sont définies
    @api.constrains('start_time', 'end_time')
    def _check_time_is_set(self):
        for record in self:
            if record.start_time <= 0 or record.end_time <= 0:
                raise ValidationError("Vous devez définir des heures de début et de fin corrects")

    def action_timetable_automatic(self):
        action = self.env.ref('siantou_ems_core.action_generatetimetable_wizard').read()[0]
        action.update({
            'name': 'Planification automatique',
            'res_model': 'siantou.ems.timetable.timetable_wizard',
            'type': 'ir.actions.act_window',
        })
        return action
    

    def action_timetable_print(self):
        action = self.env.ref('siantou_ems_core.action_print_timetable_wizard').read()[0]
        action.update({
            'name': 'Impression de l\'emploi du temps',
            'res_model': 'siantou.ems.timetable.timetable_print_wizard',
            'type': 'ir.actions.act_window',
        })
        return action

    def action_cancel_timetable_exception(self):
        employee_timetables = self.env['siantou.ems.timetable.timetable'].search([
            ('id', '=', self.id),
        ])
        employee_timetables = list(employee_timetables)
        if len(employee_timetables) > 0:
            employee_timetable = employee_timetables[0]
            employee_timetable.write({
                'status': '1',
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

class TimetableGroup(models.Model):
    _name = 'siantou.ems.timetable.group'
    _description = 'Groupe d\'emploi de temps'

    name = fields.Char('Nom du groupe', required=True)

    timetables = fields.One2many(
        'siantou.ems.timetable.timetable',
        'group_id',
        string='Emplois du temps'
    )

    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        'Semester',
        required=True
    )

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
    def _check_constrains_time(self):
        for record in self:
            if record.start_time > record.end_time:
                raise ValidationError(f"L'heure de début ne doit pas être supérieure à l'heure de fin")
            elif not TimetableSlotItem.are_almost_equal(round((record.end_time - record.start_time), 2), round(1.00, 2)):
                raise ValidationError(f"La plage horaire entre l'heure de début et l'heure de fin ne doit pas être supérieure 1")
            else:
                slotitems = self.env['siantou.ems.timetable.slotitem'].search([
                    ('id', '!=', record.id),
                ]).filtered(lambda rec: (rec.start_time <= record.start_time and rec.end_time > record.start_time) or (rec.start_time < record.end_time and rec.end_time >= record.end_time) or \
                    (record.start_time <= rec.start_time and record.end_time > rec.start_time) or (record.start_time < rec.end_time and record.end_time >= rec.end_time))
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

    is_default = fields.Boolean(string="Par défaut", default=False)

    @api.constrains('is_default')
    def _check_constrains_default(self):
        for record in self:
            if record.is_default:
                slots = self.env['siantou.ems.timetable.slot'].search([
                    ('id', '!=', record.id),
                    ('is_default', '=', True),
                ])
                slots = list(slots)
                if len(slots) > 0:
                    raise ValidationError(f"Créneau horaire par défaut déjà défini")

    @api.onchange('department_id')
    def _onchange_department(self):
        for record in self:
            if record.department_id.id:
                record.field_of_study_ids = self.env['siantou.ems.core.field_of_study'].search([
                    ('department_id', '=', record.department_id.id),
                ])
            else:
                record.field_of_study_ids = []
