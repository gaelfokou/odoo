from odoo import models, fields

class OptionOfStudy(models.Model):
    _name = 'siantou.ems.core.option'
    _description = 'Option'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    specialty_id = fields.Many2one(
        'siantou.ems.core.specialty',
        string='Spécialité',
        required=True,
    )

    # Code du programme
    code = fields.Char(
        'Code',
        required=True
    )

    # Nom du programme
    name = fields.Char(
        "Nom de l'option",
        required=True
    )

    _sql_constraints = [
        ('unique_code', 'unique(code)', "Le code de l'option doit être unique."),
    ]

    def write(self, vals):
        res = super(OptionOfStudy, self).write(vals)

        if 'name' in vals:
            options = []
            if len(self.ids) == 1:
                option = self.env['siantou.ems.core.option'].browse(self.id)
                options.append(option)
            else:
                options = self.env['siantou.ems.core.option'].browse(self.ids)
                options = list(options)

            for option in options:
                classes = self.env['siantou.ems.core.class'].search([
                    ('option_id', '=', option.id),
                ])
                classes = list(classes)
                for classe in classes:
                    classe.write({
                        'option_id': option.id,
                    })

        return res

class SpecialtyOfStudy(models.Model):
    _name = 'siantou.ems.core.specialty'
    _description = 'Spécialités'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
        required=True,
    )

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='École',
        related='field_of_study_id.school_id',
        store=False
    )

    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cursus ou Cycle',
        related='field_of_study_id.cycle_id',
        store=False
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Département'
    )

    # Code du programme
    code = fields.Char(
        'Code',
        required=True
    )

    # Nom du programme
    name = fields.Char(
        string='Nom',
        required=True
    )

    # Ensemble des options de la filière
    option_ids = fields.One2many(
        'siantou.ems.core.option',
        'specialty_id',
        'Options'
    )

    slot_id = fields.Many2one(
        'siantou.ems.timetable.slot',
        string='Créneau horaire',
    )

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code de la spécialité doit être unique.'),
    ]

    def write(self, vals):
        res = super(SpecialtyOfStudy, self).write(vals)

        if 'name' in vals:
            specialties = []
            if len(self.ids) == 1:
                specialty = self.env['siantou.ems.core.specialty'].browse(self.id)
                specialties.append(specialty)
            else:
                specialties = self.env['siantou.ems.core.specialty'].browse(self.ids)
                specialties = list(specialties)

            for specialty in specialties:
                classes = self.env['siantou.ems.core.class'].search([
                    ('specialty_id', '=', specialty.id),
                ])
                classes = list(classes)
                for classe in classes:
                    classe.write({
                        'specialty_id': specialty.id,
                    })

        return res

class FieldOfStudy(models.Model):
    _name = 'siantou.ems.core.field_of_study'
    _description = 'Filières'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    # Code du programme
    code = fields.Char(
        'Code',
        required=True
    )

    # Nom du programme
    name = fields.Char(
        string='Nom',
        required=True
    )

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='École',
    )

    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cursus ou Cycle',
    )

    # Ensemble des spécialités de la filière
    specialty_ids = fields.One2many(
        'siantou.ems.core.specialty',
        'field_of_study_id',
        'Spécialités'
    )

    batch_ids = fields.One2many(
        'siantou.ems.core.student.batch',
        'field_of_study_id',
        string='Lots de la filière'
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Département'
    )

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code de la filière doit être unique.'),
    ]

    def write(self, vals):
        res = super(FieldOfStudy, self).write(vals)

        if 'name' in vals:
            field_of_studies = []
            if len(self.ids) == 1:
                field_of_study = self.env['siantou.ems.core.field_of_study'].browse(self.id)
                field_of_studies.append(field_of_study)
            else:
                field_of_studies = self.env['siantou.ems.core.field_of_study'].browse(self.ids)
                field_of_studies = list(field_of_studies)

            for field_of_study in field_of_studies:
                classes = self.env['siantou.ems.core.class'].search([
                    ('field_of_study_id', '=', field_of_study.id),
                ])
                classes = list(classes)
                for classe in classes:
                    classe.write({
                        'field_of_study_id': field_of_study.id,
                    })

        return res

    def get_subject_ids_by_level(self):
        # Dictionnaire pour stocker les IDs des cours par niveau
        subject_ids_by_level = {}

        # Parcourt tous les niveaux de la filière
        levels = self.env['siantou.ems.core.level'].search([])
        levels = list(levels)
        for level in levels:
            subject_ids_by_level[level.id] = []
            # Filtre les cours de cette filière et de ce niveau
            classes = self.env['siantou.ems.core.class'].search([
                ('level_id', '=', level.id),
                ('field_of_study_id', '=', self.id)
            ])
            classes = list(classes)
            for classe in classes:
                subjects = self.env['siantou.ems.core.subject'].search([
                    ('ue_ids', 'in', classe.ue_ids.ids),
                ])
                subjects = list(subjects)
                for subject in subjects:
                    if subject.id not in subject_ids_by_level[level.id]:
                        subject_ids_by_level[level.id].append(subject.id)
            if len(subject_ids_by_level[level.id]) == 0:
                del(subject_ids_by_level[level.id])

        return subject_ids_by_level
