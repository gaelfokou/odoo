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

result = 0

for line in payslip.worked_days_line_ids:
    result += line.number_of_hours

if result > 2:
    result = result + 2

result = contract.wage * result
