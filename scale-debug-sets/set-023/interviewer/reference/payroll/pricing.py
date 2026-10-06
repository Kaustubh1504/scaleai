from .utils import hours_between


# VERIFIED
def base_pay(task, rule):
    if "hourly_cents" in rule:
        return int(rule["hourly_cents"]) * task.minutes // 60
    return int(rule["per_task_cents"])


def task_pay(task, rates):
    pay = base_pay(task, rates["task_types"][task.task_type])
    if hours_between(task.assigned_at, task.submitted_at) > rates["late_after_hours"]:
        pay = round(pay * rates["late_factor"])
    return pay


def to_local(usd_cents, currency, rates):
    """USD cents -> minor units of the payout currency."""
    return round(usd_cents * float(rates["currency_rates"][currency]))
