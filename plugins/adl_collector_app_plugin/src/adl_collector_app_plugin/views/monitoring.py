import datetime

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Max, Min, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone as dj_timezone
from django.utils.decorators import method_decorator
from django.views import View

from ..models import (
    CollectorSubmission,
    CollectorSubmissionRecord,
    ManualObservationConnection,
    ManualObservationStationLink,
    ManualObservationStationLinkObserver,
    SynopMessage,
)

PERIOD_DAYS = [1, 7, 30]


@method_decorator(staff_member_required, name="dispatch")
class MonitoringDashboardView(View):
    def get(self, request):
        connection_pk = request.GET.get("connection")
        if not connection_pk:
            connections = ManualObservationConnection.objects.order_by("name")
            return render(
                request,
                "adl_collector_app_plugin/monitoring/connection_selector.html",
                {"page_title": "Monitoring — Select Connection", "connections": connections},
            )

        connection = get_object_or_404(ManualObservationConnection, pk=connection_pk)

        period_days = int(request.GET.get("days", 7))
        if period_days not in PERIOD_DAYS:
            period_days = 7
        since = dj_timezone.now() - datetime.timedelta(days=period_days)

        station_stats = list(
            ManualObservationStationLink.objects
            .filter(enabled=True, network_connection=connection)
            .select_related("station", "network_connection")
            .annotate(
                submission_count=Count(
                    "submissions",
                    filter=Q(submissions__created_at__gte=since),
                ),
                last_submission=Max(
                    "submissions__created_at",
                    filter=Q(submissions__created_at__gte=since),
                ),
                earliest_obs=Min("submissions__observation_time"),
                latest_obs=Max("submissions__observation_time"),
            )
            .order_by("station__name")
        )
        for sl in station_stats:
            sl.has_data_before_start = bool(
                sl.start_date and sl.earliest_obs and sl.earliest_obs < sl.start_date
            )

        observer_activity = (
            ManualObservationStationLinkObserver.objects
            .filter(station_link__network_connection=connection)
            .select_related("user", "station_link__station")
            .annotate(
                submission_count=Count(
                    "submissions",
                    filter=Q(submissions__created_at__gte=since),
                ),
                last_seen=Max(
                    "submissions__created_at",
                    filter=Q(submissions__created_at__gte=since),
                ),
            )
            .order_by("-submission_count")[:10]
        )

        unprocessed_count = (
            CollectorSubmissionRecord.objects
            .filter(
                is_processed=False,
                submission__created_at__gte=since,
                submission__station_link__network_connection=connection,
            )
            .count()
        )

        recent_submissions = (
            CollectorSubmission.objects
            .filter(
                created_at__gte=since,
                is_test_submission=False,
                station_link__network_connection=connection,
            )
            .select_related(
                "station_link__station",
                "observer__user",
                "office_submitted_by",
            )
            .order_by("-created_at")[:10]
        )

        synop_messages = None
        if connection.enable_office_entry:
            synop_messages = (
                SynopMessage.objects
                .filter(
                    received_at__gte=since,
                    station_link__network_connection=connection,
                )
                .select_related("station_link__station", "submitted_by", "submission")
                .order_by("-received_at")[:10]
            )

        context = {
            "page_title": "Data Collection Monitoring",
            "connection": connection,
            "period_days": period_days,
            "period_choices": PERIOD_DAYS,
            "station_stats": station_stats,
            "observer_activity": observer_activity,
            "unprocessed_count": unprocessed_count,
            "recent_submissions": recent_submissions,
            "synop_messages": synop_messages,
        }

        return render(request, "adl_collector_app_plugin/monitoring/dashboard.html", context)


@method_decorator(staff_member_required, name="dispatch")
class TriggerReprocessView(View):
    def post(self, request):
        connection = get_object_or_404(ManualObservationConnection, pk=request.POST.get("connection", 0))

        sl_ids = list(
            CollectorSubmissionRecord.objects
            .filter(is_processed=False, submission__station_link__network_connection=connection)
            .values_list("submission__station_link_id", flat=True)
            .distinct()
        )

        if sl_ids:
            from adl.core.tasks import process_station_link_batch
            process_station_link_batch.delay(connection.pk, sl_ids)

        days = request.POST.get("days", 7)
        return redirect(reverse("collector_monitoring") + f"?connection={connection.pk}&days={days}")


def _parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


@method_decorator(staff_member_required, name="dispatch")
class MonitoringSubmissionsListView(View):
    def get(self, request):
        connection = get_object_or_404(ManualObservationConnection, pk=request.GET.get("connection", 0))
        date_str = request.GET.get("date", "")
        selected_date = _parse_date(date_str)

        qs = (
            CollectorSubmission.objects
            .filter(is_test_submission=False, station_link__network_connection=connection)
            .select_related("station_link__station", "observer__user", "office_submitted_by")
        )
        if selected_date:
            qs = qs.filter(created_at__date=selected_date)

        submissions = qs.order_by("-created_at")[:200]

        return render(
            request,
            "adl_collector_app_plugin/monitoring/submissions_list.html",
            {
                "page_title": "Submissions — " + connection.name,
                "connection": connection,
                "submissions": submissions,
                "selected_date": date_str,
            },
        )


@method_decorator(staff_member_required, name="dispatch")
class MonitoringSynopListView(View):
    def get(self, request):
        connection = get_object_or_404(ManualObservationConnection, pk=request.GET.get("connection", 0))
        date_str = request.GET.get("date", "")
        selected_date = _parse_date(date_str)

        qs = (
            SynopMessage.objects
            .filter(station_link__network_connection=connection)
            .select_related("station_link__station", "submitted_by", "submission")
        )
        if selected_date:
            qs = qs.filter(received_at__date=selected_date)

        synop_messages = qs.order_by("-received_at")[:200]

        return render(
            request,
            "adl_collector_app_plugin/monitoring/synop_list.html",
            {
                "page_title": "SYNOP Archive — " + connection.name,
                "connection": connection,
                "synop_messages": synop_messages,
                "selected_date": date_str,
            },
        )


@method_decorator(staff_member_required, name="dispatch")
class MonitoringObserversListView(View):
    def get(self, request):
        connection = get_object_or_404(ManualObservationConnection, pk=request.GET.get("connection", 0))
        date_str = request.GET.get("date", "")
        selected_date = _parse_date(date_str)

        if selected_date:
            count_filter = Q(submissions__created_at__date=selected_date)
        else:
            count_filter = Q()

        observers = (
            ManualObservationStationLinkObserver.objects
            .filter(station_link__network_connection=connection)
            .select_related("user", "station_link__station")
            .annotate(
                submission_count=Count("submissions", filter=count_filter),
                last_seen=Max("submissions__created_at", filter=count_filter),
            )
            .order_by("-submission_count")[:200]
        )

        return render(
            request,
            "adl_collector_app_plugin/monitoring/observers_list.html",
            {
                "page_title": "Observer Activity — " + connection.name,
                "connection": connection,
                "observers": observers,
                "selected_date": date_str,
            },
        )


@method_decorator(staff_member_required, name="dispatch")
class MonitoringStationsListView(View):
    def get(self, request):
        connection = get_object_or_404(ManualObservationConnection, pk=request.GET.get("connection", 0))
        date_str = request.GET.get("date", "")
        selected_date = _parse_date(date_str)

        if selected_date:
            count_filter = Q(submissions__created_at__date=selected_date)
        else:
            count_filter = Q()

        stations = list(
            ManualObservationStationLink.objects
            .filter(network_connection=connection)
            .select_related("station", "network_connection")
            .annotate(
                submission_count=Count("submissions", filter=count_filter),
                last_submission=Max("submissions__created_at", filter=count_filter),
                earliest_obs=Min("submissions__observation_time"),
                latest_obs=Max("submissions__observation_time"),
            )
            .order_by("station__name")[:200]
        )
        for sl in stations:
            sl.has_data_before_start = bool(
                sl.start_date and sl.earliest_obs and sl.earliest_obs < sl.start_date
            )

        return render(
            request,
            "adl_collector_app_plugin/monitoring/stations_list.html",
            {
                "page_title": "Station Status — " + connection.name,
                "connection": connection,
                "stations": stations,
                "selected_date": date_str,
            },
        )
