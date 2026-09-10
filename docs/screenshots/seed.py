"""
Post-seed state for the documentation capture run.

The harness runs this inside the web container after `seed_docs_demo` has
applied docs/screenshots/fixture.json and before the collection cycle, via
`adl shell <`. It exists because this plugin's "source" is ADL's own
database: there is nothing to mock and nothing to dial, so the demo has to
contain observations somebody submitted.

What the declarative fixture cannot express, and this does:

* two observer users, attached to each station link's Observers panel — the
  list the field app authorises against;
* office and field submissions across the last two days, each with its
  per-parameter records, so the connection overview, the station detail page
  and the monitoring dashboard have something to show;
* one submission left deliberately unprocessed and dated before the link's
  Collection Start Date, because the guide documents that state and an
  operator meeting it needs to recognise the screen.

Values are a smooth diurnal cycle plus noise. Nothing here is real data and
no real person is named.
"""

import math
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone as dj_timezone

from adl_collector_app_plugin.models import (
    CollectorSubmission,
    CollectorSubmissionRecord,
    ManualObservationConnection,
    ManualObservationStationLink,
    ManualObservationStationLinkObserver,
)

User = get_user_model()

OBSERVERS = [
    ("aketch", "Aketch", "Odhiambo"),
    ("mwangi", "Mwangi", "Kariuki"),
]

connection = ManualObservationConnection.objects.get(name="Demo Manual Observations")
links = list(
    ManualObservationStationLink.objects.filter(network_connection=connection)
    .order_by("id")
)

# -- observers ---------------------------------------------------------------

observer_users = []
for username, first, last in OBSERVERS:
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"first_name": first, "last_name": last,
                  "email": f"{username}@example.test"},
    )
    if created:
        user.set_password("adl-docs-demo")
        user.save()
    observer_users.append(user)

# CollectorSubmission.observer points at the observer *row*, not the user, so
# keep them per link to attribute submissions below.
observers_by_link = {}
for link in links:
    ManualObservationStationLinkObserver.objects.filter(station_link=link).delete()
    observers_by_link[link.id] = [
        ManualObservationStationLinkObserver.objects.create(
            station_link=link, user=user, enabled=True
        )
        for user in observer_users
    ]

# -- submissions -------------------------------------------------------------


def reading(mapping, moment, seed):
    rng = random.Random(f"{seed}-{mapping.id}-{moment:%Y%m%d%H}")
    hour = moment.hour + moment.minute / 60
    diurnal = math.sin((hour - 9) / 24 * 2 * math.pi)
    name = mapping.adl_parameter.name
    if name == "Air Temperature":
        return round(22 + 6 * diurnal + rng.uniform(-0.4, 0.4), 1)
    if name == "Relative Humidity":
        return round(68 - 22 * diurnal + rng.uniform(-2, 2), 0)
    if name == "Atmospheric Pressure":
        return round(1012 + 2 * math.sin(hour / 12 * math.pi) + rng.uniform(-0.3, 0.3), 1)
    if name == "Precipitation":
        return round(rng.choice([0.0, 0.0, 0.0, 0.2, 0.8]) if 14 <= hour <= 17 else 0.0, 1)
    return round(rng.uniform(0, 10), 1)


def submit(link, moment, observer=None, office_user=None, processed=False):
    mappings = list(link.get_variable_mappings())
    values = {str(m.adl_parameter_id): reading(m, moment, link.id) for m in mappings}
    submission = CollectorSubmission.objects.create(
        station_link=link,
        observer=observer,
        office_submitted_by=office_user,
        submission_time=moment + timedelta(minutes=4),
        observation_time=moment,
        is_test_submission=False,
        idempotency_key=f"docs-{link.id}-{moment:%Y%m%d%H%M}",
        content_hash=f"{link.id}-{moment:%Y%m%d%H%M}",
        data={"values": values, "source": "office" if office_user else "field"},
    )
    for mapping in mappings:
        CollectorSubmissionRecord.objects.create(
            submission=submission,
            variable_mapping=mapping,
            value=values[str(mapping.adl_parameter_id)],
            is_processed=processed,
        )
    return submission


admin = User.objects.filter(is_superuser=True).order_by("id").first()
now = dj_timezone.localtime(dj_timezone.now(), connection.stations_timezone)
synoptic = now.replace(minute=0, second=0, microsecond=0)

CollectorSubmission.objects.filter(station_link__in=links).delete()

created = 0
for link in links:
    # The last two days at the standard synoptic hours, alternating between an
    # observer's field submission and an office entry, so both routes appear.
    for hours_back in range(0, 48, 3):
        moment = synoptic - timedelta(hours=hours_back)
        if moment < link.start_date:
            continue
        link_observers = observers_by_link[link.id]
        if hours_back % 6 == 0:
            submit(link, moment, office_user=admin)
        else:
            submit(link, moment,
                   observer=link_observers[hours_back % len(link_observers)])
        created += 1

# One submission before the collection start date: core rejects it on every
# sweep and never marks it processed, which is the "unprocessed count never
# drops" state the guide's Troubleshooting section describes.
stuck = submit(links[0], links[0].start_date - timedelta(hours=6),
               observer=observers_by_link[links[0].id][0])

print(f"[docs-seed] {len(observer_users)} observer(s), {created} submission(s) "
      f"across {len(links)} station link(s), plus one before the start date "
      f"(submission {stuck.id}) to show the unprocessed state")
