
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger("++++++++++++")

from odoo import models, fields, api
from odoo.exceptions import ValidationError




class StudentEnrollmentAdmissionWizard(models.TransientModel):
    _name = 'siantou.ems.core.student.enrollment.admission.wizard'
    _description = 'modale pour effectuer une admission'

    # student_id = fields.Many2one(
    #     'oe.school.student', 
    #     string="Etudiant admis", 
    #     # required=True,
    # )
    student_enrollement_id = fields.Many2one(
        'oe.school.student.enrollment', 
        string="Etudiant inscrit", 
        # required=True,  
    )
    observations = fields.Html(string="Observations", required=True)


    @api.model
    def default_get(self, fields):
        res = super(StudentEnrollmentAdmissionWizard, self).default_get(fields)
        # print(self.env.context.get('active_model'))
        if self.env.context.get('active_id'):
            res['student_enrollement_id'] = self.env.context.get('active_id')
            _logger.info(f"Student admission ::: {res['student_enrollement_id']}")
        return res


    def generate_matricule(self, field_of_study_id):
        # Get the current year
        current_year = datetime.now().year
        last_caract_year = str(current_year)[2:]
        # _logger.info(f"last_caract_year : {last_caract_year}")
        students = self.env['oe.school.student'].sudo().search([])  
        # _logger.info(f"Matricule généré : {len(students)}")
        nbre = len(students) + 1
        matricule = f"{last_caract_year}{field_of_study_id.school_id.code}000{nbre}"
        _logger.info(f"Matricule généré : {matricule}")
        return matricule


    def student_enroll_admission(self):
        student_id = None
        if self.student_enrollement_id:  
            matricule=self.student_enrollement_id.matricule
            if not matricule:
                matricule = self.generate_matricule(self.student_enrollement_id.field_of_study_id)

            if self.student_enrollement_id.status_univ=='new':
                data = {
                    'student_enroll_id': self.student_enrollement_id.id,
                    'name': self.student_enrollement_id.name,
                    'matricule': matricule,
                    'cycle_id': self.student_enrollement_id.cycle_id.id,
                    'region_id': self.student_enrollement_id.region_id.id,
                    'city_id': self.student_enrollement_id.city_id.id,
                    'quarter_id': self.student_enrollement_id.quarter_id.id,
                    'field_of_study_id': self.student_enrollement_id.field_of_study_id.id,
                    'type_cour': self.student_enrollement_id.type_cour,
                    'status_univ': self.student_enrollement_id.status_univ,
                    'date_naissance': self.student_enrollement_id.date_naissance,
                    'lieu_naissance': self.student_enrollement_id.lieu_naissance,
                    'sexe': self.student_enrollement_id.sexe,
                    'situat_matri': self.student_enrollement_id.situat_matri,
                    'lieu_residence': self.student_enrollement_id.lieu_residence,
                    'email': self.student_enrollement_id.email,
                    'num_tel': self.student_enrollement_id.num_tel,
                    'level_id': self.student_enrollement_id.level_id.id,
                    'is_autre_pays': self.student_enrollement_id.is_autre_pays,
                }
                if not self.student_enrollement_id.nationalite:
                    data['autre'] = self.student_enrollement_id.autre
                    data['is_autre_pays'] = True
                else:
                    data['nationalite'] = self.student_enrollement_id.nationalite.id
                    data['is_autre_pays'] = False
                
                student_id = self.env['oe.school.student'].create(data)
            else:
                student_id = self.env['oe.school.student'].search([
                        ('name','=',self.student_enrollement_id.name),
                        ('matricule','=',matricule),
                    ], 
                    limit=1
                )

            self.student_enrollement_id.status='transfer'
            self.student_enrollement_id.observations=self.observations

            #=====Création d'un parcours étudiant
            self.env['oe.school.student.career'].create({
                'student_id': student_id.id,
                'name': f"Admission DE {student_id.name}",
                'year_id': self.student_enrollement_id.year_id.id,
                'level_id': self.student_enrollement_id.level_id.id,
                'field_of_study_id': self.student_enrollement_id.field_of_study_id.id,
                'cycle_id': self.student_enrollement_id.cycle_id.id,
                'observations': self.observations,
            })


        return {'type': 'ir.actions.act_window_close'}
