
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api

import datetime
import time
import logging

from psycopg2 import sql, DatabaseError

_logger = logging.getLogger("++++++++++++")

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError, UserError
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP




class Student(models.Model):
    _inherit = 'res.partner'

    is_student = fields.Boolean(
        string='Est un étudiant',
        default=False
    )

    # gender = fields.Selection([
    #     ('male', 'Homme'),
    #     ('female', 'Femme'),
    #     ('other', 'Autre')
    # ], string='Sexe',
    # default='other')

    # school_id = fields.Many2one(
    #     'siantou.ems.core.school',
    #     string='Ecole',
    #     required=True
    # )

    # course_id = fields.Many2one(
    #     'oe.school.course',
    #     string='Cycle'
    # )

    # field_of_study_id = fields.Many2one(
    #     'siantou.ems.core.field_of_study',
    #     string='Filière',
    #     # required=True
    # )

    # level_id = fields.Many2one(
    #     'siantou.ems.core.level',
    #     string='Niveau',
    #     # required=True
    # )

    # batch_id = fields.Many2one(
    #     'siantou.ems.core.student.batch',
    #     string='Lot de l\'étudiant',
    # )

    # @api.model
    # def create(self, vals):
    #     print(f"\n\nvals['school_id'] : {vals['school_id']}")
    #     print(f"vals['field_of_study_id'] : {vals['field_of_study_id']}")
    #     print(f"vals['level_id'] : {vals['level_id']}\n\n")
    #     batch = self.env['siantou.ems.core.student.batch'].assign_batch(vals['school_id'], vals['field_of_study_id'], vals['level_id'])
    #     vals['batch_id'] = batch.id
    #     return super(Student, self).create(vals)



class StudentInscription(models.Model):
    _name = 'oe.school.student'
    _inherit=['mail.thread', 'mail.activity.mixin',]
    _description = 'Student'

    name = fields.Char(string="Nom(s) et prénom(s)", required=True)
    matricule = fields.Char(string="Matricule")
    student_enroll_id = fields.Many2one(
        'oe.school.student.enrollment',
        string='Etudiant(Préinscription)',
        ondelete='cascade',
        # required=True
    )
    batch_id = fields.Many2one(
        'siantou.ems.core.student.batch',
        string='Lot de l\'étudiant',
    )
    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='Ecole',
        # required=True
    )
    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cycle',
        required=True
    )
    region_id = fields.Many2one("siantou.ems.core.region", string="Région")
    city_id = fields.Many2one("siantou.ems.core.city", string="Ville")
    quarter_id = fields.Many2one("siantou.ems.core.quarter", string="Quartier")
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
        required=True,
    )
    type_cour = fields.Selection([
        ('cj', 'Cours du jour'),
        ('cs', 'Cours du soir'),
    ], required=True, string="Type de cours",)
    status_univ = fields.Selection([
            ('new', 'Nouveau'),
            ('red', 'Redoublant'),
        ], required=True, 
        string="Statut universitaire"
    )
    date_naissance = fields.Date(string="Date de naissance", required=True)
    lieu_naissance = fields.Char(string="Lieu de naissance", required=True)
    sexe = fields.Selection([
            ('masculin', 'Masculin'),
            ('feminin', 'Féminin'),
        ], required=True, string="Sexe"
    )
    situat_matri = fields.Selection([
        ('marie', 'Marié'),
        ('celibat', 'Célibataire'),
        ('concub', 'Concubinage'),
    ], string="Situation matrimoniale", required=True)
    nationalite = fields.Many2one(
        'siantou.ems.core.country',
        string="Nationalité(Pays d'origine)",
        required=True,
    )
    autre = fields.Char(string="Autre pays")
    lieu_residence = fields.Char(string="Lieu de résidence", required=True)
    email = fields.Char(string="E-mail", required=True)
    num_tel = fields.Char(string="N° de Téléphone", required=True)
    level_id = fields.Many2one("siantou.ems.core.level", string="Niveau", required=True)
    annee_acad_current = fields.Many2one(
        "siantou.ems.core.year", 
        string="Année académique", 
        required=True,
        default=lambda self: self.env['siantou.ems.core.year'].sudo().search([('active', '=', True)], limit=1)
    )


    def generate_matricule(self):
        # Get the current year
        current_year = datetime.datetime.now().year
        last_caract_year = str(current_year)[2:]
        students = self.env['oe.school.student'].sudo().search([])  
        nbre = len(students) + 1
        code = f"{last_caract_year}IUS000000{nbre}"
        _logger.info(f"Matricule généré : {code}")
        return code


    @api.model
    def create(self, vals):
        field_of_study = self.env['siantou.ems.core.field_of_study'].browse(vals['field_of_study_id'])
        batch = self.env['siantou.ems.core.student.batch'].assign_batch(
            field_of_study.school_id.id, 
            field_of_study.id, 
            vals['level_id']
        )
        vals['batch_id'] = batch.id
        vals['matricule'] = self.generate_matricule()
        return super().create(vals)
    

