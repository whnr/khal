from datetime import datetime, date, timedelta, time
import os
from time import sleep
from textwrap import dedent

import pytest

from vdirsyncer.storage.base import Item

import khal.aux

from khal.khalendar import Calendar, CalendarCollection
from khal.khalendar.event import Event
from khal.khalendar.backend import CouldNotCreateDbDir
import khal.khalendar.exceptions

from .aux import _get_text, cal1, cal2, cal3
from . import aux


today = date.today()
yesterday = today - timedelta(days=1)
tomorrow = today + timedelta(days=1)

event_allday_template = u"""BEGIN:VEVENT
SEQUENCE:0
UID:uid3@host1.com
DTSTART;VALUE=DATE:{}
DTEND;VALUE=DATE:{}
SUMMARY:a meeting
DESCRIPTION:short description
LOCATION:LDB Lobby
END:VEVENT"""

event_today = event_allday_template.format(today.strftime('%Y%m%d'),
                                           tomorrow.strftime('%Y%m%d'))
item_today = Item(event_today)


class TestCalendar(object):

    def test_create(self, cal_vdir):
        assert True

    def test_new_event(self, coll_vdirs_disk):
        coll, vdirs = coll_vdirs_disk
        event = coll.new_event(event_today, cal1)
        assert event.calendar == cal1
        coll.new(event)
        events = list(coll.get_events_on(today))
        assert len(events) == 1
        assert events[0].color == 'dark blue'
        assert len(list(coll.get_events_on(tomorrow))) == 0
        assert len(list(coll.get_events_on(yesterday))) == 0
        assert len(list(vdirs[cal1].list())) == 1

    def test_db_needs_update(self, cal_vdir):
        cal, vdir = cal_vdir
        vdir.upload(item_today)
        cal.db_update()
        assert cal._db_needs_update() is False

    def test_db_needs_update_after_insert(self, cal_vdir):
        cal, vdir = cal_vdir
        event = cal.new_event(event_today)
        cal.new(event)
        assert cal._db_needs_update() is False


class TestVdirsyncerCompat(object):
    def test_list(self, cal_vdir):
        cal, vdir = cal_vdir
        event = Event.fromString(event_d, calendar=cal.name, locale=aux.locale)
        cal.new(event)
        event = Event.fromString(event_today, calendar=cal.name, locale=aux.locale)
        cal.new(event)
        hrefs = sorted(href for href, uid in cal._dbtool.list())
        assert set(str(cal._dbtool.get(href).uid) for href in hrefs) == set((
            'uid3@host1.com',
            'V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU',
        ))

aday = date(2014, 4, 9)
bday = date(2014, 4, 10)


event_dt = _get_text('event_dt_simple')
event_d = _get_text('event_d')
event_d_no_value = _get_text('event_d_no_value')


class TestCollection(object):

    astart = datetime.combine(aday, time.min)
    aend = datetime.combine(aday, time.max)
    bstart = datetime.combine(bday, time.min)
    bend = datetime.combine(bday, time.max)
    astart_berlin = aux.BERLIN.localize(astart)
    aend_berlin = aux.BERLIN.localize(aend)
    bstart_berlin = aux.BERLIN.localize(bstart)
    bend_berlin = aux.BERLIN.localize(bend)

    def test_default_calendar(self, tmpdir):
        coll = CalendarCollection(locale=aux.locale)
        props = {}
        coll.append(Calendar('foobar', ':memory:', str(tmpdir),
                             readonly=True, locale=aux.locale), props=props)
        coll.append(Calendar('home', ':memory:', str(tmpdir),
                             locale=aux.locale), props=props)
        coll.append(Calendar('work', ':memory:', str(tmpdir),
                             readonly=True, locale=aux.locale), props=props)
        assert coll.default_calendar_name is None
        with pytest.raises(ValueError):
            coll.default_calendar_name = 'work'
        assert coll.default_calendar_name is None
        with pytest.raises(ValueError):
            coll.default_calendar_name = 'unknownstuff'
        assert coll.default_calendar_name is None
        coll.default_calendar_name = 'home'
        assert coll.default_calendar_name == 'home'
        assert coll.writable_names == ['home']

    def test_empty(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        start = datetime.combine(today, time.min)
        end = datetime.combine(today, time.max)
        assert list(coll.get_floating(start, end)) == list()
        assert list(coll.get_localized(aux.BERLIN.localize(start),
                                       aux.BERLIN.localize(end))) == list()

    def test_insert(self, coll_vdirs_disk):
        """insert a localized event"""
        coll, vdirs = coll_vdirs_disk
        event = Event.fromString(event_dt, calendar=cal1, locale=aux.locale)
        coll.new(event, cal1)
        events = list(coll.get_localized(self.astart_berlin, self.aend_berlin))
        assert len(events) == 1
        assert events[0].color == 'dark blue'
        assert events[0].calendar == cal1

        events = list(coll.get_events_on(aday))
        assert len(events) == 1
        assert events[0].color == 'dark blue'
        assert events[0].calendar == cal1

        assert len(list(vdirs[cal1].list())) == 1
        assert len(list(vdirs[cal2].list())) == 0
        assert len(list(vdirs[cal3].list())) == 0
        assert list(coll.get_floating(self.astart, self.aend)) == []

    def test_insert_d(self, coll_vdirs_disk):
        """insert a floating event"""
        coll, vdirs = coll_vdirs_disk

        event = Event.fromString(event_d, calendar='foo', locale=aux.locale)
        coll.new(event, cal1)
        events = list(coll.get_events_on(aday))
        assert len(events) == 1
        assert events[0].calendar == cal1
        assert events[0].color == 'dark blue'
        assert len(list(vdirs[cal1].list())) == 1
        assert len(list(vdirs[cal2].list())) == 0
        assert len(list(vdirs[cal3].list())) == 0
        assert list(coll.get_localized(self.bstart_berlin, self.bend_berlin)) == []

    def test_insert_d_no_value(self, coll_vdirs_disk):
        """insert a date event with no VALUE=DATE option"""
        coll, vdirs = coll_vdirs_disk

        event = Event.fromString(event_d_no_value, calendar='foo', locale=aux.locale)
        coll.new(event, cal1)
        events = list(coll.get_events_on(aday))
        assert len(events) == 1
        assert events[0].calendar == cal1
        assert len(list(vdirs[cal1].list())) == 1
        assert len(list(vdirs[cal2].list())) == 0
        assert len(list(vdirs[cal3].list())) == 0
        assert list(coll.get_localized(self.bstart_berlin, self.bend_berlin)) == []

    def test_change(self, coll_vdirs_disk):
        """moving an event from one calendar to another"""
        coll, vdirs = coll_vdirs_disk
        event = Event.fromString(event_dt, calendar='foo', locale=aux.locale)
        coll.new(event, cal1)
        event = list(coll.get_events_on(aday))[0]
        assert event.calendar == cal1

        coll.change_collection(event, cal2)
        events = list(coll.get_events_on(aday))
        assert len(events) == 1
        assert events[0].calendar == cal2

    def test_update_event(self, coll_vdirs_disk):
        """updating one event"""
        coll, vdirs = coll_vdirs_disk
        event = Event.fromString(
            _get_text('event_dt_simple'), calendar=cal1, locale=aux.locale)
        coll.new(event, cal1)
        events = coll.get_events_on(aday)
        event = list(events)[0]
        event.update_summary('really simple event')
        event.update_start_end(bday, bday)
        coll.update(event)
        events = list(coll.get_localized(self.astart_berlin, self.aend_berlin))
        assert len(events) == 0
        events = list(coll.get_floating(self.bstart, self.bend))
        assert len(events) == 1
        assert events[0].summary == 'really simple event'

    def test_newevent(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        event = khal.aux.new_event(dtstart=aday, timezone=aux.BERLIN)
        event = coll.new_event(event.to_ical(), coll.default_calendar_name)
        assert event.allday is False

    def test_modify_readonly_calendar(self, tmpdir):
        coll = CalendarCollection(locale=aux.locale)
        props = {}
        coll.append(Calendar('foobar', ':memory:', str(tmpdir),
                             readonly=True, locale=aux.locale), props=props)
        coll.append(Calendar('home', ':memory:', str(tmpdir),
                             locale=aux.locale), props=props)
        coll.append(Calendar('work', ':memory:', str(tmpdir),
                             readonly=True, locale=aux.locale), props=props)
        event = Event.fromString(event_dt, calendar='home', locale=aux.locale)

        with pytest.raises(khal.khalendar.exceptions.ReadOnlyCalendarError):
            coll.new(event, cal1)
        with pytest.raises(khal.khalendar.exceptions.ReadOnlyCalendarError):
            # params don't really matter here
            coll.delete('href', 'eteg', cal1)

    def test_search(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        assert len(coll.search('Event')) == 0
        event = Event.fromString(
            _get_text('event_dt_simple'), calendar=cal1, locale=aux.locale)
        coll.new(event, cal1)
        assert len(coll.search('Event')) == 1

    def test_get_events_at(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        a_time = aux.BERLIN.localize(datetime(2014, 4, 9, 10))
        b_time = aux.BERLIN.localize(datetime(2014, 4, 9, 11))
        assert len(coll.get_events_at(a_time)) == 0
        event = Event.fromString(
            _get_text('event_dt_simple'), calendar=cal1, locale=aux.locale)
        coll.new(event, cal1)
        assert len(coll.get_events_at(a_time)) == 1
        assert len(coll.get_events_at(b_time)) == 0

    def test_delete_two_events(self, coll_vdirs_disk):
            """testing if we can delete any of two events in two different
            calendars with the same filename"""
            coll, vdirs = coll_vdirs_disk
            event1 = Event.fromString(_get_text('event_dt_simple'),
                                      calendar=cal1, locale=aux.locale)
            event2 = Event.fromString(_get_text('event_dt_simple'),
                                      calendar=cal2, locale=aux.locale)
            coll.new(event1, cal1)
            sleep(0.1)  # make sure the etags are different
            coll.new(event2, cal2)
            etag1 = list(vdirs['foobar'].list())[0][1]
            etag2 = list(vdirs['work'].list())[0][1]
            events = list(coll.get_localized(self.astart_berlin, self.aend_berlin))
            assert len(events) == 2
            assert events[0].calendar != events[1].calendar
            for event in events:
                if event.calendar == 'foobar':
                    assert event.etag == etag1
                if event.calendar == 'work':
                    assert event.etag == etag2


@pytest.fixture
def cal_dbpath(tmpdir):
    name = 'testcal'
    vdirpath = str(tmpdir) + '/' + name
    dbpath = str(tmpdir) + '/subdir/' + 'khal.db'
    cal = Calendar(name, dbpath, vdirpath, locale=aux.locale)

    return cal, dbpath


class TestDbCreation(object):

    def test_create_db(self, tmpdir):
        name = 'testcal'
        vdirpath = str(tmpdir) + '/' + name
        dbdir = str(tmpdir) + '/subdir/'
        dbpath = dbdir + 'khal.db'

        assert not os.path.isdir(dbdir)
        Calendar(name, dbpath, vdirpath, aux.locale)
        assert os.path.isdir(dbdir)

    def test_failed_create_db(self, tmpdir):
        name = 'testcal'
        vdirpath = str(tmpdir) + '/' + name
        dbdir = str(tmpdir) + '/subdir/'
        dbpath = dbdir + 'khal.db'

        os.chmod(str(tmpdir), 400)

        with pytest.raises(CouldNotCreateDbDir):
            Calendar(name, dbpath, vdirpath, aux.locale)


def test_default_calendar(coll_vdirs_disk):
    """test if an update to the vdir is detected by the CalendarCollection"""
    coll, vdirs = coll_vdirs_disk
    vdir = vdirs['foobar']
    event = coll.new_event(event_today, 'foobar')
    vdir.upload(event)
    href, etag = list(vdir.list())[0]
    assert len(list(coll.get_events_on(today))) == 0
    coll.db_update()
    assert len(list(coll.get_events_on(today))) == 1
    vdir.delete(href, etag)
    assert len(list(coll.get_events_on(today))) == 1
    coll.db_update()
    assert len(list(coll.get_events_on(today))) == 0


def test_only_update_old_event(cal_vdir, monkeypatch):
    cal, vdir = cal_vdir

    href_one, etag_one = vdir.upload(cal.new_event(dedent("""
    BEGIN:VEVENT
    UID:meeting-one
    DTSTART;VALUE=DATE:20140909
    DTEND;VALUE=DATE:20140910
    SUMMARY:first meeting
    END:VEVENT
    """)))

    href_two, etag_two = vdir.upload(cal.new_event(dedent("""
    BEGIN:VEVENT
    UID:meeting-two
    DTSTART;VALUE=DATE:20140910
    DTEND;VALUE=DATE:20140911
    SUMMARY:second meeting
    END:VEVENT
    """)))

    cal.db_update()
    assert not cal._db_needs_update()

    old_update_vevent = cal._update_vevent
    updated_hrefs = []

    def _update_vevent(href):
        updated_hrefs.append(href)
        return old_update_vevent(href)
    monkeypatch.setattr(cal, '_update_vevent', _update_vevent)

    href_three, etag_three = vdir.upload(cal.new_event(dedent("""
    BEGIN:VEVENT
    UID:meeting-three
    DTSTART;VALUE=DATE:20140911
    DTEND;VALUE=DATE:20140912
    SUMMARY:third meeting
    END:VEVENT
    """)))

    assert cal._db_needs_update()
    cal.db_update()
    assert updated_hrefs == [href_three]
