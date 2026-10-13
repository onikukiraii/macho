from features.rest_timer.types import PushMessage


def build_rest_finished_message(next_set_label: str) -> PushMessage:
    return PushMessage(title="レスト終了", body=next_set_label)
