# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

def create_payment(payment_obj, montant, name, currency_id, journal_id,
                   partner_id, partner_type, date, payment_method_id,
                   payment_method_type, facture_id, transaction_id=False,
                   destination_journal_id=None):

    values = {
        'ref': name,
        "amount": montant or 0.0,
        "currency_id": currency_id,
        "destination_journal_id": destination_journal_id,
        "journal_id": journal_id,
        "partner_id": partner_id,
        "partner_type": partner_type,
        "date": date,
        "payment_method_id": payment_method_id,
        "payment_transaction_id": transaction_id,
        "payment_type": payment_method_type}

    # if facture_id:
    #     values['move_id'] = facture_id

    _logger.info(values)

    res = payment_obj.create(values)

    # res.post()
    return res