from collections import Counter

from .broker import Broker, rejection_code
from .models import LeaseError


def snapshot(tasks):
    """A frozen copy of every task, unaffected by later events."""
    return dict(tasks)


def replay(tasks, events, config):
    """Run every event through a Broker. Returns (broker, poll log, rejections, checkpoint)."""
    broker = Broker(tasks, config["lease_ms"])
    polls, rejected = [], Counter()
    checkpoint = None
    for event in events:
        if checkpoint is None and event.at_ms > config["checkpoint_ms"]:
            broker.reap(config["checkpoint_ms"])
            checkpoint = snapshot(broker.tasks)
        broker.reap(event.at_ms)
        try:
            if event.action == "poll":
                polls.append((event.worker_id, broker.poll(event.worker_id, event.at_ms)))
            elif event.action == "heartbeat":
                broker.heartbeat(event.worker_id, event.task_id, event.at_ms)
            elif event.action == "ack":
                broker.ack(event.worker_id, event.task_id)
            elif event.action == "fail":
                broker.fail(event.worker_id, event.task_id)
        except LeaseError as exc:
            rejected[rejection_code(exc)] += 1
    if checkpoint is None:
        broker.reap(config["checkpoint_ms"])
        checkpoint = snapshot(broker.tasks)
    return broker, polls, rejected, checkpoint
