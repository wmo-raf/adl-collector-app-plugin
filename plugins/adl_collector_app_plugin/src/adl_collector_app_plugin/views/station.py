import datetime

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.messages import success as msg_success
from django.db.models import Prefetch
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone as dj_timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views import View

from ..models import (
    ManualObservationStationLink,
    CollectorSubmission,
    CollectorSubmissionRecord,
    ManualObservationConnection,
    SynopMessage,
    SynopParameterMapping,
)
from ..synop_utils import sync_synop_mappings_for_station


@staff_member_required
def connection_overview(request, pk):
    """
    Landing page for a specific ManualObservationConnection.
    Shows action cards + today's 24-hour collection-status bars per station.
    """
    connection = get_object_or_404(ManualObservationConnection, pk=pk)

    station_links = (
        ManualObservationStationLink.objects
        .filter(network_connection=connection, enabled=True)
        .select_related("station")
        .order_by("station__name")
    )

    today = dj_timezone.now().date()
    hourly_rows = (
        CollectorSubmission.objects
        .filter(
            station_link__network_connection=connection,
            observation_time__date=today,
            is_test_submission=False,
        )
        .values("station_link_id", "observation_time__hour")
        .distinct()
    )
    coverage = {}
    for row in hourly_rows:
        coverage.setdefault(row["station_link_id"], set()).add(row["observation_time__hour"])

    station_status = [
        {
            "station_link": sl,
            "hours": [h in coverage.get(sl.id, set()) for h in range(24)],
            "detail_url": reverse("collector_station_detail", args=[pk, sl.pk]),
        }
        for sl in station_links
    ]

    # --- Stats for info cards ---
    # Station link count (all, including disabled)
    station_link_count = ManualObservationStationLink.objects.filter(
        network_connection=connection
    ).count()

    # Station link list + add URLs via the registered viewset
    from adl.core.registries import station_link_viewset_registry
    from adl.core.utils import get_model_by_string_label
    _sl_model = get_model_by_string_label(connection.station_link_model_string_label)
    _sl_viewset = station_link_viewset_registry.get(_sl_model._meta.model_name)
    _conn_qs = f"?network_connection={connection.id}"
    station_links_url = reverse(_sl_viewset.get_url_name("index")) + _conn_qs
    station_links_add_url = reverse(_sl_viewset.get_url_name("add")) + _conn_qs

    # SYNOP param count (global)
    synop_param_count = SynopParameterMapping.objects.count()

    context = {
        "page_title": connection.name,
        "connection": connection,
        "station_status": station_status,
        "today": today,
        "hour_labels": list(range(24)),
        # info cards
        "station_link_count": station_link_count,
        "station_links_url": station_links_url,
        "station_links_add_url": station_links_add_url,
        "synop_param_count": synop_param_count,
    }
    return render(request, "adl_collector_app_plugin/office/connection_overview.html", context)


@staff_member_required
def connection_selector(request):
    """
    Shown when multiple ManualObservationConnections exist.
    Lets the user pick which connection to work with.
    """
    connections = ManualObservationConnection.objects.order_by("name")
    return render(request, "adl_collector_app_plugin/office/connection_selector.html", {
        "page_title": _("Manual Stations"),
        "connections": connections,
    })


@staff_member_required
def sync_station_synop_mappings_view(request, pk):
    """
    POST-only: create any missing ManualObservationStationLinkVariableMapping rows
    for all enabled stations on a connection, based on the global SynopParameterMapping table.
    Idempotent — skips parameters already mapped.
    """
    conn = get_object_or_404(ManualObservationConnection, pk=pk)
    if request.method != "POST":
        return redirect(reverse("collector_connection_overview", args=[pk]))

    station_links = ManualObservationStationLink.objects.filter(
        network_connection=conn, enabled=True
    )
    total_created = 0
    station_count = 0
    for sl in station_links:
        total_created += sync_synop_mappings_for_station(sl)
        station_count += 1

    msg_success(
        request,
        f"Synced {total_created} missing SYNOP variable mapping(s) across {station_count} station(s) "
        f"for '{conn.name}'.",
    )
    return redirect(reverse("collector_connection_overview", args=[pk]))


@method_decorator(staff_member_required, name="dispatch")
class StationDetailView(View):
    """
    Per-station submission detail page.

    Displays a filterable table of all non-test submissions for a station on a given date.
    Each row shows observation time, per-parameter values, entry method badge, and an Edit link
    that opens the appropriate form pre-populated with the original data.
    """

    def get(self, request, pk, station_pk):
        connection = get_object_or_404(ManualObservationConnection, pk=pk)
        station_link = get_object_or_404(
            ManualObservationStationLink,
            pk=station_pk,
            network_connection=connection,
        )

        date_str = request.GET.get("date")
        try:
            selected_date = (
                datetime.date.fromisoformat(date_str) if date_str else dj_timezone.now().date()
            )
        except ValueError:
            selected_date = dj_timezone.now().date()

        submissions = list(
            CollectorSubmission.objects
            .filter(
                station_link=station_link,
                observation_time__date=selected_date,
                is_test_submission=False,
            )
            .prefetch_related(
                Prefetch(
                    "records",
                    queryset=CollectorSubmissionRecord.objects.select_related(
                        "variable_mapping__adl_parameter",
                        "variable_mapping__obs_parameter_unit",
                    ),
                )
            )
            .select_related("observer__user", "office_submitted_by")
            .order_by("observation_time")
        )

        sub_ids = [s.id for s in submissions]
        synop_sub_ids = (
            set(
                SynopMessage.objects
                .filter(submission_id__in=sub_ids)
                .values_list("submission_id", flat=True)
            )
            if sub_ids else set()
        )

        params_seen = {}
        for sub in submissions:
            for rec in sub.records.all():
                p = rec.variable_mapping.adl_parameter
                params_seen[p.id] = p
        sorted_params = sorted(params_seen.values(), key=lambda p: p.name)

        rows = []
        for sub in submissions:
            values_by_param = {
                rec.variable_mapping.adl_parameter_id: rec.value
                for rec in sub.records.all()
            }

            if sub.id in synop_sub_ids:
                method = "SYNOP"
                edit_url = (
                    reverse("collector_office_synop")
                    + f"?connection={pk}&submission_id={sub.id}"
                )
            elif sub.observer_id:
                method = "Field Observer"
                edit_url = (
                    reverse("collector_office_entry")
                    + f"?connection={pk}&submission_id={sub.id}"
                )
            else:
                method = "Office Direct"
                edit_url = (
                    reverse("collector_office_entry")
                    + f"?connection={pk}&submission_id={sub.id}"
                )

            rows.append({
                "submission": sub,
                "method": method,
                "edit_url": edit_url,
                "values": [values_by_param.get(p.id) for p in sorted_params],
            })

        context = {
            "page_title": f"{station_link.station.name} — Detail",
            "connection": connection,
            "station_link": station_link,
            "selected_date": selected_date,
            "sorted_params": sorted_params,
            "rows": rows,
        }
        return render(request, "adl_collector_app_plugin/office/station_detail.html", context)


def view_test_collector_submissions(request):
    submissions = (
        CollectorSubmission.objects
        .filter(is_test_submission=True)
        .select_related("observer__user", "office_submitted_by", "station_link")
        .prefetch_related(
            Prefetch(
                "records",
                queryset=CollectorSubmissionRecord.objects.select_related("variable_mapping"),
            )
        )
        .order_by("-created_at")[:100]
    )

    return render(
        request,
        "adl_collector_app_plugin/test_submissions.html",
        {
            "submissions": submissions,
            "page_title": "Test Collector Submissions",
        }
    )
