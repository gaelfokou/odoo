# -*- coding: utf-8 -*-
from odoo.exceptions import Warning, ValidationError
import re
import logging
_logger = logging.getLogger("++++++++++++++=============")

######################################################################################
#  Source du code de conversion en chiffre                                           #
#    https://github.com/BADEP/addons/blob/8.0/amount_to_text_fr/amount_to_text_fr.py #
######################################################################################

correspondance = []

to_19_fr = (
    u'zéro', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six',
    'sept', 'huit', 'neuf', 'dix', 'onze', 'douze', 'treize',
    'quatorze', 'quinze', 'seize', 'dix-sept', 'dix-huit', 'dix-neuf')
tens_fr = (
    'vingt', 'trente', 'quarante', 'Cinquante', 'Soixante',
    'Soixante-dix', 'Quatre-vingt', 'Quatre-vingt Dix')
denom_fr = (
    '', 'Mille', 'Millions', 'Milliards', 'Billions', 'Quadrillions',
    'Quintillion', 'Sextillion', 'Septillion', 'Octillion', 'Nonillion',
    'Décillion', 'Undecillion', 'Duodecillion', 'Tredecillion',
    'Quattuordecillion', 'Sexdecillion', 'Septendecillion', 'Octodecillion',
    'Icosillion', 'Vigintillion')

pattern = re.compile(r'(?i)(un)\s+(cent|mille)+.*')

def format_amount_to_integer(amount):
    """
    Convertit un nombre decimal en un entier.

    fonction qui formate un entier et le convertit en entier
    l'entier utilise est celui le plus proche du nombre decimal.
    """
    amount = int(round(amount))
    return '{0:,}'.format(amount).replace(',', ' ')

def amount_to_text_fr_corrected(valeur, devise):
    res = amount_to_text_fr(valeur, devise)

    # enleve le zero cent
    # res = res.replace('zéro Cent', '').strip()
    rep = res

    for elt in correspondance:
        r_comp = re.compile(elt[0])
        rep = r_comp.sub(elt[1], rep)
    return rep[:-14]

def _convert_nn_fr(val):
    """ convert a value < 100 to French
    """
    if val < 20:
        return to_19_fr[val]
    for (dcap, dval) in ((k, 20 + (10 * v)) for (v, k) in enumerate(tens_fr)):
        if dval + 10 > val:
            if val % 10:
                if dval == 70 or dval == 90:
                    return tens_fr[int(dval / 10 - 3)] + '-' + to_19_fr[int(val % 10 + 10)]
                else:
                    return dcap + '-' + to_19_fr[val % 10]
            return dcap

def _convert_nnn_fr(val):
    """ convert a value < 1000 to french

        special cased because it is the level that kicks
        off the < 100 special case.  The rest are more general.
        This also allows you to
        get strings in the form of 'forty-five hundred' if called directly.
    """
    word = ''
    (mod, rem) = (val % 100, val // 100)
    if rem > 0:
        if rem == 1:
            word = 'Cent'
        else:
            word = to_19_fr[rem] + ' Cent'
        if mod > 0:
            word += ' '
    if mod > 0:
        word += _convert_nn_fr(mod)
    return word

def french_number(val):
    if val < 100:
        return _convert_nn_fr(val)
    if val < 1000:
        return _convert_nnn_fr(val)
    for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom_fr))):
        if dval > val:
            mod = 1000 ** didx
            l = val // mod
            r = val - (l * mod)
            if l == 1:
                ret = denom_fr[didx]
            else:
                ret = _convert_nnn_fr(l) + ' ' + denom_fr[didx]
            if r > 0:
                ret = ret + ' ' + french_number(r)
            return ret

def amount_to_text_fr(number, currency):
    number = '%.2f' % number
    units_name = currency
    list = str(number).split('.')
    start_word = french_number(abs(int(list[0])))
    end_word = french_number(int(list[1]))
    cents_number = int(list[1])
    cents_name = (cents_number > 1) and ' Centimes' or ' Centime'
    final_result = start_word + ' ' + units_name + ' ' + end_word + ' ' + cents_name
    return final_result

def get_amount_en_lettre(amount):
    montant = ""
    if amount:
        montant = amount_to_text_fr_corrected(
            amount,
            "FCFA"
        )
        montant = montant.partition('A')[0] + u'A'
        un_match = pattern.search(montant)
        if un_match:
            un_start = un_match.start(1)
            un_end = un_start + 2
            str_list = list(montant)
            if str_list[un_start - 1] != '-':
                str_list[un_start:un_end] = []
            montant = ''.join(str_list)
        tab = montant.split(' ')
        if tab[0] == "Millions":
            tab[0] = "Un Million"
        elif tab[0] == "un" and tab[1] == "Millions":
            tab[1] = "Million"
        elif tab[-2] == "Quatre-vingt":
            tab[-2] = "Quatre-vingts"
        montant = ' '.join(tab)
    return montant.upper()