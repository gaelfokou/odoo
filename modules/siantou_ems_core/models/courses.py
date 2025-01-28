# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError
from random import randint
import re
from odoo.exceptions import ValidationError
import logging



_logger = logging.getLogger(__name__)

# class CourseGradingType(models.Model):
#     _name = 'oe.school.course.grading.type'
#     _description = 'Type de notation'
#     name = fields.Char(string='Type', required=True, index=True, translate=True) 

    
class OeSchoolCourse(models.Model):
    _name = 'oe.school.course'
    _description = 'Gestion des Cycles'
    _order = 'name'

    def _default_color(self):
        return randint(1, 11)

    name = fields.Char(string='Nom', required=True, index=True, translate=True)
    code = fields.Char(string='Code', required=True, size=10)
    complete_name = fields.Char('Nom complet', compute='_compute_complete_name', recursive=True, )
    parent_id = fields.Many2one(
        'oe.school.course', 
        string='Cursus parent', index=True, 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    active = fields.Boolean('Actif', default=True)
    company_id = fields.Many2one('res.company', 
        string='Université', index=True,
        default=lambda self: self.env.company,
        domain=[('active','=',True),('is_school','=',True)]
    )
    level_ids = fields.Many2many(
        'siantou.ems.core.level',
        string='Niveaux'
    )
    enable_elective = fields.Boolean('Activer la sélection des cours facultatifs')
    color = fields.Integer(default=_default_color)
    
    sequence_id = fields.Many2one('ir.sequence', 'Séquence des numéros d\'enregistrement', copy=False, check_company=True)

    # batch_ids = fields.One2many('oe.school.course.batch', 'course_id', string="Lots")
    # batch_count = fields.Integer(string='Nombre de lot', compute='_compute_course_batch_count')
    
    # course_subject_line = fields.One2many('oe.school.course.subject.line', 'course_id', string="Cours")

    # use_batch = fields.Boolean(compute='_compute_use_batch_from_company')
    # use_credit_hours = fields.Char(compute='_compute_use_credit_hours_from_company')
    # use_batch_subject = fields.Boolean(compute='_compute_use_batch_subject')

    # use_section = fields.Boolean(compute='_compute_use_section_from_company')
    # section_ids = fields.One2many('oe.school.course.section', 'course_id', string="Sections")
    # section_count = fields.Integer(string='Nombre de section', compute='_compute_course_section_count')

    # def _compute_use_section_from_company(self):
    #     for record in self:
    #         record.use_section = record.company_id.use_section

    # def _compute_course_section_count(self):
    #     for record in self:
    #         record.section_count = len(record.section_ids)
        
    # def _compute_course_batch_count(self):
    #     for record in self:
    #         record.batch_count = len(record.batch_ids)
            
    # def _compute_use_credit_hours_from_company(self):
    #     for record in self:
    #         record.use_credit_hours = record.company_id.use_credit_hours
            
    # def _compute_use_batch_from_company(self):
    #     for record in self:
    #         record.use_batch = record.company_id.use_batch

    # def _compute_use_batch_subject(self):
    #     for record in self:
    #         if record.use_batch and len(record.batch_ids) > 0:
    #             record.use_batch_subject = True
    #         else:
    #             record.use_batch_subject = False


    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for course in self:
            if course.parent_id:
                course.complete_name = '%s/%s' % (course.parent_id.complete_name, course.name)
            else:
                course.complete_name = course.name


    @api.model
    def create(self, vals):
        _logger.info('**************** Vals ****************  %s', vals)
        sequence = self.env['ir.sequence'].create({
            'name': _('Sequence') + ' ' + vals['name'],
            'padding': 5,
            'prefix': vals['name'],
            'company_id': vals.get('company_id'),
        })
        vals['sequence_id'] = sequence.id
        course = super().create(vals)
        return course

    def write(self, vals):
        if 'code' in vals:
            for course in self:
                sequence_vals = {
                    'name': _('Sequence') + ' ' + vals['code'],
                    'padding': 5,
                    'prefix': vals['code'],
                }
                if course.sequence_id:
                    course.sequence_id.write(sequence_vals)
                else:
                    sequence_vals['company_id'] = vals.get('company_id', course.company_id.id)
                    sequence = self.env['ir.sequence'].create(sequence_vals)
                    course.sequence_id = sequence
        if 'company_id' in vals:
            for course in self:
                if course.sequence_id:
                    course.sequence_id.company_id = vals.get('company_id')
        return super().write(vals)

    # Actions
    # def action_open_batch(self):
    #     action = self.env.ref('de_school.action_course_batch').read()[0]
    #     action.update({
    #         'name': 'Lots',
    #         'view_mode': 'tree',
    #         'res_model': 'oe.school.course.batch',
    #         'type': 'ir.actions.act_window',
    #         'domain': [('course_id','=',self.id)],
    #         'context': {
    #             'default_course_id': self.id,
    #         }
    #     })
    #     return action

    # def action_open_section(self):
    #     action = self.env.ref('de_school.action_school_seciton').read()[0]
    #     action.update({
    #         'name': 'Sections',
    #         'view_mode': 'tree',
    #         'res_model': 'oe.school.course.section',
    #         'type': 'ir.actions.act_window',
    #         'domain': [('course_id','=',self.id)],
    #         'context': {
    #             'default_course_id': self.id,
    #         }
    #     })
    #     return action



class SchoolSyllabus(models.Model):
    _name = 'siantou.ems.core.syllabus'
    _description = 'Syllabus'

    def _get_default_acadmic_year(self):
        """Get the default acedemic year active"""
        year = self.env['siantou.ems.core.year'].search([('active', '=', True)], limit=1)
        if not year:
            raise ValidationError("""Aucune année academique activé""")
        return year.id


    name = fields.Char(
        string='Label',
        compute='_compute_name',readonly=False, precompute=True,
        tracking=True,
    )
    class_id = fields.Many2one('siantou.ems.core.class', string='Classe')
    subject_id = fields.Many2one('siantou.ems.core.subject', string='Matière')
    
    # enseignant_id = fields.Many2one(
    #     string='Enseignant',
    #     comodel_name='education.teacher',
    # )

    semestre_id = fields.Many2one('siantou.ems.core.year.semester', string='Semestre', tracking=True)
    
    # total_hours = fields.Integer(string='Total Hours')
    
    description = fields.Text(string='Syllabus Modules')

    pourcentage_cc = fields.Integer(string='Pourcentage CC',default=30,  tracking=True)

    pourcentage_exam = fields.Integer(string='Pourcentage SN', default=50, tracking=True)
    
    pourcentage_presence = fields.Integer(string='Pourcentage Présence', default=20, tracking=True)

    unite_enseignement_id = fields.Many2one('siantou.ems.core.unite.enseignement', string='UE', tracking=True)
    
    note_sn= fields.Boolean('Pas de SN')

    coefficient = fields.Integer(
        string='Crédit',
    )
    
    # display_type = fields.Selection([
    #     ('line_section', "Section"),
    #     ('line_note', "Note")], default=False, help="Technical field for UX purpose.")
    
    note_sn = fields.Selection([
        ('not_sn', 'Pas de SN'),
        ('whit_sn', 'Avec SN'),
    ], string='Type de participation', tracking=True,default='whit_sn',states={'draft': [('readonly', False)]})

    cm = fields.Integer(
        string='Cour Magistral (CM)'
    )
    tp = fields.Integer(
        string='Travaux pratiques (TP)'
    )
    td = fields.Integer(
        string='Travaux dirigés (TD)'
    )
    te = fields.Integer(
        string='Travaux de l\'étudiant (TE)'
    )
    vhp = fields.Integer(
        string='Volume horaire prévue (VHP)',
        compute='_compute_vhp'
        
    )
    vht = fields.Integer(
        string='Volume horaire total (VHT)',
        compute='_compute_vht'
        
    )
    subject_credit = fields.Integer(
        string='Crédit de la matière',
        compute='_compute_subject_credit'
        
    )

    pro_pe_id = fields.Many2one(
        string='pro_pe',
        comodel_name='production.pe',
    )
    
    @api.depends('class_id')
    def _compute_name(self):
        for line in self:
            # if line.display_type in ('line_section', 'line_note'):
            #     continue
            values = []
            if line.class_id:
                values.append(line.class_id.name)
            # if line.journal_id.type == 'sale':
            #     if product.description_sale:
            #         values.append(product.description_sale)
            # elif line.journal_id.type == 'purchase':
            #     if product.description_purchase:
            #         values.append(product.description_purchase)
            line.name = '\n'.join(values)


    @api.depends('cm','td','tp')
    def _compute_vhp(self):
        for rec in self: 
            rec.vhp = rec.cm + rec.td + rec.tp

    @api.depends('vhp','te')
    def _compute_vht(self):
        for rec in self:
            rec.vht = rec.vhp + rec.te

    @api.depends('vht')
    def _compute_subject_credit(self):
        for rec in self:
            rec.subject_credit = rec.vht / 25

    # @api.constrains('total_hours')
    # def validate_time(self):
    #     """returns validation error if the hours is not a possitive value"""
    #     for rec in self:
    #         if rec.total_hours <= 0:
    #             raise ValidationError(_('Hours must be greater than Zero'))
            
    # # ----------------------------------------
    # # Constrains
    # # ----------------------------------------
    @api.constrains('cm')
    def _check_cm_value(self):
        for record in self:
            if record.cm <0:
                raise ValidationError(f"Le Nombre de Cours magistral doit être supérieur ou égal à zéro")
    
    @api.constrains('td')
    def _check_td_value(self):
        for record in self:
            if record.td <0:
                raise ValidationError(f"Le Nombre de Travaux dirigé doit être supérieur ou égal à zéro")
    
    @api.constrains('tp')
    def _check_tp_value(self):
        for record in self:
            if record.tp <0:
                raise ValidationError(f"Le Nombre de Travaux pratique doit être supérieur ou égal à zéro")
    
    @api.constrains('te')
    def _check_tpe_value(self):
        for record in self:
            if record.te <0:
                raise ValidationError(f"Le Nombre de Travaux pratique doit être supérieur ou égal à zéro")
    
    




class SchoolCourseSubject(models.Model):
    _name = 'siantou.ems.core.unite.enseignement'
    _description = "Unité d'enseignement ou module du syllabus"

    type_ue = fields.Selection([
            ('uf', 'UE Fondamentales'),
            ('up', 'UE Professionnelles'),
            ('ut', 'UE Transversales'),
        ],
        required=True,
    )
    code = fields.Char(string="Code UE", required=True,)
    name = fields.Char(string="Intitulé de l'unité", required=True,)
    # cm = fields.Integer(string="Cours majistral", required=True,)
    # td = fields.Integer(string="Travaux dirigé", required=True,)
    # tp = fields.Integer(string="Travaux pratique", required=True,)
    # tpe = fields.Integer(string="Travaux pratique", required=True,)

    # total_volume_horaire = fields.Integer(
    #     string='Nombre d\'horaire total',
    #     compute="_compute_total_volume_horaire",
    #     # 
    # )
    
    subject_ids = fields.One2many(
        string='Matière',
        comodel_name='siantou.ems.core.subject',
        inverse_name='unite_enseignement_id'
    )
    
    semestre_id = fields.Many2one('siantou.ems.core.year.semester', string='Semestre', required=True, tracking=True)
    
    syllabus_ids = fields.One2many('siantou.ems.core.syllabus', 'unite_enseignement_id', string='field_name')
    
    total_credit = fields.Integer('Nombre de crédit total',  compute="_compute_total_credit",)

    _sql_constraints = [
        ('unique_code', 'unique(code)', "Il existe une unité d'enseignement avec ce code"),
        ('unique_name', 'unique(name)', "Il existe une unité d'enseignement avec ce nom"),
    ]
    
    @api.depends('subject_ids', 'subject_ids.syllabus_ids.subject_credit')
    def _compute_total_credit(self):
        for record in self:
            total = 0
            for subject in record.subject_ids:
                # On récupère les syllabus liés à cette sous matière
                syllabuses = self.env['siantou.ems.core.syllabus'].search([
                    ('subject_id', '=', subject.id)
                ])
                total += sum(syllabus.subject_credit for syllabus in syllabuses)
            record.total_credit = total
    
  
    
