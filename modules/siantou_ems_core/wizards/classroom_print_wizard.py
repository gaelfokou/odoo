# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from pprint import pformat
import pandas as pd
import numpy as np
import re
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import copy
import logging

_logger = logging.getLogger(__name__)

class ClassroomPrintWizard(models.TransientModel):
    _name = 'classroom.print.wizard'
    _description = 'Assistant d\'impression des enseignants'

    def print_classroom(self):
        data = self.print_classroom_report_data()

        # Appeler le rapport PDF
        if not data['docdata']['classroom_data']:
            raise UserError("Aucune donnée trouvée")
        report_action = self.env.ref('siantou_ems_core.action_report_classroom')
        return report_action.report_action(self, data=data)

    def print_classroom_report_data(self, domains=None):
        # Récupérer les emplois du temps pour le semestre sélectionné
        domain = []

        if domains:
            for d in domains:
                domain.append(d)

        search_classrooms = self.env['siantou.ems.core.building.classroom'].search(domain)

        classrooms = []
        for search_classroom in search_classrooms:
            classroom = {}
            classroom['code'] = search_classroom.code
            classroom['name'] = search_classroom.name
            classroom['building_name'] = search_classroom.building_id.name
            classroom['capacity'] = search_classroom.capacity
            classrooms.append(classroom)

        title = self.env['ir.config_parameter'].get_param(f'filter.{self.env.user.id}', '')

        _logger.info(f'----------- tototototototo classrooms {classrooms} -----------')

        return {
            'docdata': {
                'filter': title,
                'classroom_data': classrooms,
            }
        }
