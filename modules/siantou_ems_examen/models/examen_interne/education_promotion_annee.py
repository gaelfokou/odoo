from odoo import api,fields,models, _
from odoo.exceptions import UserError,ValidationError

import logging

_logger = logging.getLogger("++++============")

try:
  import qrcode
except ImportError:
  qrcode = None
try:
  import base64
except ImportError:
  base64 = None
from io import BytesIO

class AnneeAcademique(models.Model):

    """Pour faire passer un étudiant d'une salle à l'autre durant une annéé"""
    _name = 'anee.academique'
    _description ="Pour faire passer un étudiant d'une salle à l'autre durant une annéé"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('code')

    anne_academique = fields.Many2one('education.academic.year',string ='Année Académique', required=True)

    anne_academique_new = fields.Many2one('education.academic.year',string ='Nouvelle année académique')

    actual_class_id = fields.Many2one('education.class.division', string='Classe actuelle')

    next_class_id = fields.Many2one('education.class.division', string='Classe suivante')

    date_jury = fields.Date('Date du jury')

    pr_jury = fields.Char('Président du jury')

    note_etudiant_ids = fields.One2many('note.etudiants', 'gest_aca_id', string="Note de l'étudiant")

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validate', 'valider'),
        ('confirm', 'Confirmer'),
    ], string='state', default="draft")

    def action_validate(self):
        """
        Fonctionpour valider
        """
        liste = {}
        for rec in self:
            num = self.env["ir.sequence"].next_by_code("aft_formation.promotion")
            rec.name = num
            result_semestre = self.env["siantou.ems.examen.student"].search([("anne_academique_id","=",rec.anne_academique.id),("class_id","=",rec.actual_class_id.id)])
            for line in result_semestre:
                note = 1
                if line.student_id.id not in liste.keys():
                    liste[line.student_id.id] ={}
                    liste[line.student_id.id]["name"] = line.student_id.id
                    liste[line.student_id.id]["moyenne"] = line.moyenne
                    liste[line.student_id.id]["credit"] = line.credit
                    liste[line.student_id.id]["div"] = note

                else:
                    liste[line.student_id.id]["credit"] += line.credit
                    liste[line.student_id.id]["moyenne"] += line.moyenne
                    liste[line.student_id.id]["div"] += note

            for emp in  liste.values():    
                rec.note_etudiant_ids = [(
                        0,
                        0,
                        {
                            "student_id": emp["name"],
                            "moyenne": emp["moyenne"] / emp["div"],
                            "credit": emp["credit"],
                        },
                    )
                ]

            rec.state ="validate"
            if rec.state == "validate":
                return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'success',
                            'message': "Promotion validée avec succès!",
                            'next': {'type': 'ir.actions.act_window_close'},
                        }
                    }

    def action_confim(self):
        """
        Fonction pour confirmer
        """
        for rec in self:
            if rec.anne_academique_new.id  == rec.anne_academique.id:
                raise ValidationError("L'anneé atuelle doit être différente de l'année suivante")

            for line in rec.note_etudiant_ids:
                if line.statut == "Valider":
                    line.student_id.class_id = rec.next_class_id.id
            rec.action_créate_historyt()      
            rec.state = "confirm"
            if rec.state == "confirm":
                return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'success',
                            'message': "Promotion confirmée avec succès!",
                            'next': {'type': 'ir.actions.act_window_close'},
                        }
                    }

    def action_créate_historyt(self):

        """
        Fonction pour créer l'historique des étudiants
        """
        student_history = self.env['education.class.history']
        for rec in self:
            for line in rec.note_etudiant_ids:
                vals = {
                    "student_id":line.student_id.id,
                    "class_id": rec.actual_class_id.id,
                    "field_of_study_id": rec.actual_class_id.class_id.field_of_study_id.id,
                    "level_id":rec.actual_class_id.class_id.level_id.id,
                    "option_id":rec.actual_class_id.class_id.option_id.id,
                    "academic_year_id":rec.anne_academique.id,
                    "mention":line.mention,
                    "statut":line.statut,
                    "date_jury":rec.date_jury
                }

                student_history.create(vals)

class NoteEtudiants(models.Model):

    """ Recupérer les notes de l'étudiant"""
    _name ='note.etudiants'
    _description ="Recupérer les notes de l'étudiant"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    student_id = fields.Many2one('oe.school.student', string='Liste des étudiants', required=True)
    moyenne = fields.Float(string='Moyenne')
    credit = fields.Float(string='Crédit')
    statut = fields.Char('statut', store=True, compute="_compute_statut")
    gest_aca_id = fields.Many2one('anee.academique', string='Année académique')

    mention = fields.Selection([
        ('Assez bien', 'Assez bien'),
        ('Bien', 'Bien'),
        ('Passable', 'Passable'),
        ('Très Bien', 'Très Bien'),       
    ], string='Mention')

    qr_code = fields.Binary("QR Code", compute='generate_qr_code')

    def generate_qr_code(self):
        """
        Fonction pour générer le QR code
        """
        for rec in self:
            if rec.statut == "Valider":
                url_obj = self.env["student.qr.code.liste"].search([
                    ("student_qr_id.state","=","confirm"),
                    ("student_qr_id.classe_id","=",rec.gest_aca_id.actual_class_id.id),
                    ("student_id","=", rec.student_id.id)
                ])
                if url_obj :
                    for line in url_obj:
                        if qrcode and base64:
                            qr = qrcode.QRCode(
                                version=1,
                                error_correction=qrcode.constants.ERROR_CORRECT_L,
                                box_size=3,
                                border=4,
                            )
                            qr.add_data(str(line.lien_qr))
                            qr.make(fit=True)
                            img = qr.make_image()
                            temp = BytesIO()
                            img.save(temp, format="PNG")
                            qr_image = base64.b64encode(temp.getvalue())
                            rec.update({'qr_code': qr_image})
                else:
                    rec.update({'qr_code': False})
            else:
                rec.update({'qr_code': False})

    @api.depends('moyenne','credit')
    def _compute_statut(self):
        for rec in self:
            rec.statut = ""

            if rec.moyenne and rec.credit:
                if rec.moyenne >= 12 and rec.credit >= 30:
                    rec.statut = "Valider"
                else:
                    rec.statut = "Echec"

            if rec.moyenne >=12 and rec.moyenne <= 13.99:
                rec.mention = "Passable"
            elif rec.moyenne >=14 and rec.moyenne <= 14.99:
                rec.mention = "Assez bien"
            elif rec.moyenne >=15 and rec.moyenne <= 16.99:
                rec.mention = "Bien"
            elif rec.moyenne >= 16:
                rec.mention = "Très Bien"

