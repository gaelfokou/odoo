# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging
from odoo.exceptions import UserError, ValidationError
_logger = logging.getLogger("++++++++++++++++++++++++++++++++++++")

class ExamenDeliberationStudent(models.Model):
    """
    Modèle pour gérer les délibérations des notes d'un étudiant d'une classe
    """
    _name = 'siantou.ems.examen.deliberation.student'
    _description = " Modèle pour gérer les délibérations des notes d'un étudiant d'une classe"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char('Code')

    year_id = fields.Many2one('education.academic.year', string='Année Académique Actuelle', required=True)

    anne_academique_new_id = fields.Many2one('education.academic.year', string='Nouvelle année académique')

    anne_academique_ids = fields.Many2many('education.academic.year', string ="Année(s) académique", relation='deli_id')

    field_of_study_id = fields.Many2one('education.filiere', string='Filière', required=True)

    actual_class_id = fields.Many2one('education.class', string='Classe actuelle', required=True)

    date_jury = fields.Date('Date du jury', required=True)

    next_class_id = fields.Many2one('education.class.division', string='Classe suivante')

    pr_jury = fields.Char('Président du jury', required=True)

    vice_pr_jury = fields.Char('Vice-président du jury', required=True)

    members_jury_ids = fields.Many2many('siantou.ems.examen.deliberation.jury', string="Membres du jury", relation='deli_stu_id')

    deli_line_note_etudiant_ids = fields.One2many('siantou.ems.examen.deliberation.lines', 'deli_note_id', string="Lignes de notes de l'étudiant")

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validate', 'Valider'),
        ('confirm', 'Confirmer'),
    ], string='État', default='draft')

    @api.onchange('field_of_study_id')
    def _onchange_class(self):
        for rec in self:
            if rec.field_of_study_id:
                class_ids = self.env['education.class'].search([
                    ('field_of_study_id', '=', rec.field_of_study_id.id),
                    ('level_id.name', 'in', ['L1', 'L2', 'L3'])
                ])
                return {'domain': {'actual_class_id': [('id', 'in', class_ids.ids)]}}
            else:
            # Si aucune filière n'est sélectionnée, supprimer le domaine
                return {'domain': {'actual_class_id': []}}

    @api.onchange('anne_academique_id', 'actual_class_id', 'field_of_study_id')
    def _onchange_student(self):
        for rec in self:
            if rec.year_id and rec.actual_class_id and rec.field_of_study_id:
                # Filtrer les étudiants en fonction de l'année académique, de la classe et de la filière
                etudiant_ids = self.env['siantou.ems.examen.student'].search([
                    ('anne_academique_id', '=', rec.year_id.id),
                    ('class_id.class_id', '=', rec.actual_class_id.id),
                    ('class_id.class_id.field_of_study_id', '=', rec.field_of_study_id.id),
                    ('class_id.class_id.level_id', '=', rec.actual_class_id.level_id.id)  # Filtrer par niveau
                ])

                _logger.info(etudiant_ids)

                # Supprimer les lignes de notes existantes
                rec.deli_line_note_etudiant_ids.unlink()

                # Utiliser un ensemble pour éviter les doublons
                seen_students = set()

                # Ajouter les nouveaux enregistrements de lignes de notes
                for line in etudiant_ids:
                    if line.student_id.id not in seen_students:  # Vérifier si l'étudiant a déjà été ajouté
                        seen_students.add(line.student_id.id)  # Ajouter l'étudiant à l'ensemble

                        new_line = self.env['siantou.ems.examen.deliberation.lines'].create({
                            "student_id": line.student_id.id,
                            "matricule": line.student_id.matricule,
                            "place_of_birth": line.student_id.place_of_birth,
                            "name": line.student_id.name,
                            "date_of_birth": line.student_id.date_of_birth,
                            "deli_note_id": rec.id,  # Associer la ligne à l'enregistrement actuel
                        })

                        # Mise à jour de l'enregistrement associé dans siantou.ems.examen.student
                        aft_exam_student_obj = self.env['siantou.ems.examen.student'].search([
                            ("student_id", "=", line.student_id.id),
                            ("anne_academique_id", "=", rec.year_id.id),
                            ("class_id.class_id", "=", rec.actual_class_id.id)
                        ])

                        if aft_exam_student_obj:
                            for ex in aft_exam_student_obj:
                                ex.deli_stu_line_id = new_line.id  # Utilisez new_line.id ici

                # Mettre à jour le domaine si nécessaire
                return {
                    'domain': {
                        'actual_class_id': [('id', 'in', etudiant_ids.mapped('class_id.class_id.id'))]
                    }
                }

    def _get_average(self, rec, level_id=None):
        """Helper pour calculer la moyenne des notes pour un niveau d'étudiant spécifié ou pour tous les niveaux."""
        averages = {}

        for line in rec.deli_line_note_etudiant_ids:
            # Récupération du niveau de l'étudiant
            niveau = line.student_id.class_id.class_id.level_id

            if niveau not in averages:
                averages[niveau] = []

            # Ajouter les moyennes des notes de l'étudiant
            averages[niveau].extend(st.moyenne for st in line.student_note_ids)

        if level_id:
            # Retourner la moyenne pour un niveau spécifique
            notes = averages.get(level_id, [])
            return sum(notes) / len(notes) if notes else 0
        else:
            # Retourner les moyennes pour tous les niveaux
            return {niveau: (sum(notes) / len(notes) if notes else 0) for niveau, notes in averages.items()}

    def action_validate(self):
        """Fonction pour valider la délibération des étudiants et déterminer leur passage de niveau."""
        for rec in self:
            # Créer un dictionnaire pour stocker les statistiques par étudiant
            student_stats = {}
            _logger.info(f"Longueur rec : {len(rec.deli_line_note_etudiant_ids)}")

            for line in rec.deli_line_note_etudiant_ids:
                student_id = line.student_id.id

                # Initialiser les statistiques pour l'étudiant s'il n'est pas déjà présent
                if student_id not in student_stats:
                    student_stats[student_id] = {
                        'total': 0,
                        'valides': 0,
                        'student_name': line.student_id.name  # Ajoutez le nom de l'étudiant pour plus de clarté
                    }

                # Vérifier si la matière est validée
                for note in line.student_note_ids:
                    _logger.info(f"Traitement de la note: {note.id}")
                    for stu in note.examen_student_line_ids:
                        _logger.info(f"Traitement de l'UE: {stu.id}, Nombre de matières: {len(stu.examen_student_subject_line_ids)}")
                        for exam in stu.examen_student_subject_line_ids:
                            _logger.info(f"Matière: {exam.matiere_parent_id.name}, Validé: {exam.is_validated}")
                            student_stats[student_id]['total'] += 1  # Compter chaque matière
                            # Vérifier si la matière est validée
                            if getattr(exam, 'is_validated', False):
                                student_stats[student_id]['valides'] += 1

                _logger.info(f"Statistiques par étudiant : {student_stats}")

                # Calculer les moyennes des notes pour chaque étudiant
                average_notes = self._get_average(rec)

                level_id = line.student_id.class_id.class_id.level_id
                level = level_id.name

                # Initialiser les pourcentages
                pct_n1 = pct_n2 = pct_n3 = moyenne_n2 = 0
                _logger.info(f"level: {level}")
                if level == 'L1':
                    total_matiere_n1 = student_stats[line.student_id.id]['total']
                    valider_n1 = student_stats[line.student_id.id]['valides']
                    pct_n1 = (valider_n1 / total_matiere_n1 * 100) if total_matiere_n1 > 0 else 0
                    _logger.info("total_matiere_n1: %d", total_matiere_n1)
                    _logger.info("valider_n1: %d", valider_n1)
                    _logger.info("pct_n1: %d", pct_n1)

                    decision = self._determine_decision(pct_n1)
                    line.decision = decision

                elif level == 'L2':
                    total_matiere_n2 = student_stats[line.student_id.id]['total']
                    valider_n2 = student_stats[line.student_id.id]['valides']
                    pct_n2 = (valider_n2 / total_matiere_n2 * 100) if total_matiere_n2 > 0 else 0

                    moyenne_n2 = average_notes.get('L2', 0)  # Récupérer la moyenne pour L2
                    decision = self._determine_decision(pct_n1, pct_n2=pct_n2, moyenne_n2=moyenne_n2)
                    line.decision = decision

                elif level == 'L3':
                    total_matiere_n3 = student_stats[line.student_id.id]['total']
                    valider_n3 = student_stats[line.student_id.id]['valides']
                    pct_n3 = (valider_n3 / total_matiere_n3 * 100) if total_matiere_n3 > 0 else 0

                    decision = self._determine_decision(pct_n1, pct_n2=None, pct_n3=pct_n3)
                    line.decision = decision

                # Log de la décision prise
                _logger.info("Décision pour l'étudiant %s (%s): %s", line.student_id.name, level, line.decision)

            rec.state = "validate"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': "Délibération validée avec succès!",
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def _determine_decision(self, pct_n1, pct_n2=None, pct_n3=None,moyenne_n2=None):
        """Détermine la décision basée sur les pourcentages de validation."""
        for rec in self:
            for line in rec.deli_line_note_etudiant_ids:
                level_id = line.student_id.class_id.class_id.level_id
                level = level_id.name

                if level == 'L1':
                    _logger.info("eccccccccccccccc %s", pct_n1)
                    if pct_n1 == 100:
                        return "Passe en classe supérieure (ADD)"
                    elif 75 <= pct_n1 < 100:
                        return "Reprise (ADR)"
                    else:
                        return "Ajourné"

                elif level == 'L2':
                    if pct_n1 == 100 and pct_n2 == 100:
                        return "Passe en classe supérieure (ADD)"
                    elif pct_n1 == 100 and 75 <= pct_n2 < 100 and moyenne_n2 >= 13:
                        return "Reprise (ADR)"
                    else:
                        return "Ajourné"

                elif level == 'L3':
                    if pct_n1 == 100 and pct_n2 == 100 and pct_n3 == 100:
                        return "Passe en classe supérieure (ADD)"
                    elif pct_n1 == 100 and pct_n2 == 100 and pct_n3 < 100:
                        return "ASM (Admis à soutenir son mémoire)"
                    else:
                        return "Ajourné"

    def action_confirm(self):
        """Fonction pour confirmer et inscrire les étudiants dans la classe suivante ou dans la même classe pour reprise."""
        for rec in self:
            if rec.anne_academique_new_id.id == rec.year_id.id:
                raise ValidationError("L'année actuelle doit être différente de l'année suivante")

            student_history = self.env['education.class.history']  # Initialiser le modèle d'historique des étudiants

            for line in rec.deli_line_note_etudiant_ids:
                # Inscription dans la classe supérieure ou maintien dans la même classe
                if line.decision == "Passe en classe supérieure (ADD)":
                    line.student_id.class_id = rec.next_class_id.id  # Inscrire dans la classe supérieure
                elif line.decision == "Reprise (ADR)":
                    line.student_id.class_id.class_id = rec.actual_class_id.id  # Rester dans la même classe

                    # Réinscrire l'étudiant pour les matières à rattraper
                    subjects_to_retake = []
                    for note_line in line.student_note_ids:
                        for stu_line in note_line.examen_student_line_ids:
                            for sub_line in stu_line.examen_student_subject_line_ids:
                                if not sub_line.is_validated:
                                    matiere_ids = [sub_line.matiere_parent_id.id]
                                    existing_subject = next((s for s in subjects_to_retake if s['student_id'] == line.student_id.id and s['class_id'] == line.student_id.class_id.id and s['academic_year_id'] == rec.anne_academique_new_id.id), None)
                                    if existing_subject:
                                        existing_subject['matiere_parent_id'] = existing_subject.get('matiere_parent_id', []) + matiere_ids
                                    else:
                                        subjects_to_retake.append({
                                            'student_id': line.student_id.id,
                                            'class_id': line.student_id.class_id.id,
                                            'academic_year_id': rec.anne_academique_new_id.id,
                                            'matiere_parent_ids': matiere_ids,
                                        })

                    for subject in subjects_to_retake:
                        self.env['oe.school.student.enrollment'].create(subject)

            # Création de l'historique des étudiants après avoir traité toutes les lignes
            for line in rec.deli_line_note_etudiant_ids:
                if not line.student_id:
                    _logger.warning("Student ID is missing for line %s", line)

                if rec.actual_class_id and rec.year_id:
                    vals = {
                        "student_id": line.student_id.id,
                        "class_id": rec.actual_class_id.id,
                        "academic_year_id": rec.year_id.id
                    }
                    # Créer l'historique de l'étudiant
                    student_history.create(vals)
                else:
                    _logger.warning("Les informations nécessaires sont manquantes pour l'étudiant %s", line.student_id.name)

            rec.state = "confirm"  # Changer l'état de la délibération

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': "Confirmation réussie!",
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

    def action_get_pv_pdf(self): 
        """
        Fonction permettant de transférer les données vers le report PDF
        """
        for rec in self:
            datas = {}
            res = {}
            res['id'] = rec.id

            # Prepare data for the report
            datas['form'] = res

        return self.env.ref('aft_examen.action_print_pv_pdf').report_action(self, data=datas)

class ExamenDeliberationLines(models.Model):
    """
    Modèle pour gérer les lignes de délibérations des notes d'un étudiant d'une classe
    """
    _name = 'siantou.ems.examen.deliberation.lines'
    _description = " Modèle pour gérer les membres du jury"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    student_id = fields.Many2one('oe.school.student', string='Etudiant', tracking=True)

    matricule = fields.Char('Matricule', related='student_id.matricule', tracking=True)

    place_of_birth = fields.Char(string="Lieu de Naissance", related='student_id.place_of_birth', required=True)

    name = fields.Char('Nom', related='student_id.name', tracking=True)

    last_name = fields.Char('Prénom(s)', related='student_id.last_name', tracking=True)

    date_of_birth = fields.Date(string="Date de Naissance", related='student_id.date_of_birth', requird=True)

    student_note_ids = fields.One2many('siantou.ems.examen.student', string='Notes de l\'étudiants', inverse_name='deli_stu_line_id')

    deli_note_id = fields.Many2one(string='Délibération des notes', comodel_name='siantou.ems.examen.deliberation.student')

    decision = fields.Char('Décision', readonly=True)  # Champ pour stocker la décision

    moyenne = fields.Float(compute='_compute_moyenne', store=True)

    mention = fields.Selection([
        ('Assez bien', 'Assez bien'),
        ('Bien', 'Bien'),
        ('Passable', 'Passable'),
        ('Très Bien', 'Très Bien'),       
    ], string='Mention',store=True, readonly=True,compute="_compute_mention")

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validate', 'Valider'),
        ('confirm', 'Confirmer'),
    ], string='state', default='draft')

    @api.depends('student_note_ids')
    def _compute_moyenne(self):
        _logger.info("Calculating total average")

        for rec in self:
            total_moyenne = 0
            note_count = len(rec.student_note_ids)

            # Sum the averages of all student notes
            for note in rec.student_note_ids:
                total_moyenne += note.moyenne

            # Calculate the average if there are notes
            rec.moyenne = total_moyenne / note_count if note_count > 0 else 0

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

    def action_modifier_note_deliberation(self):
        _logger.info("Action de modification des notes appelée pour l'étudiant: %s", self.student_id.name)

        for rec in self:
            # Rechercher les notes de l'étudiant
            subject_lines = self.env['siantou.ems.examen.student'].search([
                ('student_id', '=', rec.student_id.id)
            ])

            _logger.info("Notes trouvées: %s", subject_lines.ids)

            # Vérifier si des notes existent
            if not subject_lines:
                raise UserError("Pas de note.")
            else:
                # Ouvrir la fenêtre pour modifier les notes
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Modifier Notes des Matières',
                    'res_model': 'siantou.ems.examen.student',
                    'view_mode': 'tree,form',
                    'domain': [('id', 'in', subject_lines.ids)],
                    'target': 'current',
                }

class ExamenDeliberationJury(models.Model):
    """
    Modèle pour gérer les délibérations des notes d'un étudiant d'une classe
    """
    _name = 'siantou.ems.examen.deliberation.jury'
    _description = " Modèle pour gérer les membres du jury"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char('Nom du membre du jury')

    fonction = fields.Char('Fonction du membre du jury')

    note = fields.Float('Note du membre du jury')

    description = fields.Char('Description')

    deli_stu_id = fields.Many2one(string='Délibération des étudiants', comodel_name='siantou.ems.examen.deliberation.student')

