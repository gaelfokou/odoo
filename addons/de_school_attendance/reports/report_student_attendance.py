from odoo import api, fields, models, tools

class ReportStudentAttendance(models.Model):
    _name = "oe.report.student.attendance"
    _description = "Student Attendance Analysis"
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    nbr = fields.Integer('# of Lines', readonly=True)
    student_id = fields.Many2one('res.partner', 'Student', readonly=True)
    date = fields.Date('Attendance Date', readonly=True)
    #attendance_status = fields.Selection([
    #    ('Present', 'Present'),
    #    ('Absent', 'Absent'),
    #], string='Attendance Status', readonly=True)
    attendance_status = fields.Float('Attendance Status')

    @property
    def _table_query(self):
        return '%s %s %s %s' % (self._select(), self._from(), self._where(), self._group_by())

    def _select(self):
        select_str = """
            SELECT
                min(d.id) as id, d.student_id, d.date_attendance as date, 
                (case 
                    when d.attendance_status = 'present' then 1
                    else 0 
                end) as attendance_status
        """
        return select_str

    def _from(self):
        from_str = """
            FROM oe_student_attendance d
        """
        return from_str

    def _where(self):
        return """
            WHERE
                d.student_id is not null
        """

    def _group_by(self):
        group_by_str = """
            GROUP BY
                d.student_id, d.date_attendance, d.attendance_status
        """
        return group_by_str
