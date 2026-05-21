from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Max, Q
from django.shortcuts import render
from django.utils import timezone as dj_timezone
from django.utils.decorators import method_decorator
from django.views import View

from ..models import (
    CollectorSubmission,
    CollectorSubmissionRecord,
    ManualObservationStationLink,
    ManualObservationStationLinkObserver,
    SynopMessage,
)

PERIOD_DAYS = [1, 7, 30]


@method_decorator(staff_member_required, name="dispatch")
class MonitoringDashboardView(View):
    """
    Overview dashboard: submission counts, observer activity, missing-data gaps,
    and SYNOP message archive.
    """

    def get(self, request):
        period_days = int(request.GET.get("days", 7))
        if period_days not in PERIOD_DAYS:
            period_days = 7
        since = dj_timezone.now() - timedelta(days=period_days)

        station_stats = (
            ManualObservationStationLink.objects
            .filter(enabled=True)
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
            )
            .order_by("station__name")
        )

        observer_activity = (
            ManualObservationStationLinkObserver.objects
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
            .order_by("-submission_count")
        )

        unprocessed_count = (
            CollectorSubmissionRecord.objects
            .filter(is_processed=False, submission__created_at__gte=since)
            .count()
        )

        recent_submissions = (
            CollectorSubmission.objects
            .filter(created_at__gte=since, is_test_submission=False)
            .select_related(
                "station_link__station",
                "observer__user",
                "office_submitted_by",
            )
            .order_by("-created_at")[:50]
        )

        synop_messages = (
            SynopMessage.objects
            .filter(received_at__gte=since)
            .select_related("station_link__station", "submitted_by", "submission")
            .order_by("-received_at")[:50]
        )

        context = {
            "page_title": "Data Collection Monitoring",
            "period_days": period_days,
            "period_choices": PERIOD_DAYS,
            "station_stats": station_stats,
            "observer_activity": observer_activity,
            "unprocessed_count": unprocessed_count,
            "recent_submissions": recent_submissions,
            "synop_messages": synop_messages,
        }
        return render(request, "adl_collector_app_plugin/monitoring/dashboard.html", context)
