import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.brokers.stub import StubBroker
from dramatiq.middleware import CurrentMessage, Retries, TimeLimit
from api.config import get_settings
import os

settings = get_settings()


def get_broker():
    if os.getenv("TESTING") == "1":
        broker = StubBroker()
        broker.emit_after("run")
        return broker

    broker = RedisBroker(
        url=settings.redis_url,
        middleware=[
            CurrentMessage(),
            Retries(max_retries=3, min_backoff=5000, max_backoff=60000),
            TimeLimit(time_limit=10 * 60 * 1000),  # 10 min max per task
        ],
    )
    return broker


broker = get_broker()
dramatiq.set_broker(broker)
