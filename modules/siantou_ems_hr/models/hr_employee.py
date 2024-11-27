# -*- coding: utf-8 -*-
from datetime import date

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta

import logging

_logger = logging.getLogger("+++++++++++++++++++==")


class Employe(models.Model):
    _inherit = "hr.employee"
    
    # verifier si un matricule existe déja
    _sql_constraints = [
        ("matricule_unique_check", "unique(matricule)", "Ce matricule existe déjà."),
        ("work_email_unique_check","unique(work_email)","Ce mail existe déja")
    ]
    
    # Education information
    diplome_ids = fields.One2many(
        comodel_name="hr.education.diplome",
        inverse_name="employee_id",
        string="Diplômes",
        tracking=True
    )
    certificat_ids = fields.One2many(
        comodel_name="hr.education.certificat",
        inverse_name="employee_id",
        string="Certificats",
        tracking=True
    )
    discipline_ids = fields.One2many(
        "hr.employee.discipline", "employee_id", string="Discipline", readonly=True,tracking=True,states={
        'integration': [('readonly', False)]}
    )
    
    # nomination_ids = fields.One2many("hr.carriere.nomination","employee_id", tracking=True)
    # study_field = fields.Char("Dernier diplôme")
    # study_equivalence = fields.Many2one(
    #     "hr.education.equivalence", string="Equivalence"
    # )
    study_domaine = fields.Many2one("hr.education.domaine", string="Domaine d'études", tracking=True)
    study_discipline = fields.Many2one(
        "hr.education.discipline", string="Discipline de l'étude",tracking=True
    )

    # civil information
    delivrance_cni = fields.Date("Date de délivrance de La CNI", tracking=True)
    expiration_cni = fields.Date("Date expiration de La CNI",tracking=True)
    lieu_cni = fields.Char("Lieu de délivrance",tracking=True)
    age = fields.Integer(string="Âge du personnel", compute="_compute_age", readonly=True,tracking=True,states={
        'integration': [('readonly', False)]})
    
    # birthday = fields.Date(string="Date de Naissance")
    
    # Classification
    type_personnel = fields.Selection(
        [('agentd', 'AGENTS D\'EXÉCUTION'),
        ('agentm', 'AGENT DE MAÎTRISE'),
        ('cardre', 'CADRE'),
        ('fonc', 'FONCTIONNAIRE'),
        ('agensouscont', 'AGENTS SOUS CONTRAT'),
        ], 'Type employé', default='agentd', select=True, required=True)
    
    type_personnel_imp = fields.Selection(
        [('somis', 'Soumis aux Impôts'),
        ('autre', 'Autre'),
        ], 'Type de Personnel', default='somis', select=True, required=True)

    qualite = fields.Selection([
        ('dg', 'Directeur Général'),
        ('daf', 'Directeur Adm & Fin'),
        ('de', 'Directeur des Etudes'),
        ], 'Qualité', select=True, index=True)
    
    class_type = fields.Selection([
        ('a1', 'Classe A1'),
        ('a2', 'Classe A2'),
        ], 'Classe', default='a2', select=True)

    class_type_b = fields.Selection([
        ('b1', 'Classe B1'),
        ('b2', 'Classe B2'),
        ('b3', 'Classe B3'),
        ('b4', 'Classe B4'),
        ], 'Classe', default='b1', select=True)
    
    expatrier = fields.Boolean(string="Est un cadre Expatrié", default=False)
    
    
    fonction_id = fields.Many2one(
        comodel_name="hr.employee.fonction", string="Fonction", readonly=False,tracking=True
    )
    
    # family
    children_ids = fields.One2many('hr.employee.family', 'employee_id',tracking=True)

    situation_conjoint = fields.Char(string="Situation du conjoint",tracking=True)
    
    rang_id = fields.Many2one(
        comodel_name="hr.employee.rang", string="Rang", tracking=True, states={
        'integration': [('readonly', False)]}, related='fonction_id.rang'
    )

    # citoyen information
    has_handicap = fields.Boolean("A un handicap ?", default=False,tracking=True)
    type_handicap = fields.Char("Type Handicap",tracking=True)
    handicap_description = fields.Text("Description du type de l'handicap",tracking=True)
    
    
    state = fields.Selection(
        [
            ("integration", "Incorporation"),
            ("actif", "Actif"),
            ("suspendu", "Suspendu"),
            ("liencie", "Licencié / Révoqué"),
            ("retraite", "Retraité"),
            ("archive", "Archivé"),
            ("disponibilite", "Mise en disponibilité"),
            ("disposition", "Mise en disposition"),
            ("detachement", "En détachement"),
            ("decede", "Décédé"),
            ("demisione", "Démissionnaire"),
            ("condamnation", "Condamnation "),
            ("stage", "En stage "),
        ],
        string="Etat",
        default="integration",
    )

    def create_employee_user(self, employee_id):
        try:
            name = employee_id.name
            # email = employee_id.work_email
            email = name.replace(' ', '.').lower() + '@siantou.cm'
            password = name.replace(' ', '.').lower()
            user_ids = self.env['res.users'].search([
                ('login', '=', email),
            ])
            user_ids = list(user_ids)
            if len(user_ids) > 0:
                user_id = user_ids[0]
                user_id.write({
                    'login': email,
                    'name': name,
                })
            else:
                group_id = self.env.ref('base.group_portal')
                user_id = self.env['res.users'].create({
                    'login': email,
                    'name': name,
                    'password' : password,
                    'groups_id': [(6, 0, [group_id.id])],
                })
            employee_id.write({
                'work_email': email,
                'user_id': user_id.id,
            })
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
            raise ValidationError("L'adresse e-mail professionnelle n'est pas renseignée.")
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    @api.model
    def create(self, vals):
        employee_id = super(Employe, self).create(vals)

        self.create_employee_user(employee_id)

        return employee_id

    def action_create_employee_user(self):
        employee_ids = self.env['hr.employee'].search([
            ('id', '=', self.id),
        ])
        employee_ids = list(employee_ids)
        if len(employee_ids) > 0:
            employee_id = employee_ids[0]
            self.create_employee_user(employee_id)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_create_all_employee_user(self):
        employee_ids = self.env['hr.employee'].search([])
        for employee_id in employee_ids:
            user_ids = self.env['res.users'].search([
                ('employee_id', '=', employee_id.id),
            ])
            user_ids = list(user_ids)
            if len(user_ids) == 0:
                self.create_employee_user(employee_id)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


    def action_integrer(self):
            sequence_obj = self.env["ir.sequence"]
            for rec in self.filtered(lambda x: x.state != 'actif'):
                rec.state = "actif"
                
    @api.depends("birthday")
    def _compute_age(self):
        for rec in self:
            if rec.birthday:
                today = fields.Date.today()
                diff = relativedelta(today, rec.birthday)
                rec.age = diff.years
            else:
                rec.age = 0