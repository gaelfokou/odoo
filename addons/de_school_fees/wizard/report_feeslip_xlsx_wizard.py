# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
import xlsxwriter
import io
import base64
import itertools
from odoo.exceptions import ValidationError
import psycopg2


class FeeslipXLSXReprot(models.TransientModel):
    """ Wizard for Student Feeslips Report """
    _name = 'oe.report.feeslip.wizard'
    _description = 'Student Fee Details Report Wizard'

    year_id = fields.Many2one('oe.school.year', string='Academic Year', required=True)
    course_ids = fields.Many2many('oe.school.course',string="Course")


    def generate_excel_report(self):
        self.ensure_one()
        file_path = 'fee_detail_report_' + str(fields.Date.today()) + '.xlsx'
        workbook = xlsxwriter.Workbook('/tmp/' + file_path)

        heading = workbook.add_format({'font_size': '12', 'align': 'center', 'bold': True,'border':True})
        title = workbook.add_format({'font_size': '10', 'align': 'center', 'bold': True, 'border':True, 'bg_color': '#ccffff'})
                
        text = workbook.add_format({'font_size': '10', 'align': 'left', 'border':True,})
        number = workbook.add_format({'font_size': '10', 'align': 'right', 'num_format':'#,##0.00', 'border':True})
        
        text_total = workbook.add_format({'font_size': '14', 'align': 'left', 'border':True, 'bold':True, 'bg_color': '#ccffff'})
        number_total = workbook.add_format({'font_size': '14', 'bold':True, 'align': 'right', 'num_format':'#,##0.00', 'border':True, 'bg_color': '#ccffff'})

        sheet = workbook.add_worksheet('Fee Details')

        end_date = self.year_id.date_end
        if self.year_id.date_end:
            end_date = self.year_id.date_end
        else:
            end_date = '2099-12-30'

        if len(self.course_ids):
            courses = ", ".join(self.course_ids.mapped('name'))
        else:
            courses = ""


        sheet.merge_range(0, 0, 0, 6, 'Fee Details Report', heading)
        
        sheet.write(1, 0, 'Date', heading)
        sheet.merge_range(1, 1, 1, 2, (str(self.year_id.date_start) + ' - ' + str(self.year_id.date_end)), text)

        sheet.write(1, 3, 'Course(s)', heading)
        sheet.merge_range(1, 4, 1, 6, courses, text)

        query = """
            SELECT
                slip.name, to_char(slip.date_from,'MM-DD-YYYY') as date_from, 
                to_char(slip.date_to,'MM-DD-YYYY') as date_to, 
                std.name as student_name, course.name -> 'en_US' as course,
                batch.name -> 'en_US' as batch,
                slip.state, line.name as fee_name, line.total as fee_amount
            FROM oe_feeslip slip
            JOIN oe_feeslip_line line on line.feeslip_id = slip.id
            JOIN res_partner std on line.student_id = std.id
            LEFT JOIN oe_school_course course on std.course_id = course.id
            LEFT JOIN oe_school_course_batch batch on std.batch_id = batch.id
            WHERE slip.date_from >= %(date_from)s and slip.date_to <= %(date_to)s 
            and std.course_id = ANY(%(course_ids)s)
            and slip.company_id = %(company_id)s
        """
        args = {
            'company_id': self.env.company,
            'date_from': self.year_id.date_start,
            'date_to': self.year_id.date_end or '2099-12-30',
            'course_ids': self.course_ids.ids
        }
        self.env.cr.execute(query, args)
        rs_slips = self._cr.dictfetchall()

        sheet.write(2, 0, 'Reference', title)
        sheet.write(2, 1, 'From Date', title)
        sheet.write(2, 2, 'To Date', title)
        sheet.write(2, 3, 'Student', title)
        sheet.write(2, 4, 'Course', title)
        sheet.write(2, 5, 'Batch', title)
        sheet.write(2, 6, 'State', title)
        sheet.write(2, 7, 'Fee', title)
        sheet.write(2, 8, 'Fee Amount', title)

        row = 3
            
        if len(rs_slips):
            for slip in rs_slips:
                sheet.set_column(row, 0, 20)
                sheet.set_column(row, 1, 20)
                sheet.set_column(row, 2, 30)
                sheet.set_column(row, 3, 20)
                sheet.set_column(row, 4, 10)
                sheet.set_column(row, 5, 10)
                sheet.set_column(row, 6, 10)
                sheet.set_column(row, 7, 10)
                sheet.set_column(row, 8, 10)

                sheet.write(row, 0, slip['name'],text)
                sheet.write(row, 1, slip['date_from'],text)
                sheet.write(row, 2, slip['date_to'],text)
                sheet.write(row, 3, slip['student_name'],text)
                sheet.write(row, 4, slip['course'],text)
                sheet.write(row, 5, slip['batch'],text)
                sheet.write(row, 6, slip['state'],text)
                sheet.write(row, 7, slip['fee_name'],text)
                sheet.write(row, 8, slip['fee_amount'],text)
                

                row += 1

        # Fee Summary
        sheet = workbook.add_worksheet('Fee Summary')

        sheet.merge_range(0, 0, 0, 10, 'Fee Summary Report', heading)
                
        sheet.write(1, 0, 'Date', heading)
        sheet.merge_range(1, 1, 1, 2, (str(self.year_id.date_start) + ' - ' + str(self.year_id.date_end)), text)

        sheet.write(1, 3, 'Course(s)', heading)
        sheet.merge_range(1, 4, 1, 6, courses, text)
        
        query = """
            SELECT
                course.name as course, sum(line.total) as fee_amount
            FROM oe_feeslip slip
            JOIN oe_feeslip_line line on line.feeslip_id = slip.id
            JOIN res_partner std on line.student_id = std.id
            JOIN oe_school_course course on std.course_id = course.id
            WHERE slip.date_from >= %(date_from)s and slip.date_to <= %(date_to)s 
            and slip.company_id = %(company_id)s
            group by course.name
        """
        args = {
            'company_id': self.env.company,
            'date_from': self.year_id.date_start,
            'date_to': self.year_id.date_end or '2099-12-30',
            'course_ids': self.course_ids.ids
        }
        self.env.cr.execute(query, args)
        rs_slips = self._cr.dictfetchall()

        sheet.write(2, 0, 'course', title)
        sheet.write(2, 1, 'fee_amount', title)
            
        row = 3
            
        if len(rs_slips):
            for slip in rs_slips:
                sheet.set_column(row, 0, 20)
                sheet.set_column(row, 1, 20)

                sheet.write(row, 0, slip['name'],text)
                sheet.write(row, 1, slip['name'],text)
                
                row += 1
                    
            
        else:
            sheet.merge_range(row , 3, row , 5,"No Data Was Found For This student In Selected Date", text)
            row += 4



        workbook.close()
        ex_report = base64.b64encode(open('/tmp/' + file_path, 'rb+').read())

        excel_report_id = self.env['oe.feeslip.save.xlsx.wizard'].create({"document_frame": file_path,
                                                                        "file_name": ex_report})

        return {
            'res_id': excel_report_id.id,
            'name': 'Files to Download',
            'view_type': 'form',
            "view_mode": 'form',
            'view_id': False,
            'res_model': 'oe.feeslip.save.xlsx.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }


