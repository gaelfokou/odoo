# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger("Logger ==========")


# class RapportFraisEtudiant(models.TransientModel):
# 	_name = 'wizard.frais.etudiant'
# 	_description = "Impression de la liste des Étudiant"

# 	classe_ids = fields.Many2many('siantou.ems.core.field_of_study, string='Classes', required=True)
# 	frais = fields.Selection([('glo', 'Global'), ('cat', 'Par Catégorie')],
#         "type", default='glo',required=True)
# 	cat_ids = fields.Many2many('siantou.ems.fee.category', string='Catégories')

# 	def print_listes(self):
# 		data = {}
# 		data['classes'] = [(reg.id,reg.name) for reg in self.classe_ids]
# 		data['frais'] = self.frais
# 		data['cat_ids'] = [(reg.id,reg.name) for reg in self.cat_ids] if self.frais == 'cat' else []
# 		return self.env.ref('siantou.ems.fee.action_liste_etudiant').report_action(self, data=data)
	


class ScolariteEtudiant(models.TransientModel):
	_name = 'wizard.etudiant.scolarite'
	_description = "Impression de la liste des Étudiant"

	student_id = fields.Many2one('oe.school.student', string='Étudiant',create=False,required=True)
	scolarite = fields.Selection([('normal', 'Normale'), ('reprise', 'Avec reprise'),
         ('complementaire', 'Cours Additionnelles')],string='Scolarité')
	scolaritered = fields.Selection([('redoublant', 'Redoublant'), ('report', 'Report'),
         ('readmission', 'Réadmission')],string='redoublant')
	amount = fields.Monetary(
        'Montant total',  tracking=True)
	currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id, readonly=True, related_sudo=False)
	fee_structure_id = fields.Many2one('siantou.ems.fee.structure',
                                       domain=[('fee_special', '=', True)],
                                       string='Catégorie de frais',  tracking=True)
	# campus = fields.Many2one('siantou.ems.core.campus',
    #     'Campus', related="student_id.admission_class.campus", store=True, tracking=True)
	campus = fields.Many2one(
		'siantou.ems.core.campus',
        'Campus',
		store=True,
		tracking=True
	)
	redoublant = fields.Selection(
        [('oui', 'OUI'), ('non', 'NON')],
        'Redoublant?',related="student_id.redoublant")


	def print_etudiant(self):
		for rec in self:
			if rec.student_id.redoublant == 'oui':
				fee = self.env['siantou.ems.fee.special'].create({     
	                          	'student_id': rec.student_id.id,
                                'fee_structure_id': rec.fee_structure_id.id,
                                'amount': rec.amount,
                            })
				fee.validate_special()
			elif rec.student_id.redoublant == 'non' and rec.scolarite in ['reprise','complementaire','']:
				fee = self.env['siantou.ems.fee.special'].create({     
				'student_id': rec.student_id.id,
				'fee_structure_id': rec.fee_structure_id.id,
                'amount': rec.amount,
					})
				fee.validate_special()