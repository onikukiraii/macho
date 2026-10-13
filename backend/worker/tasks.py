from common.db.session import SessionLocal
from dependencies import get_push_sender, get_rest_timer_repository
from features.rest_timer import service as rest_timer_service
from worker.app import celery_app


@celery_app.task(name=rest_timer_service.NOTIFY_REST_FINISHED_TASK_NAME)
def notify_rest_finished_task(uid: str, ends_at: int, next_set_label: str) -> None:
    with SessionLocal() as session:
        rest_timer_service.notify_rest_finished(
            get_rest_timer_repository(session),
            get_push_sender(),
            uid=uid,
            ends_at=ends_at,
            next_set_label=next_set_label,
        )
