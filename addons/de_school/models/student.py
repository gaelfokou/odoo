# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import logging

from psycopg2 import sql, DatabaseError

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError, UserError
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _rec_names_search = ['display_name', 'email', 'ref', 'vat', 'company_registry', 'roll_no','admission_no']  # TODO vat must be sanitized the same way for storing/searching
 
    is_student = fields.Boolean('Est un étudiant')
    is_parent_student = fields.Boolean('Est un parent', store=True, compute='_compute_parent')
    contact_type = fields.Selection([
        ('parent', 'Parent'),
        ('address', 'Adresse'),
    ], string='Type de contact', default='parent')
    relation = fields.Selection([
        ('father', 'Père'),
        ('mother', 'Mère'),
        ('uncle', 'Oncle'),
        ('aunt', 'Tante'),
        ('grand-father', 'Grand Père'),
        ('grand-mother', 'Grand Mère'),
        ('other', 'Autre'),
    ], string='Relation')
    is_guardian = fields.Boolean('Est un tuteur')
    
    
    # Academic Fields
    roll_no = fields.Char('Numéro de matricule')
    admission_no = fields.Char('Numéro d\'admission')
    
    course_id = fields.Many2one('oe.school.course', string='Cursus')
    
    use_batch = fields.Boolean(related='course_id.use_batch_subject')
    batch_id = fields.Many2one('oe.school.course.batch', string='Lot',
                               domain="[('course_id','=',course_id)]"
                              )

    use_section = fields.Boolean(related='course_id.use_section')
    section_id = fields.Many2one('oe.school.course.section', string='Section', 
                                 domain="[('course_id','=',course_id)]"
                              )
    
    student_subject_line = fields.One2many('res.partner.subjects.line', 'student_id', 'Cours')
    
    enrollment_count = fields.Integer(string='Nombre d\'enrollement', compute='_compute_enrollment_count')

    med_info_ids = fields.One2many('oe.school.student.medical', 'student_id', 'Informations médicales')
    med_info_count = fields.Integer(string='Nombre d\'informations médicales', compute='_compute_med_info_count')
    
    sibling_ids = fields.One2many('oe.student.sibling', 'partner_id', 'Fraternité')
    #student_subject_ids = fields.One2many('oe.school.student.subject', 'partner_id', 'Subjects')
    
    # Demographic Info
    date_birth = fields.Date(string='Date d\'anniversaire')
    gender = fields.Selection([
        ('male', 'Homme'),
        ('female', 'Femme'),
        ('other', 'Autre'),
    ], string='Genre')
    merital_status = fields.Selection([
        ('single', 'Célibataire'),
        ('married', 'Marié(e)'),
        ('widowed', 'Veuf(ve)'),
        ('separated', 'Séparé(e)'),
        ('divorced', 'Divorcé(e)'),
        ('other', 'Autre'),
    ], string='Situation familiale')
    country_birth = fields.Many2one('res.country','Pays de naissance')
    country_nationality = fields.Many2one('res.country','Nationalité')

    #Gaurdian 
    guardian_id = fields.Many2one('res.partner', string='Tuteur', readonly=True, store=True,
                compute='_compute_guardian',
                help='Le tuteur est une personne responsable de l\'étudiant.',
                                 )
    guardian_name = fields.Char(string='Nom du tuteur', readonly=True,
                compute='_compute_guardian',
                help='Le tuteur est une personne responsable de l\'étudiant.',
                                 ) 
    # Medical Info
    student_complexion = fields.Char('Teint')
    student_weight = fields.Float('Poids (en kg)')
    student_height = fields.Float('Taille (en cm)')
    student_mark_identify = fields.Text('Marque d\'identité')
    student_emergency_contact = fields.Char('Nom du contact en cas d\'urgence')
    student_emergency_phone = fields.Char('Numéro de contact en cas d`\'urgence')

    @api.depends('child_ids', 'child_ids.is_guardian')
    def _compute_guardian(self):
        for record in self:
            guardian = record.child_ids.filtered(lambda x: x.is_guardian)
            if guardian:
                record.guardian_id = guardian[0].id
                record.guardian_name = guardian[0].name
            else:
                record.guardian_id = False
                record.guardian_name = False

    def _compute_enrollment_count(self):
        enrollment_ids = self.env['oe.school.student.enrollment']
        for record in self:
            record.enrollment_count = len(enrollment_ids.search([('model','=',self._name),('res_id','=',record.id)]))

    def _compute_med_info_count(self):
        for record in self:
            record.med_info_count = len(record.med_info_ids)
            
    @api.onchange('contact_type')
    def _onchange_contact_type(self):
        for record in self:
            if record.contact_type == 'parent':
                record.type = 'contact'
            else:
                record.type = 'other'
    
    @api.depends('parent_id')
    def _compute_parent(self):
        for record in self:
            if record.parent_id.is_student:
                record.is_parent_student = True
            else:
                record.is_parent_student = False

    def _compute_subjects(self):
        #subject_ids = self.env['oe.school.course.subject'].search(['|',('course_ids','in',self.course_id.id),('batch_ids','in',self.batch_id.id)])
        self.subject_ids = False #subject_ids.ids

    def _compute_use_batch_from_course(self):
        for record in self:
            if record.course_id.use_batch and len(record.course_id.batch_ids) > 0:
                record.use_batch = True
            else:
                record.use_batch = False
    
            
    def attach_document(self, **kwargs):
        pass
    
    # Generatel Roll Number Method
    def generate_roll_number(self):
        students = self.env['res.partner'].browse(self.env.context.get('active_ids'))
        for student in students:
            if not student.roll_no:
                number = student.course_id.sequence_id.next_by_id()
                student.write({
                    'roll_no': number,
                })

    # -------- Actions ---------------
    def open_enrollment_history(self):
        enrollment_ids = self.env['oe.school.student.enrollment'].search([('model','=',self._name),('res_id','=',self.id)])
        action = self.env.ref('de_school.action_enrollment_history').read()[0]
        action.update({
            'name': 'Historique d\'enregistrement',
            'view_mode': 'tree',
            'res_model': 'oe.school.student.enrollment',
            'type': 'ir.actions.act_window',
            'domain': [('id','in',enrollment_ids.ids)],
            'context': {
                'default_model': self._name,
                'default_res_id': self.id,
            },
        })
        return action

    def open_medical_info(self):
        action = self.env.ref('de_school.action_medical_history').read()[0]
        action.update({
            'name': 'Historique médical',
            'view_mode': 'tree',
            'res_model': 'oe.school.student.medical',
            'type': 'ir.actions.act_window',
            'domain': [('student_id','=',self.id)],
            'context': {
                'default_student_id': self.id,
            },
        })
        return action


class StudentSiblings(models.Model):
    _name = 'oe.student.sibling'
    _description = 'Fraternité'
    
    name = fields.Many2one('res.partner', 'Nom de l\'étudiant', domain="[('is_student','=',True),('is_parent_student','=',False)]", required=True)
    partner_id = fields.Many2one('res.partner', string='Etudiant', required=True, ondelete='cascade', index=True, copy=False)
    course_id = fields.Many2one('oe.school.course', string='Cursus')
    roll_no = fields.Char(string='Numéro de matricule')
    date_birth = fields.Date('Date d\'anniversaire')
    relation = fields.Selection([
        ('brother', 'Frère'),
        ('sister', 'Soeur'),
    ], string='Genre', default='brother', required=True)


class SubjectLine(models.Model):
    _name = 'res.partner.subjects.line'
    _description = 'Cours de l\'étudiant'

    student_id = fields.Many2one('res.partner', 
                                  string='Etudiant',
                                  required=True, 
                                  ondelete='cascade', 
                                  index=True, copy=False
                                )
    subject_id = fields.Many2one('oe.school.subject', string='Cours',
                                 required=True,
                                 domain="[('id','in',subject_ids)]"
                                )
    subject_ids = fields.Many2many(
        comodel_name='oe.school.subject',
        string='Cours du cursus',
        compute='_compute_subjects_from_course',
    )
    

    _sql_constraints = [
        ('unique_student_subject', 'UNIQUE(student_id, subject_id)', 'Un cours doit être unique!'),
    ]

    @api.depends('student_id.course_id')
    def _compute_subjects_from_course(self):
        for record in self:
            if record.student_id.course_id:
                subject_ids = self.env['oe.school.course.subject.line'].search([
                    ('course_id','=',record.student_id.course_id.id)
                ]).mapped('subject_id')
                record.subject_ids = subject_ids
            else:
                record.subject_ids = False    
    
    