# -*- coding: utf-8 -*-

from odoo import models, fields, api,tools, _
import logging
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger("++++++++++++++")

class AdmissiRegistre(models.Model):
    """
    Modèle pour ajouter les matière dans le régistre 
    """
    _inherit = 'siantou.session.registre'

    matiere_ids = fields.Many2many('education.subject',
    domain=[('type_subject','=','enter')],
    string='Matière', required=True, tracking=True)

    admission_note_ids = fields.One2many('siantou.ems.admission.run.note', 'registre_id', string='field_name')

    condition_admission_ids = fields.One2many('siantou.ems.condition.admission', 'registre_id')

    date = fields.Date('Date')

    responsable_id = fields.Many2one( 'res.users', string='Responsable',default=lambda self: self.env.uid,readonly=True)

    numero_decision = fields.Char('Numéro de décision')

    def action_validat_note(self): 
        for rec in self:
            rec.state = "deliberation"
            if rec.state == "deliberation":
                return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'success',
                            'message': "Vous venez de passer à la phase de délibération",
                            'next': {'type': 'ir.actions.act_window_close'},
                        }
                    }

    def action_validat(self): 
        for rec in self:
            if not rec.condition_admission_ids:
                raise UserError("Veuillez remplir les conditions")
            for nat in rec.condition_admission_ids:

                candidat_note = self.env['siantou.ems.admission.run.note'].search([('registre_id', '=',rec.id),('nationalite_id', '=',nat.nationality_id.id)])
                for app in candidat_note:
                    if app.rang in range(1,nat.nombre+1):
                        app.candidat_id.verified_by =  self.env.uid
                        app.candidat_id.state = 'approve'
                    elif app.rang in range(nat.nombre,nat.nbre_attente+1):
                        app.candidat_id.verified_by =  self.env.uid
                        app.candidat_id.state = 'waiting'
                    else:
                        app.candidat_id.verified_by =  self.env.uid
                        app.candidat_id.state = 'reject'

            rec.state = "done"
            if rec.state == "done":
                return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'success',
                            'message': "Délibération validée avec succès !",
                            'next': {'type': 'ir.actions.act_window_close'},
                        }
                    }

    def action_get_liste_admi(self):
        """
        Fonction permettant de transférer les données pour imprimer le fichier excel
        """
        for rec in self:
            datas = {}
            res = {}

            res ['id'] = rec.id            
            datas['form'] = res

        return self.env.ref('aft_examen.action_print_liste_admis').report_action(self, data=datas)

    def action_get_liste_waiting(self):
        """
        Fonction permettant de transférer les données pour imprimer le fichier excel
        """
        for rec in self:
            datas = {}
            res = {}

            res ['id'] = rec.id            
            datas['form'] = res

        return self.env.ref('aft_examen.action_print_liste_waiting').report_action(self, data=datas)

    def action_get_liste_student(self):
        """
        Fonction permettant de transférer les données pour imprimer le fichier excel
        """
        for rec in self:
            datas = {}
            res = {}

            res ['id'] = rec.id            
            datas['form'] = res

        return self.env.ref('aft_examen.action_print_admission_resultat').report_action(self, data=datas)

    def get_moyenne_candidat(self):
        """
        Fonction pour transferer l'id du régistre dans le rapport de moyenne
        """

        datas = {}
        res = {}

        res ['id'] = self.id

        datas['form'] = res
        return self.env.ref('aft_examen.action_print_moyenne_candidat').report_action(self, data=datas)

