# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging
from odoo.exceptions import UserError, ValidationError
_logger = logging.getLogger("+++++++++++++++++++++")

class ExamenStudent(models.Model):
    """
    Modèle pour calculer les données d'examen d'un étudiant
    """
    _name = 'siantou.ems.examen.student'
    _description = " Modèle pour calculer les données d'examen d'un étudiant"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char('code')
    
    student_id = fields.Many2one('oe.school.student', string='Etudiant', required=True, tracking=True)

    semestre_id = fields.Many2one('education.semestre', string='Semestre', required=True, tracking=True)

    class_id = fields.Many2one('education.class.division', string='Classe', required=True, tracking=True)

    anne_academique_id = fields.Many2one('education.academic.year', string='Année académique',  required=True, tracking=True)

    examen_planifier_id = fields.Many2one('siantou.ems.examen.plannifier')

    deli_stu_line_id = fields.Many2one(string='Délibération des lines étudiants', comodel_name='siantou.ems.examen.deliberation.lines')
    
    tpe_exame = fields.Char('')
    
    rang = fields.Integer('Rang',compute="_compute_rang")
    
    credit = fields.Float('Crédit',store=True,compute="_compute_credit")

    # pourcentage_valid = fields.Float(compute='_compute_pourcentage_validation', store=True)

    moyenne = fields.Float('Moyenne',store=True, compute="_compute_moyenne")

    examen_student_line_ids = fields.One2many('siantou.ems.examen.student.moyenne.line', 'examen_student_id', "line")

    decision = fields.Selection([
        ('Semestre validé', 'Semestre validé'),
        ('Semestre non validé', 'Semestre non validé'),
    ], string='decision', readonly=True, compute="_compute_decision")
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validate', 'Valider'),
        ('confirm', 'Confirmer'),
    ], string='state', 
    default='draft'
    )

    stat = fields.Selection([
        ('Valider', 'Valider'),
        ('Échec', 'Échec'),
    ], string='Décision du jury',store=True, compute="_compute_stat")

    session = fields.Selection([
        ('SN', 'Séssion normale'),
        ('SR', 'Séssion de rattrapage'),
    ], string='Séssion', default='SN')
    
    mention = fields.Selection([
        ('Assez bien', 'Assez bien'),
        ('Bien', 'Bien'),
        ('Passable', 'Passable'),
        ('Très Bien', 'Très Bien'),       
    ], string='Mention',store=True, readonly=True,compute="_compute_mention")

    moyenne_annuelle = fields.Float('Moyenne Annuelle', compute='_compute_statistiques_annuelles', store=True)
    pourcentage_reussite = fields.Float('Pourcentage de Réussite', compute='_compute_statistiques_annuelles', store=True)

    nb_matieres_a_rattraper = fields.Integer(string="Nombre de matières à rattraper", compute="_compute_matieres_a_rattraper", store=True)
    a_des_rattrapages = fields.Boolean(string="A des rattrapages", compute="_compute_matieres_a_rattraper", store=True)

    nb_etudiants_avec_rattrapages = fields.Integer(string="Nombre d'étudiants avec rattrapages", compute='_compute_nb_etudiants_avec_rattrapages', store=True)

    is_graduate = fields.Boolean('Est diplômé', compute='_compute_is_graduate', store=True)

    
    
    @api.depends('moyenne')
    def _compute_decision(self):
        for rec in self:
            rec.decision = ''
            if rec.moyenne and rec.credit:
                if rec.credit >= 30 and rec.moyenne >= 10:
                    rec.decision = "Semestre validé"
                else:
                    rec.decision = "Semestre non validé"
                    
    @api.depends('moyenne')
    def _compute_mention(self):
        for rec in self:
            if rec.moyenne:
                if rec.moyenne >=12 and rec.moyenne <= 13.99:
                    rec.mention = "Passable"
                elif rec.moyenne >=14 and rec.moyenne <= 14.99:
                    rec.mention = "Assez bien"
                elif rec.moyenne >=15 and rec.moyenne <= 16.99:
                    rec.mention = "Bien"
                elif rec.moyenne >= 16:
                    rec.mention = "Très Bien"

    
    @api.depends('credit')
    def _compute_stat(self):
        """
        Fonction pour déterminer si une personne a valider 
        """
        for rec in self:
            if rec.credit:
                if rec.credit >= 30:
                    rec.stat = "Valider"
                else:
                    rec.stat = "Échec"
    
    
    def action_validate(self):
        """
        fonction pour valider les actions
        """
        for rec in self:
            rec.state = "validate"

    def action_confirm(self):
        """
        fonction pour confirmer les actions
        """
        liste = []
        for rec in self:
            resultat = self.env["siantou.ems.examen.plannifier"].search([("id","=",rec.examen_planifier_id.id)])
            for emp in resultat.line_examen_ids:
                liste.append(emp.unite_enseignement_id.id)
            liste = set(liste)
            for ue in liste:
                rec.examen_student_line_ids.create({
                    "ue_id" : ue,
                    "examen_student_id" : rec.id })
            rec.examen_student_line_ids.action_confirm()

    @api.depends('examen_student_line_ids')
    def _compute_credit(self):
        for rec in self:
            rec.credit = 0
            if rec.examen_student_line_ids:
                for cd in rec.examen_student_line_ids:
                    rec.credit += cd.credit
    
    @api.depends('credit')  # Dépend uniquement du crédit
    def _compute_pourcentage_validation(self):
        for rec in self:
            rec.pourcentage_valid = (rec.credit * 30) / 100

                    
    @api.depends('examen_student_line_ids', 'credit')
    def _compute_moyenne(self):
        for rec in self:
            rec.moyenne = 0
            som = 0
            som_credit = 0
            if rec.examen_student_line_ids:
                for cd in rec.examen_student_line_ids:
                    for emp in cd.examen_student_subject_line_ids:     
                        som += emp.moyenne_matiere_parent * emp.coeficeint
                        som_credit += emp.coeficeint

            # Vérifier si som_credit est supérieur à zéro pour éviter la division par zéro
            if som_credit > 0:
                rec.moyenne = round(som / som_credit, 2)
            else:
                rec.moyenne = 0  # Ou une autre valeur par défaut si tu le souhaites
            
            
    
    @api.depends('moyenne')
    def _compute_rang(self):
        for rec in self:
            rec.rang = 0
            candidat_ids = self.search([("anne_academique_id","=", rec.anne_academique_id.id),("class_id","=", rec.class_id.id),("semestre_id","=", rec.semestre_id.id)])
            notes = candidat_ids.sorted(lambda r: r.moyenne,reverse=True)
            for pos in range(len(notes)):
                if notes[pos].id == rec.id:
                    rec.rang = pos+1
    
    @api.depends('examen_student_line_ids', 'examen_student_line_ids.moyenne_ue', 'examen_student_line_ids.credit')
    def _compute_statistiques_annuelles(self):
        for student in self:
            total_credits = sum(line.credit for line in student.examen_student_line_ids)
            total_points = sum(line.moyenne_ue * line.credit for line in student.examen_student_line_ids)
            
            if total_credits > 0:
                student.moyenne_annuelle = total_points / total_credits
            else:
                student.moyenne_annuelle = 0

            ues_validees = len([line for line in student.examen_student_line_ids if line.statut == 'valid'])
            total_ues = len(student.examen_student_line_ids)
            
            if total_ues > 0:
                student.pourcentage_reussite = (ues_validees / total_ues) * 100
            else:
                student.pourcentage_reussite = 0

    def action_voir_statistiques(self):
        return {
            'name': 'Statistiques Annuelles',
            'view_mode': 'tree,form',
            'res_model': 'siantou.ems.examen.student',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.ids)],
            'context': {'tree_view_ref': 'aft_examen.view_aft_examen_student_statistiques_tree'},
        }

    @api.depends('examen_student_line_ids', 'examen_student_line_ids.examen_student_subject_line_ids', 'examen_student_line_ids.examen_student_subject_line_ids.statut')
    def _compute_matieres_a_rattraper(self):
        for student in self:
            matieres_a_rattraper = student.examen_student_line_ids.mapped('examen_student_subject_line_ids').filtered(lambda x: x.statut in ['rpo', 'rpf'])
            student.nb_matieres_a_rattraper = len(matieres_a_rattraper)
            student.a_des_rattrapages = bool(matieres_a_rattraper)

    @api.depends('a_des_rattrapages')
    def _compute_nb_etudiants_avec_rattrapages(self):
        for record in self:
            record.nb_etudiants_avec_rattrapages = 1 if record.a_des_rattrapages else 0

    @api.depends('class_id', 'stat', 'moyenne_annuelle')
    def _compute_is_graduate(self):
        for student in self:
            niveau = student.class_id.class_id.level_id.name
            if niveau in ['L3', 'M2', 'D']:
                student.is_graduate = (
                    student.stat == 'Valider' and
                    student.moyenne_annuelle >= 10
                )
            else:
                student.is_graduate = False

    def action_print_attestation(self):
        return self.env.ref('aft_examen.action_print_attestation_reussite').report_action(self)

class ExamenStudentLine(models.Model):
    """
    Modèle pour les lignes de calculer les données d'examen d'un étudiant
    """
    _name = "siantou.ems.examen.student.moyenne.line"
    _description = "Modèle pour les lignes de calculer les données d'examen d'un étudiant"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    ue_id = fields.Many2one('education.unite.enseignement', string="Unité d'enseignement")

    moyenne_ue = fields.Float('Moyenne',store=True,compute='_compute_moyenne')

    credit = fields.Float('Credit', store=True,compute='_compute_credit')

    statut = fields.Selection([
        ('rpo', 'Rattrapage obligatoire'),
        ('rpf', 'Rattrapage facultatif'),
        ('valid', 'Valider'),
        ('ajour', 'Ajourner')
    ], string='statut')

    examen_student_id = fields.Many2one('siantou.ems.examen.student')

    examen_student_subject_line_ids = fields.One2many('siantou.ems.examen.student.subject.parent', 'examen_student_line_id')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validate', 'Valider'),
        ('confirm', 'Confirmer')
    ], string='Statue', default="draft")

    def action_validate(self):
        """
        fonction pour valider les actions
        """
        for rec in self:
            rec.state = "validate"
    def action_confirm(self):
        """
        fonction pour confirmer les actions
        """
        for rec in self:
            liste = {}
            results = self.env["siantou.ems.examen.registre.line"].search([
                ("unite_enseignement_id","=",rec.ue_id.id),
                ("semestre_id","=",rec.examen_student_id.semestre_id.id),
                ("class_id","=",rec.examen_student_id.class_id.id),
                ("anne_academique_id","=",rec.examen_student_id.anne_academique_id.id)])
            
            for mat in results:
                if mat.matiere_id.under_subject_id.id not in liste.keys():
                    liste[mat.matiere_id.under_subject_id.id]={}
                    liste[mat.matiere_id.under_subject_id.id]["liste"]=[]
                    liste[mat.matiere_id.under_subject_id.id]["liste"].append({
                        "matiere_parent_id" : mat.matiere_id.under_subject_id.id,
                        "matiere_id" : mat.matiere_id.id,
                        "coeficeint" : mat.coeficien,
                        "examen_student_line_id" : rec.id
                    })
                    
                    
            for line in liste.values():
                for value in line["liste"]:
                    rec.examen_student_subject_line_ids.create({
                        "matiere_parent_id" : value["matiere_parent_id"],
                        "examen_student_line_id" : value["examen_student_line_id"]})
            rec.examen_student_subject_line_ids.action_confirm()
        
    @api.depends('examen_student_subject_line_ids')
    def _compute_credit(self):
        for rec in self:
            rec.credit = 0
            if rec.examen_student_subject_line_ids:
                for cd in rec.examen_student_subject_line_ids:
                    if cd.statut == "rpo":
                        rec.credit = 0
                        rec.statut = "rpo"
                        break
                    rec.credit += cd.coeficeint

                for cd in rec.examen_student_subject_line_ids:
                    if cd.statut == "rpf":
                        rec.statut = "rpf"
                        break
                        
    
    @api.depends('examen_student_subject_line_ids')
    def _compute_moyenne(self):
        for rec in self:
            rec.moyenne_ue = 0
            som = 0
            som_credit = 0
            if rec.examen_student_subject_line_ids:
                for emp in rec.examen_student_subject_line_ids:        
                    som += emp.moyenne_matiere_parent * emp.coeficeint
                    som_credit += emp.coeficeint
            rec. moyenne_ue = som / som_credit

class ExamenStudentMatiereParent(models.Model):
    """
    Modèle permettant de concerver les notes par matière d'un étudiant
    """
    _name = "siantou.ems.examen.student.subject.parent"
    _description = " Modèle permettant de concerver les notes par matière parent d'un étudiant"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    matiere_parent_id = fields.Many2one('education.under.subject', string='Matière')

    moyenne_matiere_parent = fields.Float('Moyenne', store=True,compute="_compute_moyenne_matiere_parent")

    examen_student_line_id = fields.Many2one('siantou.ems.examen.student.moyenne.line')

    examen_student_subject_ids = fields.One2many('siantou.ems.examen.student.subject', 'examen_student_parent_subject_id')

    coeficeint = fields.Float('Coéficient', compute = "_compute_credit_parent")

    student_id = fields.Many2one(
        'siantou.ems.examen.student', 
        string='Étudiant', 
        required=True,
        ondelete='cascade'
    )
    
    pourcentage_validation = fields.Float('Pourcentage de validation', store=True, compute='_compute_pourcentage_validation')

    is_validated = fields.Boolean('Validé', compute='_compute_is_validated')

    @api.depends('moyenne_matiere_parent')
    def _compute_is_validated(self):
        for rec in self:
            rec.is_validated = rec.moyenne_matiere_parent >= 10  # Supposons que la moyenne_matiere_parent minimale pour valider est 10
    
    statut = fields.Selection([
        ('rpo', 'Rattrapage obligatoire'),
        ('rpf', 'Rattrapage facultatif'),
        ('valid', 'Valider'),
        ('ajour', 'Ajourner')
    ], string='statut', compute="_compute_state")

    
    state = fields.Selection([
    ('draft', 'Brouillon'),
    ('validate', 'Valider'),
    ('confirm', 'Confirmer')
    ], string='Statue', default="draft")
    

    @api.depends('examen_student_subject_ids')
    def _compute_pourcentage_validation(self):
        for rec in self:
            total_matiere_parent = len(rec.examen_student_subject_ids)
            matiere_parent_valide = len(rec.examen_student_subject_ids.filtered(lambda x: x.statut in ['valid', 'rpf']))
            rec.pourcentage_validation = (matiere_parent_valide / total_matiere_parent) * 100 if total_matiere_parent > 0 else 0


    def action_validate(self):
        """
        fonction pour valider les actions
        """
        for rec in self:
            rec.state = "validate"
            
    def action_confirm(self):
        """
        fonction pour confirmer les actions
        """
        for rec in self:
            liste = {}
            results = self.env["siantou.ems.examen.registre.line"].search([
                ("unite_enseignement_id","=",rec.examen_student_line_id.ue_id.id),
                ("semestre_id","=",rec.examen_student_line_id.examen_student_id.semestre_id.id),
                ("class_id","=",rec.examen_student_line_id.examen_student_id.class_id.id),
                ("anne_academique_id","=",rec.examen_student_line_id.examen_student_id.anne_academique_id.id),
                ("matiere_id.under_subject_id", "=", rec.matiere_parent_id.id)])
            
            for mat in results:
                if mat.matiere_id.id not in liste.keys():
                    liste[mat.matiere_id.id]={}
                    liste[mat.matiere_id.id]["liste"]=[]
                    liste[mat.matiere_id.id]["liste"].append({
                        "matiere_id" : mat.matiere_id.id,
                        "coeficeint" : mat.coeficien,
                        "examen_student_parent_subject_id" : rec.id
                    })
                    
                    
            for line in liste.values():
                for value in line["liste"]:
                    rec.examen_student_subject_ids.create({
                        "matiere_id" : value["matiere_id"],
                        "coeficeint" : value["coeficeint"],
                        "examen_student_parent_subject_id" : value["examen_student_parent_subject_id"]})
            rec.examen_student_subject_ids.action_confirm()


    @api.depends('examen_student_subject_ids')
    def _compute_credit_parent(self):
        for rec in self:
            som_credit = 0
            if rec.examen_student_subject_ids:
                for emp in rec.examen_student_subject_ids:        
                    som_credit += emp.coeficeint
            rec.coeficeint = som_credit
            _logger.info(rec.coeficeint)

    @api.depends('examen_student_subject_ids', 'coeficeint')
    def _compute_moyenne_matiere_parent(self):
        for rec in self:
            total_moyenne = 0
            total_credit = 0
            if rec.examen_student_subject_ids:
                for moyenn in rec.examen_student_subject_ids:
                    total_moyenne += moyenn.moyenne_matiere * moyenn.coeficeint
                    total_credit += moyenn.coeficeint
                # Calcul de la moyenne des sous-matières
                rec.moyenne_matiere_parent = total_moyenne / total_credit

            _logger.info(rec.moyenne_matiere_parent)
            
    
    @api.depends('moyenne_matiere_parent','examen_student_line_id')
    def _compute_state(self):
        for rec in self:
            rec.statut = "valid"
            for moyenn in  rec.examen_student_subject_ids:
                for moy in moyenn.examen_student_subject_ids:
                    if rec.moyenne_matiere_parent and rec.examen_student_line_id:
                        if rec.moyenne_matiere_parent < 10:
                            rec.statut = "rpo"
                            rec.examen_student_line_id.statut = "rpo"
                        elif rec.moyenne_matiere_parent < 10 and rec.examen_student_line_id.moyenne_ue < 12:
                            rec.statut = "rpo"
                            rec.examen_student_line_id.statut = "rpo"
                        elif rec.moyenne_matiere_parent < 10 and rec.examen_student_line_id.moyenne_ue >= 12:
                            rec.statut = "rpf"
                            rec.examen_student_line_id.statut = "rpf"
                        elif rec.moyenne_matiere_parent < 10 and moy.type_examen_id.code == "SR":
                            rec.statut = "ajour"
                            rec.examen_student_line_id.statut = "ajour"
                        elif rec.moyenne_matiere_parent <= 10 and rec.examen_student_line_id.moyenne_ue < 12 and moy.type_examen_id.code == "SR":
                            rec.statut = "ajour"
                            rec.examen_student_line_id.statut = "ajour"
                        else:
                            rec.statut = "valid"
                            rec.examen_student_line_id.statut = "valid"
    
class ExamenStudentMatiere(models.Model):
    """
    Modèle permettant de concerver les notes par matière d'un étudiant
    """
    _name = "siantou.ems.examen.student.subject"
    _description = " Modèle permettant de concerver les notes par matière d'un étudiant"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    matiere_id = fields.Many2one('education.subject', string='Matière')

    moyenne_matiere = fields.Float('Moyenne', store=True,compute="_compute_moyenne_matiere")

    examen_student_parent_subject_id = fields.Many2one('siantou.ems.examen.student.subject.parent')

    examen_student_subject_ids = fields.One2many('siantou.ems.examen.student.subject.line', 'examen_student_subject_id')

    coeficeint = fields.Float('Coéficient')
    
    
    statut = fields.Selection([
        ('rpo', 'Rattrapage obligatoire'),
        ('rpf', 'Rattrapage facultatif'),
        ('valid', 'Valider'),
        ('ajour', 'Ajourner')
    ], string='statut', compute="_compute_state")

    
    state = fields.Selection([
    ('draft', 'Brouillon'),
    ('validate', 'Valider'),
    ('confirm', 'Confirmer')
    ], string='Statue', default="draft")
    

    def action_validate(self):
        """
        fonction pour valider les actions
        """
        for rec in self:
            rec.state = "validate"
    def action_confirm(self):
        """
        fonction pour confirmer les actions
        """
        for rec in self:
            results = self.env["siantou.ems.examen.student.line"].search([
                ("examen_student_number_id.matiere_id","=",rec.matiere_id.id),
                ("student_id","=",rec.examen_student_parent_subject_id.examen_student_line_id.examen_student_id.student_id.id),
                ("examen_student_number_id.class_id","=",rec.examen_student_parent_subject_id.examen_student_line_id.examen_student_id.class_id.id),
                ("examen_student_number_id.anne_academique_id","=",rec.examen_student_parent_subject_id.examen_student_line_id.examen_student_id.anne_academique_id.id)
                ])
            for note in results:
                rec.examen_student_subject_ids.create({
                    "type_examen_id" : note.examen_student_number_id.type_examen_id.id,
                    "note" : note.note,
                    "pourcentage" : note.examen_student_number_id.Pourcentage,
                    "examen_student_subject_id" : rec.id
                })

    @api.depends('examen_student_subject_ids')
    def _compute_moyenne_matiere(self):
        for rec in self:
            rec.moyenne_matiere = 0
            for moyenn in rec.examen_student_subject_ids:
                rec.moyenne_matiere += moyenn.moyenne_type_examne
    
    
    @api.depends('moyenne_matiere','examen_student_parent_subject_id')
    def _compute_state(self):
        for rec in self:
            rec.statut = "valid"
            for moyenn in  rec.examen_student_subject_ids:
                if rec.moyenne_matiere and rec.examen_student_parent_subject_id.examen_student_line_id:
                    if rec.moyenne_matiere < 5 :
                        rec.statut = "rpo"
                        rec.examen_student_parent_subject_id.examen_student_line_id.statut = "rpo"
                    elif rec.moyenne_matiere >= 5 and rec.moyenne_matiere < 10 and rec.examen_student_parent_subject_id.examen_student_line_id.moyenne_ue < 12:
                        rec.statut = "rpo"
                        rec.examen_student_parent_subject_id.examen_student_line_id.statut = "rpo"
                    elif rec.moyenne_matiere > 10 and rec.examen_student_parent_subject_id.examen_student_line_id.moyenne_ue < 12:
                        rec.statut = "rpo"
                        rec.examen_student_parent_subject_id.examen_student_line_id.statut = "rpo"
                    elif rec.moyenne_matiere >= 5 and rec.moyenne_matiere < 10 and rec.examen_student_parent_subject_id.examen_student_line_id.moyenne_ue >= 12:
                        rec.statut = "rpf"
                        rec.examen_student_parent_subject_id.examen_student_line_id.statut = "rpf"
                    elif rec.moyenne_matiere < 10 and moyenn.type_examen_id.code == "SR":
                        rec.statut = "ajour"
                        rec.examen_student_parent_subject_id.examen_student_line_id.statut = "ajour"
                    elif rec.moyenne_matiere >= 5 and rec.moyenne_matiere <= 10 and rec.examen_student_parent_subject_id.examen_student_line_id.moyenne_ue < 12 and moyenn.type_examen_id.code == "SR":
                        rec.statut = "ajour"
                        rec.examen_student_parent_subject_id.examen_student_line_id.statut = "ajour"
                    else:
                        rec.statut = "valid"
                        rec.examen_student_parent_subject_id.examen_student_line_id.statut = "valid"

    
class ExamenStudentMatiereLine(models.Model):
    """
    Modèle des ligne permettant de concerver les notes par matière d'un étudiant
    """
    _name = "siantou.ems.examen.student.subject.line"
    _description = "  Modèle des ligne permettant de concerver les notes par matière d'un étudiant"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    type_examen_id = fields.Many2one('siantou.ems.type.examen', string="Type d'examen")
    
    pourcentage = fields.Integer('Pourcentage')
    
    note = fields.Float('note')

    moyenne_type_examne = fields.Float('Moyenne',store=True,compute='_compute_moyenne_type_examne')
    
    examen_student_subject_id = fields.Many2one('siantou.ems.examen.student.subject')
    
    examen_student_under_subject_id = fields.Many2one('siantou.ems.examen.student.subject.parent')

    @api.depends('pourcentage','note')
    def _compute_moyenne_type_examne(self):
        for rec in self:
            rec.moyenne_type_examne = 0
            rec.moyenne_type_examne = ((rec.note * rec.pourcentage) / 100)
    
    
    
