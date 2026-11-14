import datetime
from typing import Optional, List, Tuple
from backend.app.core.config import settings

COMPANY_HOLIDAYS_2026 = {
    "2026-01-26", # Republic Day
    "2026-08-15", # Independence Day
    "2026-10-02", # Gandhi Jayanti
    "2026-10-20", # Dussehra
    "2026-11-08", # Diwali
    "2026-12-25", # Christmas
}

class SLACalculator:
    @staticmethod
    def calculate_deadlines(
        priority: str,
        channel_id: str,
        created_at: datetime.datetime,
        channel_sla_factor: float = 1.0,
        holidays: Optional[set] = None
    ) -> Tuple[datetime.datetime, datetime.datetime]:
        """
        Calculates first response due date and resolution due date.
        P1 is calculated using 24x7 continuous wall-clock time.
        P2, P3, P4 incorporate business hours (Mon-Fri 09:00 - 18:00) excluding weekends and holidays.
        """
        first_resp_min = settings.SLA_FIRST_RESPONSE_MINUTES.get(priority, 60)
        resol_min = settings.SLA_RESOLUTION_MINUTES.get(priority, 480)

        # Apply channel multiplier (e.g. Live chat = 0.5x, Phone = 0.2x)
        first_resp_min = max(1, int(first_resp_min * channel_sla_factor))
        resol_min = max(15, int(resol_min * channel_sla_factor))

        if priority == "P1":
            # Wall clock strictly for P1 critical (24x7x365)
            first_response_due = created_at + datetime.timedelta(minutes=first_resp_min)
            resolution_due = created_at + datetime.timedelta(minutes=resol_min)
            return first_response_due, resolution_due

        # For P2-P4, calculate using business hours & holidays
        holiday_set = holidays if holidays is not None else COMPANY_HOLIDAYS_2026
        first_response_due = SLACalculator._add_business_minutes(created_at, first_resp_min, holiday_set)
        resolution_due = SLACalculator._add_business_minutes(created_at, resol_min, holiday_set)
        return first_response_due, resolution_due

    @staticmethod
    def _add_business_minutes(
        start_dt: datetime.datetime,
        minutes_to_add: int,
        holidays: Optional[set] = None
    ) -> datetime.datetime:
        """
        Deterministic business calendar addition:
        Working hours: 09:00 - 18:00 IST (9 hours / 540 mins daily)
        Working days: Mon-Fri (weekday 0-4), skipping weekends & designated holidays.
        """
        holiday_set = holidays or set()
        curr = start_dt

        def is_non_working_day(dt: datetime.datetime) -> bool:
            return dt.weekday() >= 5 or dt.strftime("%Y-%m-%d") in holiday_set

        # Adjust start time if outside working hours or on weekend/holiday
        while is_non_working_day(curr):
            curr = curr.replace(hour=9, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)

        if curr.hour < 9:
            curr = curr.replace(hour=9, minute=0, second=0, microsecond=0)
        elif curr.hour >= 18:
            curr = curr.replace(hour=9, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
            while is_non_working_day(curr):
                curr += datetime.timedelta(days=1)

        remaining_mins = minutes_to_add
        while remaining_mins > 0:
            eod = curr.replace(hour=18, minute=0, second=0, microsecond=0)
            avail_mins_today = int((eod - curr).total_seconds() / 60)
            if remaining_mins <= avail_mins_today:
                curr += datetime.timedelta(minutes=remaining_mins)
                remaining_mins = 0
            else:
                remaining_mins -= avail_mins_today
                # Advance to next business day 09:00
                curr = curr.replace(hour=9, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
                while is_non_working_day(curr):
                    curr += datetime.timedelta(days=1)

        return curr

    @staticmethod
    def calculate_warning_threshold(
        created_at: datetime.datetime,
        due_at: datetime.datetime,
        threshold_ratio: float = 0.80
    ) -> datetime.datetime:
        """
        Calculates when an SLA escalation warning should trigger (e.g. at 80% elapsed time).
        """
        total_duration = due_at - created_at
        return created_at + datetime.timedelta(seconds=total_duration.total_seconds() * threshold_ratio)

    @staticmethod
    def calculate_extended_deadline(
        due_at: datetime.datetime,
        pause_duration: datetime.timedelta
    ) -> datetime.datetime:
        """
        Extends deadline when ticket is unpaused from PENDING_CUSTOMER.
        """
        return due_at + pause_duration
