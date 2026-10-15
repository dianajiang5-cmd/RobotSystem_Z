from celery import shared_task

@shared_task
def test_task():
    return "任务执行成功"