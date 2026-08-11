from odoo import models, fields

class School(models.Model):
    _name = 'siantou.ems.core.school'
    _description = 'École'

    code = fields.Char(
        string='Code',
        index=True,
        required=True
    )

    name = fields.Char(
        string='Nom',
        index=True,
        required=True
    )

    max_students_per_batch = fields.Integer(
        string='Nombre maximal d\'étudiants par lot',
        required=True,
        default=60
    )

    field_of_study_ids = fields.One2many(
        'siantou.ems.core.field_of_study',
        'school_id',
        string='Filières'
    )

    # student_ids = fields.One2many(
    #     'res.partner',
    #     'school_id',
    #     string='Étudiants'
    # )

    student_ids = fields.One2many(
        'oe.school.student',
        'school_id',
        string='Étudiants'
    )

    batch_ids = fields.One2many(
        'siantou.ems.core.student.batch',
        'school_id',
        string='Lots d\'étudiants'
    )

    building_ids = fields.Many2many('siantou.ems.core.building', 'school_building_rel', 'school_id', 'building_id', string="Bâtiments")

    group_ids = fields.Many2many('siantou.ems.timetable.group', 'school_group_rel', 'school_id', 'group_id', string="Versions d'emploi du temps")

    department_ids = fields.One2many(
        'hr.department',
        'school_id',
        string='Départements'
    )

    def write(self, vals):
        res = super(School, self).write(vals)

        if 'name' in vals:
            schools = []
            if len(self.ids) == 1:
                school = self.env['siantou.ems.core.school'].browse(self.id)
                schools.append(school)
            else:
                schools = self.env['siantou.ems.core.school'].browse(self.ids)
                schools = list(schools)

            for school in schools:
                departments = self.env['hr.department'].search([
                    ('school_id', '=', school.id),
                ])
                departments = list(departments)
                for department in departments:
                    department.write({
                        'school_id': school.id,
                    })

        return res
