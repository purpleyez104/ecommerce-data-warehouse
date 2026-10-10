from datetime import datetime
from ecommerce_generator.behavior import EVENTS, events


def test_behavior_independent_and_deterministic():
    t = datetime(2026, 9, 20, 14, 0)
    first = list(events('unit-a', 42, 120, t, 90))
    assert first == list(events('unit-a', 42, 120, t, 90))
    assert len(first) == 120
    assert set(x[0] for x in first) == {'page', 'product', 'cart'}
    assert set(x[1]['event_type'] for x in first) == {e for _, e in EVENTS}
    assert len({x[1]['event_id'] for x in first}) == 120
    assert all('op' not in row and 'before' not in row and 'after' not in row for _, row in first)
    assert all((e['user_id'] is None) != (e['visitor_id'] is None) for _, e in first)
    assert all(e['source'] == 'independent_behavior_generator' for _, e in first)
