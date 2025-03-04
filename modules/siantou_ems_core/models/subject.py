import math

from odoo import models, fields, api
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
        default=True
    )

    subject_id = fields.Many2one(
        'siantou.ems.core.subject',
        string='Cours',
        domain="[('shared_subject', '=', True)]",
    )

    # Disponibilité de l'enseignant
    subject_ids = fields.One2many(
        'siantou.ems.core.subject',
        'subject_id',
        'Cours',
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
        default=0,
        required=True
    )

    ue_ids = fields.Many2many('siantou.ems.core.unite.enseignement', 'ue_subject_rel', 'subject_id', 'ue_id', string="Unités d'enseignement")
    
    syllabus_ids = fields.One2many(comodel_name= "siantou.ems.core.syllabus", inverse_name='subject_id', string='Syllabus')

    # Les enseignants qui dispensent ce cours
    teacher_ids = fields.Many2many(
        'hr.employee',
        relation='teacher_subject_rel',
        column1='subject_id',
        column2='employee_id',
        string='Enseignants',
        compute='_compute_teacher_ids',
        inverse='_set_teacher_ids'
    )
    
    # Les priorités pour chaque enseignant sur ce cours
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
    @api.constrains('subject_ids')
    def _check_subject_ids(self):
        for record in self:
            if record.shared_subject and len(record.subject_ids.ids) == 0:
                raise ValidationError("Les cours en tronc commun doivent être ajoutés")

    @api.onchange('shared_subject')
    def _onchange_shared_subject(self):
        for record in self:
            record.subject_ids = []

    # Contrainte logique pour s'assurer que le volume horaire est précisé et strictement supérieur à 0
    @api.constrains('hours_credit')
    def _check_hours_credit(self):
        for record in self:
            if record.hours_credit <= 0:
                raise ValidationError("Le volume horaire semestriel doit être supérieur à 0")

    # Méthode calculée pour teacher_ids afin de montrer les enseignants liés dans le modèle des priorités
    @api.depends('teacher_priority_ids')
    def _compute_teacher_ids(self):
        for record in self:
            record.teacher_ids = record.teacher_priority_ids.mapped('employee_id')

    # Méthode inverse pour ajouter/supprimer des enseignants dans le modèle des priorités avec une priorité par défaut de 1
    def _set_teacher_ids(self):
        for record in self:
            current_teacher_ids = record.teacher_priority_ids.mapped('employee_id').ids
            new_teacher_ids = record.teacher_ids.ids

            # Ajouter les nouveaux enseignants avec une priorité par défaut de 1
            to_add = set(new_teacher_ids) - set(current_teacher_ids)
            for teacher_id in to_add:
                self.env['siantou.ems.core.teacher.subject.priority'].create({
                    'employee_id': teacher_id,
                    'subject_id': record.id,
                    'priority': 1,
                })

            # Supprimer les enseignants enlevés de teacher_ids
            to_remove = set(current_teacher_ids) - set(new_teacher_ids)
            record.teacher_priority_ids.filtered(lambda p: p.employee_id.id in to_remove).unlink()
            
    
    field_name = fields.Char(compute='_compute_field_name', string='field_name')
    
    @api.depends('syllabus_ids.subject_credit')
    def _compute_credit(self):
        for rec in self:
            total = 0
            # On récupère tous les syllabus liés à cette sous matière
            syllabuses = self.env['siantou.ems.core.syllabus'].search([
                ('subject_id', '=', rec.id)
            ])
            
            # Additionner les crédits de chaque syllabus
            for syllabus in syllabuses:
                total += syllabus.subject_credit
            
            rec.total_credit = total