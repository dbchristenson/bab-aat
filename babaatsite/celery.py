import os
from sys import platform

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "babaatsite.settings")

# mac os check
if platform == "darwin":
    os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

redis_password = os.getenv("redis_password", "")
redis_host = os.getenv("redis_host", "localhost")
redis_port = os.getenv("redis_port", "6379")

# build the redis URL
celery_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/0"

app = Celery(
    "babaatsite",
    broker=celery_url,
    backend=celery_url,
)

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
