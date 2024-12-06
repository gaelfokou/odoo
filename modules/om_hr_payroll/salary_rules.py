# Available variables:
#----------------------
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

# Salaire enseignant permanent SALENSPER
# Salaire enseignant temporaire SALENSTEM
# Salaire employé permanent SALEMPPER
# Salaire employé temporaire SALEMPTEM

# Règles salariales :

# Salaire de base enseignant permanent BASICENSPER
# Salaire de base enseignant temporaire BASICENSTEM
# Salaire de base employé permanent BASICEMPPER
# Salaire de base employé temporaire BASICEMPTEM

# 8h -- 1jr
# 40h -- 5jr -- 1week
# 160h -- 20jr -- 4week -- 1month
# contract.wage -- 160h -- 20jr -- 4week -- 1month

# Permanent

worked_days = 0

for line in payslip.worked_days_line_ids:
    worked_days += line.number_of_days

if worked_days < 20:
    result = ((contract.wage / 20) * worked_days) - (((contract.wage / 20) * worked_days) * 0.10)
else:
    # result = (contract.wage / 20) * worked_days
    result = contract.wage

# Temporaire

worked_hours = 0

for line in payslip.worked_days_line_ids:
    worked_hours += line.number_of_hours

if worked_hours < 160:
    result = ((contract.wage / 160) * worked_hours) - (((contract.wage / 160) * worked_hours) * 0.10)
else:
    result = (contract.wage / 160) * worked_hours
