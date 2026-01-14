from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)

class SessionEnrollment(models.Model):
    _name = 'siantou.session'
    _inherit = 'mail.thread'
    _description = "Gestion des Session d'admission"
    _order = 'id desc'
    _sql_constraints = [
        ('uniq_session', 'unique(name,year_id,campus)',
         "Cette session existe déja pour cette Année académique!"),
    ]

    def _get_default_acadmic_year(self):
        """Get the default acedemic year active"""
        year_id = self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1)
        if not year_id:
            raise ValidationError("""Aucune annéé academique activé""")
        self.name = f"Session_{year_id.name}"
        return year_id.id

    # @api.onchange("year_id")
    @api.depends('year_id')
    def _get_name(self):
        for record in self:
            self.name = f"Session_{record.year_id.name}"
        return self.name

    # @api.depends('year_id')
    # def _compute_fee_start_date(self):
    #     for record in self:
    #         record.start_date = record.year_id.start_time

    # @api.depends('year_id')
    # def _compute_fee_end_date(self):
    #     for record in self:
    #         record.end_date = record.year_id.end_time

    name = fields.Char(
        string="Nom de la session",
        required=True,
    )
    start_date = fields.Date('Date de début', required=True, related='year_id.start_time')
    end_date = fields.Date(
        'Date de fin',
        required=True, related='year_id.end_time')
    cycle_ids = fields.Many2many(
        'oe.school.course',
        string='Cycles',
        required=True,
    )
    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année Académique',
        help="Séletionner l'année Académique",
        required=True,
        default=lambda self: self._get_default_acadmic_year()
    )
    is_active = fields.Boolean(string='Actif ?', default=False)
    state = fields.Selection([
            ('draft', 'Brouillon'),
            ('cancel', 'Cancelled'),
            ('admission', 'Admission en cours'),
            ('done', 'Fait')
        ],
        'Statut',
        default='draft'
    )
    registre_ids = fields.One2many(
        'siantou.session.registre',
        'session_id',
        'Registres de session'
    )

    # @api.constrains('active')
    # def _check_unique_active(self):
    #     for record in self:
    #         if self.search([('id', '!=', record.id), ('active', '=', 'True')]):
    #             raise ValidationError("Il ne peut y avoir qu'une seule session active à la fois.")

    @api.constrains('cycle_ids')
    def check_cycle_id_existe_in_session(self):
        session_ids = self.env['siantou.session'].sudo().search([
            ('year_id','=',self.year_id.id)
        ])
        if len(session_ids)>=1:
            for session_id in session_ids:
                for id in self.cycle_ids.ids:
                    # _logger.info(f"form {self.cycle_ids.ids}")
                    # _logger.info(f"id {id}")
                    # _logger.info(session_id.cycle_ids.ids)
                    # _logger.info(id in session_id.cycle_ids.ids)
                    if id in session_id.cycle_ids.ids:
                        cycle_id = self.env['oe.school.course'].search([('id','=',id)], limit=1)
                        raise ValidationError(
                            _(f"Le cycle << {cycle_id.name} >> existe déjà dans une session d'admission de l'année {self.year_id.name}"))

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        for record in self:
            start_date = fields.Date.from_string(record.start_date)
            end_date = fields.Date.from_string(record.end_date)
            if start_date > end_date:
                raise ValidationError(
                    _("La date de début doit être antérieur à la date de fin"))

    def set_to_draft(self):
        self.state = 'draft'

    def cancel_register(self):
        self.state = 'cancel'

    def start_admission(self):
        for record in self:
            for  c in record.cycle_ids:
                self.env["siantou.session.registre"].create({
                        "name":'Reg_'+c.name,
                        "start_date": record.start_date,
                        "end_date": record.end_date,
                        "cycle_id": c.id,
                        "session_id": record.id,
                        "year_id": record.year_id.id,
                        # "campus": record.campus_id.id,
                        "session_id": record.id,
                        "state": "application",
                })
        self.state = 'admission'
        self.active=True

    def close_register(self):
        for record in self:
            registres = self.env["siantou.session.registre"].search([('session_id','=',self.id)])
            for reg in registres:
                for stud in reg.admission_ids:
                    if stud.status not in ['transfer', 'rej']:
                        raise ValidationError(
                        _("Veuillez d'abord valider les candidatures présentent les registres de cette session d'admission"))
            record.state = 'done'
            record.active = True

class SessionRegisterEnrollment(models.Model):
    _name = "siantou.session.registre"
    _inherit = 'mail.thread'
    _description = "Gestion des Registre d'admission"
    _order = 'id desc'
    _sql_constraints = [
        ('uniq_registre', 'unique(name,field_of_study_id,year_id,campus)',
         "Cette session existe déja pour cette année académique!"),
    ]

    name = fields.Char(
        'Name', required=True, readonly=True)
    start_date = fields.Date(
        'Date de début', store=True, related='session_id.start_date')
    end_date = fields.Date(
        'Date de fin', store=True, related='session_id.end_date')
    cycle_id = fields.Many2one(
        'oe.school.course', 'Cursus ou Cycle',
        required=True,
    )
    session_id = fields.Many2one(
        'siantou.session',
        "Session d'admission",
        required=True,
        ondelete='cascade'
    )
    admission_ids = fields.One2many(
        'oe.school.student.enrollment',
        'registre_id',
        'Candidatures'
    )
    state = fields.Selection(
        [
            ('draft', 'Brouillon'),
            ('application', 'Candidature en cours'),
            ('cancel', 'Annulé'),
            ('admission', 'Admission En cours'),
            ('done', 'Fait'),
            ('archive', 'Archivé')
        ],
        'Status',
        default='draft',
        tracking=True
    )

    is_active = fields.Boolean(default=True)

    year_id = fields.Many2one('siantou.ems.core.year',
        'Année académique',
        readonly=True,
        related='session_id.year_id',
        store=True
    )

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        for record in self:
            start_date = fields.Date.from_string(record.start_date)
            end_date = fields.Date.from_string(record.end_date)
            if start_date > end_date:
                raise ValidationError(
                    _('End Date cannot be set before Start Date'))

    def confirm_register(self):
        self.state = 'confirm'

    def set_to_draft(self):
        self.state = 'draft'

    def cancel_register(self):
        self.state = 'cancel'

    def start_application(self):
        self.state = 'application'

    def start_admission(self):
        for record in self:
            if len(record.admission_ids)==0:
                raise ValidationError(
                    _("Aucune candidature n'a été enregistré sur ce registre!"))
            else:
                data = [l for l in record.admission_ids if l.state == "draft"]
                for  c in data:
                    c.send_to_verify()
                record.state = 'admission'

    def approve_all(self):
        for a in self.admission_ids:
            if a.state == 'verification':
                a.approve_application()

    def approve_all(self):
        for a in self.admission_ids:
            if a.state == 'verification':
                a.approve_application()

    def close_register(self):
        for record in self:
            for ad in record.admission_ids:
                if ad.state not in ['approve','reject']:
                    raise ValidationError(
                    _("Veuillez d'abord approuver ou rejeter toutes les candidatures"))
            record.state = 'done'
