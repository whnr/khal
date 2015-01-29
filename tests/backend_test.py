
import pytest
import pytz

from datetime import date, datetime, timedelta
import icalendar

from khal.khalendar import backend
from khal.compat import unicode_type
from khal.khalendar.exceptions import OutdatedDbVersionError, UpdateFailed

berlin = pytz.timezone('Europe/Berlin')
locale = {'local_timezone': berlin, 'default_timezone': berlin}


def test_new_db_version():
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    backend.DB_VERSION += 1
    with pytest.raises(OutdatedDbVersionError):
        dbi._check_table_version()

event_rrule_recurrence_id = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RRULE:FREQ=WEEKLY;UNTIL=20140806T060000Z
DTSTART;TZID=Europe/Berlin:20140630T070000
DTEND;TZID=Europe/Berlin:20140630T120000
END:VEVENT
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RECURRENCE-ID:20140707T050000Z
DTSTART;TZID=Europe/Berlin:20140707T090000
DTEND;TZID=Europe/Berlin:20140707T140000
END:VEVENT
END:VCALENDAR
"""

event_rrule_recurrence_id_update = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RRULE:FREQ=WEEKLY;UNTIL=20140806T060000Z
DTSTART;TZID=Europe/Berlin:20140630T070000
DTEND;TZID=Europe/Berlin:20140630T120000
EXDATE;TZID=Europe/Berlin:20140714T070000
END:VEVENT
END:VCALENDAR
"""


def test_event_rrule_recurrence_id():
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    assert dbi.list() == list()
    events = dbi.get_time_range(datetime(2014, 6, 30, 0, 0), datetime(2014, 7, 26, 0, 0))
    assert events == list()
    dbi.update(event_rrule_recurrence_id, href='12345.ics', etag='abcd')
    assert dbi.list() == [('12345.ics', 'abcd')]
    events = dbi.get_time_range(datetime(2014, 4, 30, 0, 0), datetime(2014, 9, 26, 0, 0))
    events.sort(key=lambda x: x.start)
    assert len(events) == 6

    assert events[0].start == berlin.localize(datetime(2014, 6, 30, 7, 0))
    assert events[1].start == berlin.localize(datetime(2014, 7, 7, 9, 0))
    assert events[2].start == berlin.localize(datetime(2014, 7, 14, 7, 0))
    assert events[3].start == berlin.localize(datetime(2014, 7, 21, 7, 0))
    assert events[4].start == berlin.localize(datetime(2014, 7, 28, 7, 0))
    assert events[5].start == berlin.localize(datetime(2014, 8, 4, 7, 0))

    assert dbi

event_rrule_recurrence_id_reverse = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RECURRENCE-ID:20140707T050000Z
DTSTART;TZID=Europe/Berlin:20140707T090000
DTEND;TZID=Europe/Berlin:20140707T140000
END:VEVENT
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RRULE:FREQ=WEEKLY;COUNT=6
DTSTART;TZID=Europe/Berlin:20140630T070000
DTEND;TZID=Europe/Berlin:20140630T120000
END:VEVENT
END:VCALENDAR
"""


def test_event_rrule_recurrence_id_reverse():
    """as icalendar elements can be saved in arbitrary order, we also have to
    deal with `reverse` ordered icalendar files
    """
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    assert dbi.list() == list()
    events = dbi.get_time_range(datetime(2014, 6, 30, 0, 0), datetime(2014, 7, 26, 0, 0))
    assert events == list()
    dbi.update(event_rrule_recurrence_id_reverse, href='12345.ics', etag='abcd')
    assert dbi.list() == [('12345.ics', 'abcd')]
    events = dbi.get_time_range(datetime(2014, 4, 30, 0, 0), datetime(2014, 9, 26, 0, 0))
    events.sort(key=lambda x: x.start)
    assert len(events) == 6

    assert events[0].start == berlin.localize(datetime(2014, 6, 30, 7, 0))
    assert events[1].start == berlin.localize(datetime(2014, 7, 7, 9, 0))
    assert events[2].start == berlin.localize(datetime(2014, 7, 14, 7, 0))
    assert events[3].start == berlin.localize(datetime(2014, 7, 21, 7, 0))
    assert events[4].start == berlin.localize(datetime(2014, 7, 28, 7, 0))
    assert events[5].start == berlin.localize(datetime(2014, 8, 4, 7, 0))


def test_event_rrule_recurrence_id_update_with_exclude():
    """
    test if updates work as they should. The updated event has the extra
    RECURRENCE-ID event removed and one recurrence date excluded via EXDATE
    """
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    dbi.update(event_rrule_recurrence_id, href='12345.ics', etag='abcd')
    dbi.update(event_rrule_recurrence_id_update, href='12345.ics', etag='abcd')
    events = dbi.get_time_range(datetime(2014, 4, 30, 0, 0), datetime(2014, 9, 26, 0, 0))
    events.sort(key=lambda x: x.start)
    assert len(events) == 5
    assert events[0].start == berlin.localize(datetime(2014, 6, 30, 7, 0))
    assert events[1].start == berlin.localize(datetime(2014, 7, 7, 7, 0))
    assert events[2].start == berlin.localize(datetime(2014, 7, 21, 7, 0))
    assert events[3].start == berlin.localize(datetime(2014, 7, 28, 7, 0))
    assert events[4].start == berlin.localize(datetime(2014, 8, 4, 7, 0))


def test_event_delete():
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    assert dbi.list() == list()
    events = dbi.get_time_range(datetime(2014, 6, 30, 0, 0), datetime(2014, 7, 26, 0, 0))
    assert events == list()
    dbi.update(event_rrule_recurrence_id_reverse, href='12345.ics', etag='abcd')
    assert dbi.list() == [('12345.ics', 'abcd')]
    events = dbi.get_time_range(datetime(2014, 4, 30, 0, 0), datetime(2014, 9, 26, 0, 0))
    assert len(events) == 6
    dbi.delete('12345.ics')
    events = dbi.get_time_range(datetime(2014, 4, 30, 0, 0), datetime(2014, 9, 26, 0, 0))
    assert len(events) == 0


event_rrule_this_and_prior = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RRULE:FREQ=WEEKLY;UNTIL=20140806T060000Z
DTSTART;TZID=Europe/Berlin:20140630T070000
DTEND;TZID=Europe/Berlin:20140630T120000
END:VEVENT
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RECURRENCE-ID;RANGE=THISANDPRIOR:20140707T050000Z
DTSTART;TZID=Europe/Berlin:20140707T090000
DTEND;TZID=Europe/Berlin:20140707T140000
END:VEVENT
END:VCALENDAR
"""


def test_this_and_prior():
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    with pytest.raises(UpdateFailed):
        dbi.update(event_rrule_this_and_prior, href='12345.ics', etag='abcd')


event_rrule_this_and_future_temp = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RRULE:FREQ=WEEKLY;UNTIL=20140806T060000Z
DTSTART;TZID=Europe/Berlin:20140630T070000
DTEND;TZID=Europe/Berlin:20140630T120000
END:VEVENT
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit (lang)
RECURRENCE-ID;RANGE=THISANDFUTURE:20140707T050000Z
DTSTART;TZID=Europe/Berlin:{0}
DTEND;TZID=Europe/Berlin:{1}
END:VEVENT
END:VCALENDAR
"""

event_rrule_this_and_future = \
    event_rrule_this_and_future_temp.format('20140707T090000', '20140707T180000')


def test_event_rrule_this_and_future():
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    dbi.update(event_rrule_this_and_future, href='12345.ics', etag='abcd')
    assert dbi.list() == [('12345.ics', 'abcd')]
    events = dbi.get_time_range(datetime(2014, 4, 30, 0, 0), datetime(2014, 9, 26, 0, 0))
    events.sort(key=lambda x: x.start)
    assert len(events) == 6

    assert events[0].start == berlin.localize(datetime(2014, 6, 30, 7, 0))
    assert events[1].start == berlin.localize(datetime(2014, 7, 7, 9, 0))
    assert events[2].start == berlin.localize(datetime(2014, 7, 14, 9, 0))
    assert events[3].start == berlin.localize(datetime(2014, 7, 21, 9, 0))
    assert events[4].start == berlin.localize(datetime(2014, 7, 28, 9, 0))
    assert events[5].start == berlin.localize(datetime(2014, 8, 4, 9, 0))

    assert events[0].end == berlin.localize(datetime(2014, 6, 30, 12, 0))
    assert events[1].end == berlin.localize(datetime(2014, 7, 7, 18, 0))
    assert events[2].end == berlin.localize(datetime(2014, 7, 14, 18, 0))
    assert events[3].end == berlin.localize(datetime(2014, 7, 21, 18, 0))
    assert events[4].end == berlin.localize(datetime(2014, 7, 28, 18, 0))
    assert events[5].end == berlin.localize(datetime(2014, 8, 4, 18, 0))

    assert unicode_type(events[0].vevent['SUMMARY']) == u'Arbeit'
    for event in events[1:]:
        assert unicode_type(event.vevent['SUMMARY']) == u'Arbeit (lang)'


event_rrule_this_and_future_multi_day_shift = \
    event_rrule_this_and_future_temp.format('20140708T090000', '20140709T150000')


def test_event_rrule_this_and_future_multi_day_shift():
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    dbi.update(event_rrule_this_and_future_multi_day_shift, href='12345.ics', etag='abcd')
    assert dbi.list() == [('12345.ics', 'abcd')]
    events = dbi.get_time_range(datetime(2014, 4, 30, 0, 0), datetime(2014, 9, 26, 0, 0))
    events.sort(key=lambda x: x.start)
    assert len(events) == 6

    assert events[0].start == berlin.localize(datetime(2014, 6, 30, 7, 0))
    assert events[1].start == berlin.localize(datetime(2014, 7, 8, 9, 0))
    assert events[2].start == berlin.localize(datetime(2014, 7, 15, 9, 0))
    assert events[3].start == berlin.localize(datetime(2014, 7, 22, 9, 0))
    assert events[4].start == berlin.localize(datetime(2014, 7, 29, 9, 0))
    assert events[5].start == berlin.localize(datetime(2014, 8, 5, 9, 0))

    assert events[0].end == berlin.localize(datetime(2014, 6, 30, 12, 0))
    assert events[1].end == berlin.localize(datetime(2014, 7, 9, 15, 0))
    assert events[2].end == berlin.localize(datetime(2014, 7, 16, 15, 0))
    assert events[3].end == berlin.localize(datetime(2014, 7, 23, 15, 0))
    assert events[4].end == berlin.localize(datetime(2014, 7, 30, 15, 0))
    assert events[5].end == berlin.localize(datetime(2014, 8, 6, 15, 0))

    assert unicode_type(events[0].vevent['SUMMARY']) == u'Arbeit'
    for event in events[1:]:
        assert unicode_type(event.vevent['SUMMARY']) == u'Arbeit (lang)'

event_rrule_this_and_future_allday = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event_rrule_recurrence_id_allday
SUMMARY:Arbeit
RRULE:FREQ=WEEKLY;UNTIL=20140806
DTSTART;VALUE=DATE:20140630
DTEND;VALUE=DATE:20140701
END:VEVENT

BEGIN:VEVENT
UID:event_rrule_recurrence_id_allday
SUMMARY:Arbeit (lang)
RECURRENCE-ID;RANGE=THISANDFUTURE;VALUE=DATE:20140707
DTSTART;VALUE=DATE:20140708
DTEND;VALUE=DATE:20140709
END:VEVENT
END:VCALENDAR
"""


def test_event_rrule_this_and_future_allday():
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    dbi.update(event_rrule_this_and_future_allday, href='rrule_this_and_future_allday.ics', etag='abcd')
    assert dbi.list() == [('rrule_this_and_future_allday.ics', 'abcd')]
    events = dbi.get_allday_range(datetime(2014, 4, 30, 0, 0), datetime(2014, 9, 26, 0, 0))
    events.sort(key=lambda x: x.start)
    assert len(events) == 6

    assert events[0].start == date(2014, 6, 30)
    assert events[1].start == date(2014, 7, 8)
    assert events[2].start == date(2014, 7, 15)
    assert events[3].start == date(2014, 7, 22)
    assert events[4].start == date(2014, 7, 29)
    assert events[5].start == date(2014, 8, 5)

    assert events[0].end == date(2014, 7, 1)
    assert events[1].end == date(2014, 7, 9)
    assert events[2].end == date(2014, 7, 16)
    assert events[3].end == date(2014, 7, 23)
    assert events[4].end == date(2014, 7, 30)
    assert events[5].end == date(2014, 8, 6)

    assert unicode_type(events[0].vevent['SUMMARY']) == u'Arbeit'
    for event in events[1:]:
        assert unicode_type(event.vevent['SUMMARY']) == u'Arbeit (lang)'


master = """BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RRULE:FREQ=WEEKLY;UNTIL=20140806T060000Z
DTSTART;TZID=Europe/Berlin:20140630T070000
DTEND;TZID=Europe/Berlin:20140630T120000
END:VEVENT"""

recuid_this_future = icalendar.Event.from_ical("""BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RECURRENCE-ID;RANGE=THISANDFUTURE:20140707T050000Z
DTSTART;TZID=Europe/Berlin:20140707T090000
DTEND;TZID=Europe/Berlin:20140707T140000
END:VEVENT""")

recuid_this_future_duration = icalendar.Event.from_ical("""BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RECURRENCE-ID;RANGE=THISANDFUTURE:20140707T050000Z
DTSTART;TZID=Europe/Berlin:20140707T090000
DURATION:PT4H30M
END:VEVENT""")


def test_calc_shift_deltas():
    assert (timedelta(hours=2), timedelta(hours=5)) == \
        backend.calc_shift_deltas(recuid_this_future)
    assert (timedelta(hours=2), timedelta(hours=4, minutes=30)) == \
        backend.calc_shift_deltas(recuid_this_future_duration)
