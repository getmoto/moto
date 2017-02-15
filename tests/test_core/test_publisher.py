from __future__ import unicode_literals

import sure  # noqa

from moto.core.publisher import Publisher


def test_observers_invoked():
    publisher = Publisher()

    event10, event20, event30 = (10, 20, 30)

    publisher.subscribe(lambda _event_id, e_data: e_data.append('A'),
                        event10, event20, event30)

    publisher.subscribe(lambda _event_id, e_data: e_data.append('B'),
                        event20)

    publisher.subscribe(lambda _event_id, e_data: e_data.append('C'),
                        event20, event30)

    event_data = []
    publisher.notify(event10, event_data)
    event_data.should.equal(['A'])

    event_data = []
    publisher.notify(event20, event_data)
    event_data.should.equal(['A', 'B', 'C'])

    event_data = []
    publisher.notify(event30, event_data)
    event_data.should.equal(['A', 'C'])

    publisher.reset()
    event_data = []
    publisher.notify(event20, event_data)
    event_data.should.equal([])
