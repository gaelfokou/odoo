# -*- coding: utf-8 -*-
from odoo import models, fields, api
from babel.dates import format_date
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger("++++++++++++")



class SecretariatExamen(models.Model):
    _name = 'siantou.ems.examen.secretariat'
    _description = "Model pour gérer les sécretariat des examen"
    _inherit = ["mail.thread", "mail.activity.mixin"]


    name = fields.Char(
        'Libellé', 
        required=True,
    )
    type_examen_id = fields.Many2one(
        'siantou.ems.examen.type',
        string="Type d'examen",
        required=True,
    )
    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année académique', 
        required=True,
        default=lambda self: self.env['siantou.ems.core.year'].search([('active','=',True)], limit=1)
    )
    responsable_id = fields.Many2one(
        'hr.employee',
        string='Responsable',
        # domain=[
        #     ('is_permanent','=',True),
        #     ('is_teacher','=',True)
        # ],
        required=True
    )
    responsable_adj_id = fields.Many2one(
        'hr.employee',
        string='Adjoint responsable',
        # domain=[
        #     ('is_permanent','=',True),
        #     ('is_teacher','=',True)
        # ],
        required=True
    )
    
    school_id = fields.Many2one('siantou.ems.core.school', string='Ecole')
    
    niveau_id = fields.Many2one('siantou.ems.core.level', string='Niveau',required=True,
                                 help="Niveau")
    
    surveillent_perm_ids = fields.Many2many(
        'hr.employee',
        string='Surveillants Internes',
        # domain=[
        #     ('is_permanent','=',True), 
        #     ('is_teacher','=',True)
        # ]
    )
    # surveillent_vac_ids = fields.Many2many(
    #     'hr.employee',
    #     string='Surveillants vacataires',
    #     domain=[('is_permanent','=',False)]
    # )

    _sql_constraints = [
        ('unique_name', 'unique(name)', "Ce nom existe déjà")
    ]



    @api.onchange('type_examen_id', 'year_id')
    def _onchange_name(self):
        for  secr in self:
            name = f"Session_de_"
            if secr.type_examen_id:
                name = f"{name}{secr.type_examen_id.code}"
            if secr.year_id:
                name = f"{name}_{secr.year_id.name}"
            
            secr.name=name



class SessionExamen(models.Model):
    _name = 'siantou.ems.examen.session'
    _description = "Model pour gérer les sessions d'examen"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        'Libellé', 
        required=True,
    )
    secretariat_examen_id = fields.Many2one(
        'siantou.ems.examen.secretariat',
        string="Sécretariat",
        required=True,
    )
    type_examen_id = fields.Many2one(
        'siantou.ems.examen.type',
        string="Type d'examen", 
        required=True,
        related='secretariat_examen_id.type_examen_id'
    )
    # field_of_study_ids = fields.Many2many(
    #     'siantou.ems.core.field_of_study', 
    #     string="Filières", required=True,
    # )
    
    level_id = fields.Many2one('siantou.ems.core.level', required=True,string='Niveau')
    
    school_id = fields.Many2one('siantou.ems.core.school', required=False,string='Ecole')
    
    field_of_study_ids = fields.Many2many('siantou.ems.core.field_of_study', required=True,string='Filières')
    
    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année académique', 
        required=True,
        related='secretariat_examen_id.year_id'
    )
    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester', 
        string="Semestre",
        required=True,
    )
    show_field = fields.Boolean(default=False)
    date_start = fields.Date(string='Date de début', required=True,)
    date_end = fields.Date(string='Date de fin', required=True, )
    # exam_hours = fields.Float(string='Durée', 
    #     compute='_compute_exam_hours', 
    #     store=True, 
    #     readonly=True
    # )
    state = fields.Selection([
        ('create', 'Encours de création'),
        ('draft', 'En attente de lancement'),
        ('progress', 'Lancé'),
        ('close', 'Terminé'),
        ('cancel', 'Annulé')
    ], string='Statut', readonly=True, index=True, copy=False, default='create', tracking=True)
    exam_subject_ids = fields.One2many('examen.session.line.subject', 'exam_id', string='Exams')
    exam_count = fields.Integer("Nombre d'examen", compute='_compute_exam')

    _sql_constraints = [
        ('unique_name', 'unique(name)', "Ce nom existe déjà")
    ]


    @api.model
    def create(self, values):
        values['state']='draft'
        result = super().create(values)
        return result

    @api.onchange('school_id')
    def _onchange_school_id(self):
        if self.school_id:
            # Récupérer les filières associées à l'école sélectionnée
            fields_of_study = self.env['siantou.ems.core.field_of_study'].search([
                ('school_id', '=', self.school_id.id)
            ])
            # Remplir le champ des filières avec les IDs des filières trouvées
            self.field_of_study_ids = [(6, 0, fields_of_study.ids)]
        else:
            # Si aucune école n'est sélectionnée, vider le champ des filières
            self.field_of_study_ids = [(5, 0, 0)]

    # @api.depends('date_start', 'date_end')
    # def _compute_exam_hours(self):
    #     for exam in self:
    #         if exam.date_start and exam.date_end:
    #             delta = exam.date_end - exam.date_start
    #             exam.exam_hours = delta.total_seconds() / 3600.0
    #         else:
    #             exam.exam_hours = False


    @api.onchange('type_examen_id', 'semester_id', 'year_id')
    def _onchange_name(self):
        for exam in self:
            name = f"Session_de_"
            if exam.type_examen_id:
                name = f"{name}{exam.type_examen_id.code}"
            if exam.semester_id:
                name = f"{name}_{exam.semester_id.name}"
            if exam.year_id:
                name = f"{name}_{exam.year_id.name}"
            
            exam.name=name


    @api.constrains('exam_hours')
    def _check_exam_hours(self):
        for record in self:
            if record.exam_hours < 0:
                raise ValidationError("La date de fin ne peut être inférieure à la date de début.")


    # Constraints
    @api.constrains('state')
    def _check_state(self):
        for record in self:
            if record.state != 'cancel':
                # Check the uniqueness constraint when the state is not 'cancel'
                if self.env['siantou.ems.examen.session'].search([
                    ('field_of_study_ids', 'in', record.field_of_study_ids.ids),
                    ('year_id', '=', record.year_id.id),
                    ('type_examen_id', '=', record.type_examen_id.id),
                    ('semester_id', '=', record.semester_id.id),
                    ('state', '!=', 'cancel'),
                    ('id', '!=', record.id),
                ]):
                    raise ValidationError("La session d'examen a déjà commencé pour cette filière !")


    # Compute Methods
    def _compute_exam(self):
        for record in self:
            record.exam_count = len(record.exam_subject_ids)
        

    # CRUD Operations
    # def unlink(self):
    #     for record in self:
    #         if record.state != 'draft':
    #             raise UserError("Impossible de supprimer une session d'examen dont le statut n'est pas « brouillon ».")
    #     return super(SessionExamen, self).unlink()



    # Action Buttons
    def button_draft(self):
        self.write({'state': 'draft'})



    def button_open(self):
        for rec in self:
            if rec.exam_subject_ids:
                rec.exam_subject_ids.unlink()
            
            for field_of_study_id in rec.field_of_study_ids:
                cycle_id = field_of_study_id.cursus_id
                student_ids = field_of_study_id.student_ids
                if cycle_id:
                    if cycle_id.level_ids:
                        for level_id in cycle_id.level_ids:
                            syllabus_id = self.env['siantou.ems.core.syllabus'].search(
                                [
                                    ('field_of_study_id','=',field_of_study_id.id),
                                    ('year_id','=',rec.year_id.id),
                                    ('semester_id','=',rec.semester_id.id),
                                    ('level_id','=',level_id.id),
                                ],
                                limit=1
                            )
                            if syllabus_id:
                                if syllabus_id.syllabus_subject_ids:
                                    for syllabus_subject_id in syllabus_id.syllabus_subject_ids:
                                        if syllabus_subject_id.syllabus_subject_line_ids:
                                            for subject_line_id in syllabus_subject_id.syllabus_subject_line_ids:
                                                exam_subject_id = rec.exam_subject_ids.create({
                                                    'exam_id':rec.id,
                                                    'name':f"{subject_line_id.name}_[{rec.name}]",
                                                    'field_of_study_id':syllabus_id.field_of_study_id.id,
                                                    'subject_id': subject_line_id.id,
                                                    'year_id':rec.year_id.id,
                                                    'level_id':level_id.id,
                                                    'date_start':rec.date_start,
                                                    'date_end':rec.date_end,
                                                    'state':'schedule',
                                                })
                                                rec.show_field=True
                                                if student_ids:
                                                    for student_id in student_ids:
                                                        exam_attendee_id = self.env['session.line.attende'].search([
                                                                ('exam_subject_id','=', exam_subject_id.id),
                                                                ('student_id','=', student_id.id)
                                                            ],
                                                            limit=1
                                                        )
                                                        if not exam_attendee_id:
                                                            exam_subject_id.exam_attendee_ids.create({
                                                                'exam_subject_id':exam_subject_id.id,
                                                                'student_id':student_id.id,
                                                                'status':'',
                                                            })
                                                else:
                                                    raise ValidationError(f"Aucun étudiant de la {exam_subject_id.name} trouvé")
                                        else:
                                            raise ValidationError("Matière des unitées d'enseignement non configuré")
                                else:
                                    raise ValidationError("Unité d'enseignement de syllabus non configuré")
                            else:
                                raise ValidationError("Syllabus non configuré")
                    else:
                        raise ValidationError("Niveau non configuré")
                else:
                    raise ValidationError("Cycle non configuré")

        self.write({'state': 'progress'})


    def get_students_has_paid(self, student_id, year_id):
        paids = self.env['education.fee.payment'].search(
            [
                ('year_id','=',year_id.id),
                ('student_id','=',student_id.id),
            ]
        )


    def button_close(self):
        for session in self:
            if any(exam.state != 'done' for exam in session.exam_subject_ids.filtered(lambda e: e.state != 'cancel')):
                raise UserError(_('Veuillez fermer tous les examens avant de clôturer la session. %s') % (session.name))
            session.exam_subject_ids.unlink()
        self.write({'state': 'close'})
        


    def button_cancel(self):
        self.write({'state': 'draft'})



    def action_view_exams(self):
        #self.ensure_one()
        #raise UserError(self.id)
        context = {
            'default_exam_session_id': self.id,
            'exam_session_id': self.id,
        }
        action = {
            'name': 'Voir tous les examens[matières]',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'examen.session.line.subject',
            'type': 'ir.actions.act_window',
            'context': context,
            'domain': [('exam_id','=',self.id)],
        }
        return action



class SessionExamenLine(models.Model):
    _name = 'examen.session.line'
    _description = "Model pour gérer les examens"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    exam_session_id = fields.Many2one(
        comodel_name='siantou.ems.examen.session',
        string="Session d'examen", 
        required=True, 
        ondelete='cascade', 
        index=True, copy=False,
        domain="[('state','=','progress')]"
    )
    sequence_id = fields.Many2one('ir.sequence', 'séquencement', copy=False, check_company=True)
    name = fields.Char("Nom", required=True)

    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study', 
        string="Filières", 
        required=True,
    )
    specialty_id = fields.Many2one(
        'siantou.ems.core.specialty',
        'Options',
        required=True,
    )
    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année académique', 
        required=True,
        related='exam_session_id.year_id'
    )
    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester', 
        string="Semestre",
        required=True,
        related='exam_session_id.semester_id'
    )
    level_ids = fields.Many2many(
        'siantou.ems.core.level',
        string='Niveaux',
        required=True,
    )
    date_start = fields.Datetime(string='Date de début')
    date_end = fields.Datetime(string='Date de fin')
    state = fields.Selection([
            ('create', 'Encours de création'),
            ('draft', 'En attente de lancement'),
            ('progress', 'Lancé'),
            ('close', 'Terminé'),
            ('cancel', 'Annulé')
        ], 
        string='Statut', readonly=True, 
        index=True, copy=False, 
        default='create', tracking=True
    )
    
    subjects_count = fields.Integer('Nombre de matière',compute='_compute_subject_count')
    exam_subject_ids = fields.One2many('examen.session.line.subject', 'exam_id', string='Matières', )



    # Action Buttons
    def button_draft(self):
        self.write({'state': 'draft'})


    def button_schedule(self):
        self.exam_subject_ids.unlink()
        student_ids = self.field_of_study_id.student_ids
        for student_id in student_ids:
            self.exam_subject_ids.create({
                'exam_id':self.id,
                'name':f"",
                'field_of_study_id':student_id.id,
                'specialty_id':student_id.id,
                'year_id':student_id.id,
                'date_start':student_id.id,
                'date_end':student_id.id,
                'state':'schedule',
            })
        self.write({'state': 'schedule'})


    def button_close(self):
        # if any(not attendee.status for attendee in self.exam_subject_ids):
        #     raise UserError(_("One or more attendance is missing."))
        self.write({'state': 'complete'})
        

    def button_cancel(self):
        self.write({'state': 'cancel'})


    @api.model
    def create(self, vals):
        # sequence = self.env['ir.sequence'].create({
        #     'name': _('Sequence') + ' ' + vals['code'],
        #     'padding': 5,
        #     'prefix': vals['code'],
        # })
        # vals['sequence_id'] = sequence.id
        examen = super().create(vals)
        return examen

    def _compute_subject_count(self):
        for record in self:
            record.subjects_count = len(record.exam_subject_ids)


    def action_view_subjects(self):
        action = self.env.ref('siantou_ems_examen.action_view_subjects').read()[0]
        action.update({
            'name': "Matières de l'examen",
            'view_mode': 'tree,form',
            'res_model': 'examen.session.line.subject',
            'type': 'ir.actions.act_window',
            'domain': [('exam_id','=',self.id)],
            'context': {
                'create': False,
                'delete': False,
            },
        })
        return action


class SessionExamenLineSubject(models.Model):
    _name = 'examen.session.line.subject'
    _description = "Model pour gérer les matières des examens"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    exam_id = fields.Many2one(
        comodel_name='siantou.ems.examen.session',
        string="Examen", 
        required=True, 
        ondelete='cascade', 
        index=True, copy=False,
    )
    sequence_id = fields.Many2one('ir.sequence', 'séquencement', copy=False, check_company=True)
    name = fields.Char("Nom", required=True)
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study', 
        string="Filières", 
        required=True,
    )
    subject_id = fields.Many2one(
        'siantou.ems.core.syllabus.subject.line',
        'Matière',
        required=True,
    )
    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année académique', 
        required=True,
        related='exam_id.year_id'
    )
    level_id = fields.Many2one(
        'siantou.ems.core.level',
        string='Niveaux',
        required=True,
    )
    date_start = fields.Datetime(string='Date de début')
    date_end = fields.Datetime(string='Date de fin')
    show_field = fields.Boolean(default=False)
    state = fields.Selection([
            ('draft', 'Brouillon'),
            ('schedule', 'Lancé'),
            ('complete', 'Terminé'),
            ('code', 'Codification des étudiants'),
            ('prepare', 'Mise à jour des notes'),
            ('done', 'Notes mis à jour'),
            ('cancel', 'Annulé')
        ], 
        string='Statut', 
        readonly=True, 
        index=True, copy=False, 
        default='draft', tracking=True
    )
    attendees_count = fields.Integer('Nombre de participants',compute='_compute_attendees_count')
    exam_attendee_ids = fields.One2many('session.line.attende', 'exam_subject_id', string='Participants', )


    # exam_result_line = fields.One2many('examen.session.line.result', 'exam_subject_id', string='Résultats', )
    # exam_result_count = fields.Integer('Résultats', compute='_compute_exam_result')

    def _compute_exam_result(self):
        for record in self:
            record.exam_result_count = len(record.exam_result_line)


    # Action Buttons
    def button_draft(self):
        self.write({'state': 'draft'})


    def button_schedule(self):
        self.exam_attendee_ids.unlink()
        student_ids = self.field_of_study_id.student_ids
        for student_id in student_ids:
            self.exam_attendee_ids.create({
                'exam_id':self.id,
                'student_id':student_id.id,
                'status':'A',
            })
        self.write({'state': 'schedule'})


    def button_close(self):
        if any(not attendee.status for attendee in self.exam_attendee_ids):
            raise UserError(_("One or more attendance is missing."))
        self.write({'state': 'complete'})
        

    def button_cancel(self):
        self.write({'state': 'cancel'})


    def button_prepare_result(self):
        #raise UserError(student_ids)
        # self.exam_result_line.unlink()
        # for attendee in self.exam_attendee_ids:
        #     exam_result = self.env['examen.session.line.result'].create({
        #         'student_id': attendee.student_id.id,
        #         'exam_subject_id': self.id,
        #         'attendance_status': attendee.status,
        #         'marks': 0,
        #     })
        self.write({'state': 'prepare'})





    def button_complete_result(self):
        for exam in self:
            if any(er.marks == 0 for er in exam.exam_result_line.filtered(lambda e: e.attendance_status == 'present')):
                raise UserError("One or more student's marks are not updated.")
        self.write({'state': 'done'})


    # def action_anonyma_wizard(self):
    #     action = self.env.ref('siantou_ems_examen.action_anonyma_wizard').read()[0]
    #     action.update({
    #         'name': f"Anonymation des notes",
    #         'res_model': 'examen.session.line.result.wizard',
    #         'type': 'ir.actions.act_window',
    #     })
    #     return action


    def button_open_anonyma_form(self):
        # self.exam_result_line.unlink()
        # for attendee in self.exam_attendee_ids:
        #     self.env['examen.session.line.result'].create({
        #         'student_id': attendee.student_id.id,
        #         'exam_subject_id': self.id,
        #         'anonyma_code':'',
        #         'attendance_status': attendee.status,
        #         'marks': 0,
        #     })
        # self.write({'state': 'prepare'})

        action = self.env['ir.actions.actions']._for_xml_id('siantou_ems_examen.action_exam_result')
        domain = [('exam_subject_id', '=', self.id)]
        action['domain'] = domain
        action['view_mode'] = 'tree,form'
        context = {
            'default_exam_id': self.id,
            'exam_subject_id': self.id,
            'create': False,
            'delete': False,
        }
        action['context'] = context
        return action


    @api.model
    def create(self, vals):
        # sequence = self.env['ir.sequence'].create({
        #     'name': _('Sequence') + ' ' + vals['code'],
        #     'padding': 5,
        #     'prefix': vals['code'],
        # })
        # vals['sequence_id'] = sequence.id
        examen = super().create(vals)
        return examen


    def _compute_attendees_count(self):
        for record in self:
            record.attendees_count = len(record.exam_attendee_ids)



    def button_open_results(self):
        action = self.env['ir.actions.actions']._for_xml_id('siantou_ems_examen.action_exam_teacher_result')
        domain = [('exam_subject_id', '=', self.id)]
        action['domain'] = domain
        action['view_mode'] = 'tree,form'
        context = {
            'default_exam_id': self.id,
            'exam_subject_id': self.id,
            'create': False,
            'delete': False,
        }
        action['context'] = context
        return action


    def action_view_attendees(self):
        action = self.env.ref('siantou_ems_examen.action_exam_attendees').read()[0]
        action.update({
            'name': "Participation à l'examen",
            'view_mode': 'tree',
            'res_model': 'session.line.attende',
            'type': 'ir.actions.act_window',
            'domain': [('exam_subject_id','=',self.id)],
            'context': {
                'create': False,
                'delete': False,
            },
        })
        return action




