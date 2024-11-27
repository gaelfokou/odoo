from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError



class SessionEnrollment(models.Model):
    _name = "siantou.session"
    _inherit = "mail.thread"
    _description = "Gestion des Session d'admission"
    _order = 'id DESC'
    _sql_constraints = [
        ('uniq_session', 'unique(name,year_id,campus)',
         "Cette session existe déja pour cette Année académique!"),
    ]

    def _get_default_acadmic_year(self):
        """Get the default acedemic year active"""
        year = self.env['siantou.ems.core.year'].search([('active', '=', True)], limit=1)
        if not year:
            raise ValidationError("""Aucune annéé academique activé""")
        return year.id

    @api.depends("end_date")
    def _get_name(self):
        self.name = "Session_" + str(self.end_date.strftime("%d-%B-%Y"))
        return self.name


    @api.depends('year_id')
    def _compute_fee_start_date(self):
        for record in self:
            record.start_date = record.year_id.start_time

    @api.depends('year_id')
    def _compute_fee_end_date(self):
        for record in self:
            record.end_date = record.year_id.end_time

    name = fields.Char(string="Nom de la session", required=True)
    start_date = fields.Date('Date debut', required=True,
        compute="_compute_fee_start_date")
    end_date = fields.Date(
        'Date de fin', 
        required=True,
        compute="_compute_fee_end_date")
    cycle_ids = fields.Many2many(
        'oe.school.course', 
        string='Cycles', 
        required=True,
    )
    # structure_frais_id = fields.Many2one(
    #     'siantou.ems.fee.structure',
    #     string='Structure de frais', 
    #     required=True
    # )
    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année Académique',
        help="Séletionner l'année Académique",
        required=True, 
        default=lambda self: self._get_default_acadmic_year()
    )
    active = fields.Boolean(default=False)
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
        for rec in self:
            for  c in rec.cycle_ids:
                self.env["siantou.session.registre"].create({
                        "name":'Reg_'+c.name,
                        "start_date": rec.start_date,
                        "end_date": rec.end_date,
                        "cycle_id": c.id,
                        "session_id": rec.id,
                        "year_id": rec.year_id.id,
                        # "campus": rec.campus_id.id,
                        "session_id": rec.id,
                        "state": "application",
                })
        self.state = 'admission'
        self.active=True

    def close_register(self):
        for rec in self:
            registres = self.env["siantou.session.registre"].search([('session_id','=',self.id)])
            for reg in registres:
                for stud in reg.admission_ids:
                    if stud.status not in ['transfer', 'rej']:
                        raise ValidationError(
                        _("Veuillez d'abord valider les candidatures présentent les registres de cette session d'admission"))
            rec.state = 'done'
            rec.active = False





class SessionRegisterEnrollment(models.Model):
    _name = "siantou.session.registre"
    _inherit = "mail.thread"
    _description = "Gestion des Registre d'admission"
    _order = 'id DESC'
    _sql_constraints = [
        ('uniq_registre', 'unique(name,filiere_id,year_id,campus)',
         "Cette session existe déja pour cette année académique!"),
    ]

    name = fields.Char(
        'Name', required=True, readonly=True)
    start_date = fields.Date(
        'Date debut', store=True, related="session_id.start_date")
    end_date = fields.Date(
        'Date de fin', store=True, related="session_id.end_date")
    cycle_id = fields.Many2one(
        'oe.school.course', 'Cycle', 
        required=True, 
        readonly=True,
         tracking=True
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
        ('archive', 'Archivé')],
        'Status', 
        default='draft', 
        tracking=True
    )

    active = fields.Boolean(default=True)

    year_id = fields.Many2one('siantou.ems.core.year',
        'Année académique', 
        readonly=True,
        related="session_id.year_id",
        store=True
    )
    # campus = fields.Many2one(
    #     'siantou.ems.core.campus',
    #     'Campus', 
    #     required=True,
    #     tracking=True
    # )


    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        for record in self:
            start_date = fields.Date.from_string(record.start_date)
            end_date = fields.Date.from_string(record.end_date)
            if start_date > end_date:
                raise ValidationError(
                    _("End Date cannot be set before Start Date."))



    def confirm_register(self):
        self.state = 'confirm'

    def set_to_draft(self):
        self.state = 'draft'

    def cancel_register(self):
        self.state = 'cancel'

    def start_application(self):
        self.state = 'application'

    def start_admission(self):
        for rec in self:
            if len(rec.admission_ids)==0:
                raise ValidationError(
                    _("Aucune candidature n'a été enregistré sur ce registre!"))
            else:
                data = [l for l in rec.admission_ids if l.state=="draft"]
                for  c in data:
                    c.send_to_verify()
                rec.state = 'admission'

    def approve_all(self):
        for a in self.admission_ids:
            if a.state=='verification':
                a.approve_application()

    def approve_all(self):
        for a in self.admission_ids:
            if a.state=='verification':
                a.approve_application()

    def close_register(self):
        for rec in self:
            for ad in rec.admission_ids:
                if ad.state not in ['approve','reject']:
                    raise ValidationError(
                    _("Veuillez d'abord approuver ou rejeter toutes les candidatures"))
            rec.state = 'done'
