# Available variables:
# ----------------------
# payslip: object containing the payslips
# employee: hr.employee object
# contract: hr.contract object
# rules: object containing the rules code (previously computed)
# categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
# worked_days: object containing the computed worked days.
# inputs: object containing the computed inputs.

# Note: returned value have to be set in the variable 'result'

# result = contract.wage * 0.10
# result = worked_days.WORK100.number_of_days
# result = worked_days.WORK100.number_of_hours

# Structure des salaires :

# Structure de salaire (BASE)
# Règles salariales :
# Salaire de Base (BASIC) : result = contract.wage
# Brut (GROSS) : result = categories.BASIC + categories.ALW
# Impôt sur le revenu (IR) : result = (categories.BASIC + categories.ALW) * 5.5 / 100
# Apecus (APECUS) : result = 1500
# Cnps (CNPS) : result = (categories.BASIC + categories.ALW) * 4.2 / 100
# Salaire Net (NET) : result = categories.BASIC + categories.ALW - categories.DED

# Structure de salaire chef département (BASECD)
# Règles salariales :
# Salaire de Base (BASIC) : result = contract.wage
# Prime CD (PRIMCD) : result = 0
# Brut (GROSS) : result = categories.BASIC + categories.ALW
# Impôt sur le revenu (IR) : result = (categories.BASIC + categories.ALW) * 5.5 / 100
# Apecus (APECUS) : result = 1500
# Cnps (CNPS) : result = (categories.BASIC + categories.ALW) * 4.2 / 100
# Salaire Net (NET) : result = categories.BASIC + categories.ALW - categories.DED

# Structure de salaire coordonnateur (BASECO)
# Règles salariales :
# Salaire de Base (BASIC) : result = contract.wage
# Prime CO (PRIMCO) : result = 0
# Brut (GROSS) : result = categories.BASIC + categories.ALW
# Impôt sur le revenu (IR) : result = (categories.BASIC + categories.ALW) * 5.5 / 100
# Apecus (APECUS) : result = 1500
# Cnps (CNPS) : result = (categories.BASIC + categories.ALW) * 4.2 / 100
# Salaire Net (NET) : result = categories.BASIC + categories.ALW - categories.DED

# 8h -- 1jr
# 40h -- 5jr -- 1week
# 160h -- 20jr -- 4week -- 1month
# contract.wage -- 160h -- 20jr -- 4week -- 1month

# Permanent

# worked_days = 0
# for line in payslip.worked_days_line_ids:
#     worked_days += line.number_of_days
# result = (contract.wage / 20) * worked_days

# Temporaire

# worked_hours = 0
# for line in payslip.worked_days_line_ids:
#     worked_hours += line.number_of_hours
# result = (contract.wage / 160) * worked_hours
