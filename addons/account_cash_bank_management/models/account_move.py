from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    transaction_date = fields.Date(
        string='Transaction Date',
        compute='_compute_transaction_date', store=True, readonly=False,
        index=True,
        precompute=True,
        copy=False,
    )
    type_inclusion_fee = fields.Selection(
        [
            ('fee_inscrip', "Frais d'inscription"),
            ('fee_scol', 'Frais de scolarité'),
            ('fee_spec', 'Frais spéciaux'), 
        ],
        "Catégorie de frais", 
        # required=True,
    )
    ecole_id = fields.Many2one('siantou.ems.core.school', string='École', compute='_compute_school_accounting_axes', readonly=False, store=True)
    departement_id = fields.Many2one('hr.department', string='Département', compute='_compute_school_accounting_axes', readonly=False, store=True)
    field_of_study_id = fields.Many2one('siantou.ems.core.field_of_study', compute='_compute_school_accounting_axes', readonly=False, store=True)
    specialite_id = fields.Many2one('siantou.ems.core.specialty', compute='_compute_school_accounting_axes', readonly=False, store=True)
    year_id = fields.Many2one('siantou.ems.core.year', compute='_compute_school_accounting_axes', readonly=False, store=True)
    cycle_id = fields.Many2one('oe.school.course', compute='_compute_school_accounting_axes', readonly=False, store=True)
    level_id = fields.Many2one('siantou.ems.core.level', compute='_compute_school_accounting_axes', readonly=False, store=True)
    semestre_id = fields.Many2one('siantou.ems.core.year.semester', compute='_compute_school_accounting_axes', readonly=False, store=True)

    @api.depends('statement_line_id.ecole_id',
                 'statement_line_id.departement_id',
                 'statement_line_id.field_of_study_id',
                 'statement_line_id.specialite_id',
                 'statement_line_id.year_id',
                 'statement_line_id.cycle_id',
                 'statement_line_id.level_id',
                 'statement_line_id.semestre_id',)
    def _compute_school_accounting_axes(self):
        for rec in self:
            if rec.statement_line_id:
                rec.ecole_id = rec.statement_line_id.ecole_id
                rec.departement_id = rec.statement_line_id.departement_id
                rec.field_of_study_id = rec.statement_line_id.field_of_study_id
                rec.specialite_id = rec.statement_line_id.specialite_id
                rec.year_id = rec.statement_line_id.year_id
                rec.cycle_id = rec.statement_line_id.cycle_id
                rec.level_id = rec.statement_line_id.level_id
                rec.semestre_id = rec.statement_line_id.semestre_id
                rec.type_inclusion_fee = rec.statement_line_id.type_inclusion_fee

    @api.depends('statement_line_id')
    def _compute_transaction_date(self):
        for move in self:
            if move.statement_line_id:
                move.transaction_date = move.statement_line_id.date

    @api.depends('invoice_date', 'company_id', 'transaction_date')
    def _compute_date(self):
        res = super()._compute_date()
        for move in self:
            if not move.transaction_date:
                if not move.date:
                    move.date = fields.Date.context_today(self)
                continue
            move.date = move.transaction_date
        return res

