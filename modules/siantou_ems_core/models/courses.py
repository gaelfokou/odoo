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
    complete_name = fields.Char('Nom complet', compute='_compute_complete_name', recursive=True, store=True)
    parent_id = fields.Many2one('oe.school.course', string='Cursus parent', index=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
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
    def action_open_batch(self):
        action = self.env.ref('de_school.action_course_batch').read()[0]
        action.update({
            'name': 'Lots',
            'view_mode': 'tree',
            'res_model': 'oe.school.course.batch',
            'type': 'ir.actions.act_window',
            'domain': [('course_id','=',self.id)],
            'context': {
                'default_course_id': self.id,
            }
        })
        return action

    def action_open_section(self):
        action = self.env.ref('de_school.action_school_seciton').read()[0]
        action.update({
            'name': 'Sections',
            'view_mode': 'tree',
            'res_model': 'oe.school.course.section',
            'type': 'ir.actions.act_window',
            'domain': [('course_id','=',self.id)],
            'context': {
                'default_course_id': self.id,
            }
        })
        return action



class SchoolSyllabus(models.Model):
    _name = 'siantou.ems.core.syllabus'
    _description = 'Syllabus'

    def _get_default_acadmic_year(self):
        """Get the default acedemic year active"""
        year = self.env['siantou.ems.core.year'].search([('active', '=', True)], limit=1)
        if not year:
            raise ValidationError("""Aucune année academique activé""")
        return year.id


    name = fields.Char(string="Intitulé", required=True)
    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester', 
        string="Semestre",
        required=True,
    )
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
        required=True,
    )
    level_id = fields.Many2one(
        'siantou.ems.core.level',
        string='Niveau',
        required=True,
        domain=[('id','=',False)]
    )
    specialty_id = fields.Many2one(
        'siantou.ems.core.specialty', 
        string="spécialité",
        domain=[('id','=',False)]
    )
    year_id = fields.Many2one(
        'siantou.ems.core.year', 
        string="Année académique", 
        default=lambda self: self._get_default_acadmic_year()
    )
    specialty_domain = fields.Binary(default=0, store=False)
    level_domain = fields.Binary(default=0, store=False)
    is_exist_speciality = fields.Boolean(default=False)
    state = fields.Selection([
            ('norecord', "Pas d'unité d'enseignement"),
            ('yesrecord', 'Enseignement')
        ],
        default='norecord'
    )
    syllabus_subject_ids = fields.One2many('siantou.ems.core.syllabus.subject', 'syllabus_id')


    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Ce nom existe déjà'),
    ]


    @api.onchange('semester_id', 'field_of_study_id', 'level_id', 'specialty_id', 'year_id')
    def onchange_name(self):
        specialty_name = ""
        field_of_study_name = ""
        level_name = ""
        semester_name = ""
        year_name = ""

        name = f"Syllabus_"
        if self.field_of_study_id:
            field_of_study_name = self.field_of_study_id.name
            name = f"Syllabus_{field_of_study_name}"
        
        if self.specialty_id:
            specialty_name = self.specialty_id.name
            name = f"Syllabus_{field_of_study_name}{'_'+specialty_name or ''}"
        
        if self.level_id:
            level_name = self.level_id.name
            if specialty_name!="":
                name = f"Syllabus_{field_of_study_name}{'_'+specialty_name or ''}{'_'+level_name}"
            else:
                name = f"Syllabus_{field_of_study_name}{'_'+level_name}"

        if self.semester_id:
            semester_name = self.semester_id.name
            name = f"Syllabus_{field_of_study_name}{'_'+specialty_name or ''}{'_'+level_name}{'_'+semester_name}"

        if self.year_id:
            year_name = self.year_id.name
            name = f"Syllabus_{field_of_study_name}{'_'+specialty_name or ''}{'_'+level_name}{'_'+semester_name}{'_'+year_name}"
        
        new_name=re.sub("[$@&+-/*!;:," ")={}]","_",name)
        new_name = new_name.replace(" ", "_")
        self.name = new_name
        if self.field_of_study_id:
            specilty_ids = self.env['siantou.ems.core.specialty'].search([("field_of_study_id","=",self.field_of_study_id.id)])
            if len(specilty_ids)>0:
                _logger.info(specilty_ids)
                self.is_exist_speciality = True
                self.specialty_domain = [("field_of_study_id","=",self.field_of_study_id.id)]
            
            self.level_domain = [('cycle_ids','in',self.field_of_study_id.cursus_id.id)]



    @api.model
    def create(self, values):
        res = super().create(values)
        if len(res.syllabus_subject_ids)>0:
            res.update({
                'state':'yesrecord'
            })
        return res


    def write(self, values):
        _logger.info(values)
        _logger.info(self.id)
        if 'syllabus_subject_ids' in values or values.get('syllabus_subject_ids'):
            syllabus_subject_ids = values.get('syllabus_subject_ids')
            if len(syllabus_subject_ids)>0:
                values['state']='yesrecord'
        res = super().write(values)
        return res




class SchoolCourseSubject(models.Model):
    _name = 'siantou.ems.core.syllabus.subject'
    _description = "Unité d'enseignement ou module du syllabus"

    syllabus_id = fields.Many2one(
        'siantou.ems.core.syllabus',
        string='Syllabus',
        required=True,
    )
    type_ue = fields.Selection([
            ('uf', 'UE Fondamentales'),
            ('up', 'UE Professionnelles'),
            ('ut', 'UE Transversales'),
        ],
        required=True,
    )
    code = fields.Char(string="Code UE", required=True,)
    name = fields.Char(string="Intitulé", required=True,)
    cm = fields.Integer(string="Cours majistral", required=True,)
    td = fields.Integer(string="Travaux dirigé", required=True,)
    tp = fields.Integer(string="Travaux pratique", required=True,)
    tpe = fields.Integer(string="Travaux pratique", required=True,)
    nbre_credit = fields.Integer(string="Nombre de crédits", required=True,)
    syllabus_subject_line_ids = fields.One2many('siantou.ems.core.syllabus.subject.line', 'syllabus_subject_id')

    _sql_constraints = [
        ('unique_code', 'unique(code)', "Il existe une unité d'enseignement avec ce code"),
        ('unique_name', 'unique(name)', "Il existe une unité d'enseignement avec ce nom"),
    ]

    # ----------------------------------------
    # Constrains
    # ----------------------------------------
    @api.constrains('cm')
    def _check_cm_value(self):
        for record in self:
            if record.cm <=0:
                raise ValidationError(f"Le Nombre de Cours majistral doit être supérieur à zéro")
    
    @api.constrains('td')
    def _check_td_value(self):
        for record in self:
            if record.td <=0:
                raise ValidationError(f"Le Nombre de Travaux dirigé doit être supérieur à zéro")
    
    @api.constrains('tp')
    def _check_tp_value(self):
        for record in self:
            if record.tp <=0:
                raise ValidationError(f"Le Nombre de Travaux pratique doit être supérieur à zéro")
    
    @api.constrains('tpe')
    def _check_tpe_value(self):
        for record in self:
            if record.tpe <=0:
                raise ValidationError(f"Le Nombre de Travaux pratique doit être supérieur à zéro")

    @api.constrains('nbre_credit')
    def _check_nbre_credit_value(self):
        for record in self:
            if record.nbre_credit <=0:
                raise ValidationError(f"Le Nombre de crédit doit être supérieur à zéro")
    


class SchoolCourseSubjectLine(models.Model):
    _name = 'siantou.ems.core.syllabus.subject.line'
    _description = "Unité d'enseignement"

    syllabus_subject_id = fields.Many2one(
        'siantou.ems.core.syllabus.subject',
        string="Unité d'enseignement",
        required=True,
    )
    code = fields.Char(string="Code UE")
    name = fields.Char(string="Intitulé")
    nbre_credit = fields.Integer(string="Nombre de crédits")

    _sql_constraints = [
        ('unique_code', 'unique(code)', f"Il existe une matière avec le code entré"),
        ('unique_name', 'unique(name)', f"Il existe une matière avec ce nom entré"),
    ]

    @api.constrains('nbre_credit')
    def _check_nbre_credit_value(self):
        for record in self:
            if record.nbre_credit <=0:
                raise ValidationError(f"Le Nombre de crédit doit être supérieur à zéro")
    

