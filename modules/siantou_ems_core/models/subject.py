import math

from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError

class Subject(models.Model):
    _name = 'siantou.ems.core.subject'
    _description = 'Cours'

    # Code du cours
    code = fields.Char(
        'Code',
        required=True
    )

    # Variable booléenne pour savoir si c'est un tronc commun ou pas
    shared_subject = fields.Boolean(
        'Tronc commun',
        default=False
    )

    subject_parent_ids = fields.Many2many(
        'siantou.ems.core.subject',
        'subject_parent_child_rel',
        'subject_child_id',
        'subject_parent_id',
        string='Cours parent',
        domain="[('shared_subject', '=', True)]",
    )

    subject_child_ids = fields.Many2many(
        'siantou.ems.core.subject',
        'subject_parent_child_rel',
        'subject_parent_id',
        'subject_child_id',
        string='Cours enfant',
        domain="[('shared_subject', '=', False)]",
    )

    # Variable booléenne pour savoir si c'est une matière fait partie de l'EPS ou pas
    eps_subject = fields.Boolean(
        'Mathière de l\'EPS'
    )

    # Nom du cours
    name = fields.Char(
        'Nom du cours',
        required=True
    )

    # Volume horaire du cours sur un semestre
    hours_credit = fields.Float(
        'Volume horaire semestriel',
        help='Volume horaire du cours sur un semestre',
        default=0.0,
        required=True
    )

    ue_ids = fields.Many2many('siantou.ems.core.unite.enseignement', 'ue_subject_rel', 'subject_id', 'ue_id', string='Unités d\'enseignement')

    syllabus_ids = fields.One2many('siantou.ems.core.syllabus', 'subject_id', string='Syllabus')

    # Les enseignants qui dispensent ce cours
    teacher_ids = fields.Many2many(
        'hr.employee',
        'teacher_subject_rel',
        'subject_id',
        'employee_id',
        string='Enseignants',
        # compute='_compute_teacher_ids',
        # inverse='_set_teacher_ids'
    )

    # Les priorités de chaque enseignant sur ce cours
    teacher_priority_ids = fields.One2many(
        'siantou.ems.core.teacher.subject.priority',
        'subject_id',
        'Priorités des enseignants'
    )

    total_credit = fields.Integer(
        string='Crédit total',
        compute='_compute_credit'

    )

    # Contrainte SQL pour empêcher d'avoir le même code pour différentes filières
    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code du cours doit être unique.'),
    ]

    # Contrainte logique pour s'assurer que les cours en tronc commun sont ajoutés
    @api.constrains('subject_child_ids')
    def _check_subject_child_ids(self):
        for record in self:
            if record.shared_subject and len(record.subject_child_ids.ids) == 0:
                raise ValidationError("Les cours en tronc commun doivent être ajoutés")

    @api.onchange('shared_subject')
    def _onchange_shared_subject(self):
        for record in self:
            record.subject_child_ids = []

    # Contrainte logique pour s'assurer que le volume horaire est précisé et supérieur à 0
    @api.constrains('hours_credit')
    def _check_hours_credit(self):
        for record in self:
            if record.hours_credit <= 0:
                raise ValidationError("Le volume horaire semestriel doit être supérieur à 0")

    # Méthode calculée pour teacher_ids afin de montrer les enseignants liés dans le modèle des priorités
    # @api.depends('teacher_priority_ids')
    # def _compute_teacher_ids(self):
    #     for record in self:
    #         record.teacher_ids = record.teacher_priority_ids.mapped('employee_id')

    # Méthode inverse pour ajouter/supprimer des enseignants dans le modèle des priorités avec une priorité par défaut de 1
    # def _set_teacher_ids(self):
    #     for record in self:
    #         current_teacher_ids = record.teacher_priority_ids.mapped('employee_id').ids
    #         new_teacher_ids = record.teacher_ids.ids

    #         # Ajouter les nouveaux enseignants avec une priorité par défaut de 1
    #         to_add = set(new_teacher_ids) - set(current_teacher_ids)
    #         for teacher_id in to_add:
    #             self.env['siantou.ems.core.teacher.subject.priority'].create({
    #                 'employee_id': teacher_id,
    #                 'subject_id': record.id,
    #                 'priority': 1,
    #             })

    #         # Supprimer les enseignants enlevés de teacher_ids
    #         to_remove = set(current_teacher_ids) - set(new_teacher_ids)
    #         record.teacher_priority_ids.filtered(lambda p: p.employee_id.id in to_remove).unlink()

    field_name = fields.Char(compute='_compute_field_name', string='field_name')

    @api.depends('syllabus_ids.subject_credit')
    def _compute_credit(self):
        for record in self:
            total = 0
            # On récupère tous les syllabus liés à cette sous matière
            syllabuses = self.env['siantou.ems.core.syllabus'].search([
                ('subject_id', '=', record.id)
            ])

            # Additionner les crédits de chaque syllabus
            for syllabus in syllabuses:
                total += syllabus.subject_credit

            record.total_credit = total

    def update_teacher_priority(self, subject):
        try:
            teacher_ids = subject.teacher_ids.ids
            exist_teacher_ids = []
            for teacher_priority_id in subject.teacher_priority_ids:
                if teacher_priority_id.employee_id.id not in teacher_ids:
                    teacher_priority_id.unlink()
                else:
                    exist_teacher_ids.append(teacher_priority_id.employee_id.id)
            exist_teacher_ids = list(set(exist_teacher_ids))
            for teacher_id in subject.teacher_ids:
                if teacher_id.id not in exist_teacher_ids:
                    subject.teacher_priority_ids.create({
                        'employee_id': teacher_id.id,
                        'subject_id': subject.id,
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
        subject = super(Subject, self).create(vals)

        self.update_teacher_priority(subject)

        return subject

    def write(self, vals):
        subject = self.env['siantou.ems.core.subject'].search([('id', '=', self.id)], limit=1)

        res = super(Subject, self).write(vals)

        self.update_teacher_priority(subject)

        return res

class ProgressReport(models.Model):
    _name = 'siantou.ems.core.progress.report'
    _description = 'Fiche de progression'

    name = fields.Char(
        string='Nom',
        compute='_compute_name', store=True,
    )

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
        required=True,
        ondelete='cascade'
    )

    subject_id = fields.Many2one(
        'siantou.ems.core.subject',
        'Cours',
        required=True,
        ondelete='cascade'
    )

    session_ids = fields.One2many(
        'siantou.ems.core.subject.session',
        'report_id',
        'Sessions de cours'
    )

    subject_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    @api.depends('class_id', 'subject_id')
    def _compute_name(self):
        for record in self:
            class_name = record.class_id.name if record.class_id.id else ''
            subject_name = record.subject_id.name if record.subject_id.id else ''
            name = '{} - {}'.format(class_name, subject_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.onchange('class_id', 'subject_id')
    def _onchange_name(self):
        for record in self:
            class_name = record.class_id.name if record.class_id.id else ''
            subject_name = record.subject_id.name if record.subject_id.id else ''
            name = '{} - {}'.format(class_name, subject_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.depends('class_id')
    def _compute_class_domain(self):
        for record in self:
            domain = []
            if record.class_id.id:
                ue_ids = record.class_id.ue_ids
                domain = [
                    ('ue_ids', 'in', ue_ids.ids)
                ]
            record.subject_id_domain = domain

    @api.onchange('class_id')
    def _onchange_class(self):
        for record in self:
            record.subject_id = None

class SubjectSession(models.Model):
    _name = 'siantou.ems.core.subject.session'
    _description = 'Session de cours'

    name = fields.Char(
        string='Nom',
        required=True
    )

    description = fields.Text(
        'Description',
    )

    timetable_id = fields.Many2one(
        'siantou.ems.timetable.timetable',
        string='Emploi du temps',
        ondelete='cascade'
    )

    report_id = fields.Many2one(
        'siantou.ems.core.progress.report',
        'Fiche de progression',
        required=True,
        ondelete='cascade'
    )

    _sql_constraints = [
        ('unique_timetable_report_rel', 'unique(timetable_id, report_id)', 'Un emploi du temps ne peut être lié à une même fiche de progression qu\'une seule fois.')
    ]

    timetable_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    @api.depends('report_id')
    def _compute_class_domain(self):
        for record in self:
            domain = []
            if record.report_id.id:
                timetable_ids = record.report_id.class_id.timetable_ids
                domain = [
                    ('id', 'in', timetable_ids.ids),
                    ('group_id.is_active', '=', True),
                    ('group_id.is_submit', '=', False),
                    ('subject_id', '=', record.report_id.subject_id.id)
                ]
            record.timetable_id_domain = domain

    @api.onchange('report_id')
    def _onchange_school(self):
        for record in self:
            record.timetable_id = None
