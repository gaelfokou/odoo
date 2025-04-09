import json
import logging
from datetime import datetime

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class RestApi(http.Controller):

    @http.route(['/odoo_connect'], type="http", auth="none", csrf=False, methods=['GET'])
    def odoo_connect(self, **kw):
        datas = json.dumps({"Status": "auth successful","User": "landry",})
        return http.request.make_response(data=datas)
