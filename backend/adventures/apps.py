from django.apps import AppConfig
from django.core.signals import request_started
from django.db.utils import OperationalError, ProgrammingError
from django.dispatch import receiver

_reset_done = False


def _reset_waiting_ai():
    from .models import Adventure

    Adventure.objects.filter(is_waiting_ai=True).update(is_waiting_ai=False)


@receiver(request_started, dispatch_uid="adventures.reset_waiting_ai_once")
def reset_waiting_ai_once(**_kwargs):
    global _reset_done
    if _reset_done:
        return
    try:
        _reset_waiting_ai()
        _reset_done = True
    except (OperationalError, ProgrammingError):
        # Database might not be ready on the first request.
        return


class AdventuresConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "adventures"

    def ready(self):
        from backup_scheduler import start_backup_scheduler

        start_backup_scheduler()
