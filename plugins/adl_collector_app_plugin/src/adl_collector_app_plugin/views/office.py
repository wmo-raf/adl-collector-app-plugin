import datetime
import zoneinfo

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Prefetch
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone as dj_timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views import View
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..forms import SynopForm
from ..models import (
    ManualObservationStationLink,
    ManualObservationStationLinkVariableMapping,
    CollectorSubmission,
    SynopParameterMapping,
    SynopMessage,
)
from ..serializers import (
    OfficeSubmissionInSer,
    SynopDecodeInSer,
    SynopSubmitInSer,
)
from ..synop_utils import build_submission_records_from_synop, get_unmapped_elements
from ..wmo_codes import WMO_CODE_TABLES

_SYNOP_TPL = "adl_collector_app_plugin/office/synop.html"


class DecodeSynopView(APIView):
    """
    POST /api/adl-collector/synop/decode/
    Decode a raw FM12 SYNOP message and return the decoded values mapped to
    ADL parameters. Does NOT persist anything — preview only.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        ser = SynopDecodeInSer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)

        decoded = ser.validated_data["_decoded"]
        mappings = ser.validated_data["_mappings"]
        show_param_ids = ser.validated_data["_show_param_ids"]
        observation_time = ser.validated_data["_observation_time"]
        decoded_station_id = ser.validated_data["_decoded_station_id"]

        mapped_records = build_submission_records_from_synop(decoded, mappings)

        visible_records = [
            r for r in mapped_records
            if r["adl_parameter_id"] in show_param_ids
        ]

        response_data = {
            "decoded": decoded,
            "mapped_records": visible_records,
            "unmapped_count": len(mappings) - len(mapped_records),
            "station_id": decoded_station_id,
        }
        if observation_time is not None:
            response_data["observation_time"] = observation_time.isoformat()

        return Response(response_data)


class SubmitSynopView(APIView):
    """
    POST /api/adl-collector/synop/submit/
    Archive a SYNOP message and create a CollectorSubmission from decoded values.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        ser = SynopSubmitInSer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        
        synop_msg = ser.save()
        
        return Response(
            {
                "synop_message_id": synop_msg.id,
                "observation_time": synop_msg.observation_time,
                "submission_id": synop_msg.submission_id,
            },
            status=status.HTTP_201_CREATED,
        )


@method_decorator(staff_member_required, name="dispatch")
class OfficeEntryView(View):
    """
    GET  — render the office data entry form (station picker + variable mappings)
    POST — submit direct parameter values
    """
    page_title = _("Direct Data Entry")
    template_name = "adl_collector_app_plugin/office/entry.html"
    
    def _station_links_qs(self):
        return (
            ManualObservationStationLink.objects
            .filter(enabled=True)
            .select_related("station", "network_connection")
            .prefetch_related(
                Prefetch(
                    "variable_mappings",
                    queryset=ManualObservationStationLinkVariableMapping.objects
                    .filter(show_in_direct_entry=True)
                    .select_related("adl_parameter", "obs_parameter_unit"),
                )
            )
            .order_by("station__name")
        )
    
    def get(self, request):
        import json
        
        station_links = self._station_links_qs()
        
        selected_id = request.GET.get("station_link_id")
        selected_link = None
        if selected_id:
            try:
                selected_link = station_links.get(id=selected_id)
            except ManualObservationStationLink.DoesNotExist:
                pass
        
        # Pre-population from an existing submission (edit mode)
        pre_filled_values_json = "{}"
        pre_filled_obs_time = ""
        editing_submission_id = request.GET.get("submission_id")
        if editing_submission_id:
            try:
                editing_sub = (
                    CollectorSubmission.objects
                    .prefetch_related("records__variable_mapping")
                    .get(pk=editing_submission_id)
                )
                try:
                    selected_link = station_links.get(id=editing_sub.station_link_id)
                except ManualObservationStationLink.DoesNotExist:
                    editing_submission_id = None
                
                if editing_submission_id:
                    pre_filled_values_json = json.dumps(
                        {str(r.variable_mapping_id): r.value for r in editing_sub.records.all()}
                    )
                    pre_filled_obs_time = editing_sub.observation_time.strftime("%Y-%m-%dT%H:%M")
            except CollectorSubmission.DoesNotExist:
                editing_submission_id = None
        
        context = {
            "page_title": self.page_title,
            "station_links": station_links,
            "selected_link": selected_link,
            "wmo_code_tables": WMO_CODE_TABLES,
            "pre_filled_values_json": pre_filled_values_json,
            "observation_time": pre_filled_obs_time,
            "editing_submission_id": editing_submission_id,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        ser = OfficeSubmissionInSer(data=request.POST, context={"request": request})
        
        if not ser.is_valid():
            station_links = self._station_links_qs()
            selected_id = request.POST.get("station_link_id")
            selected_link = None
            if selected_id:
                try:
                    selected_link = station_links.get(id=selected_id)
                except ManualObservationStationLink.DoesNotExist:
                    pass
            return render(request, self.template_name, {
                "page_title": self.page_title,
                "station_links": station_links,
                "selected_link": selected_link,
                "errors": ser.errors,
                "wmo_code_tables": WMO_CODE_TABLES,
            })
        
        sub, was_duplicate = ser.save()
        return render(request, self.template_name, {
            "page_title": self.page_title,
            "station_links": self._station_links_qs(),
            "success": True,
            "duplicate": was_duplicate,
            "submission_id": sub.id,
            "wmo_code_tables": WMO_CODE_TABLES,
        })


@method_decorator(staff_member_required, name="dispatch")
class OfficeSynopView(View):
    """
    GET              — Step 1: render the SYNOP FM12 entry form
    POST action=decode — Step 2: decode-only preview (no DB writes)
    POST action=save   — save via SynopSubmitInSer (raw message carried in hidden fields)
    """
    
    def get(self, request):
        now = dj_timezone.now()
        initial = {"observation_year": now.year, "observation_month": now.month}
        
        editing_submission_id = request.GET.get("submission_id")
        if editing_submission_id:
            try:
                sub = CollectorSubmission.objects.get(pk=editing_submission_id)
                synop_msg = SynopMessage.objects.filter(submission=sub).first()
                if synop_msg:
                    initial.update({
                        "observation_year": sub.observation_time.year,
                        "observation_month": sub.observation_time.month,
                        "raw_message": synop_msg.raw_message,
                    })
                else:
                    editing_submission_id = None
            except CollectorSubmission.DoesNotExist:
                editing_submission_id = None
        
        form = SynopForm(initial=initial)
        ctx = {"page_title": "SYNOP FM12 Entry", "step": 1, "form": form}
        if editing_submission_id:
            ctx["editing_submission_id"] = editing_submission_id
        return render(request, _SYNOP_TPL, ctx)
    
    def post(self, request):
        form = SynopForm(request.POST)
        if not form.is_valid():
            return render(request, _SYNOP_TPL, {"page_title": "SYNOP FM12 Entry", "step": 1, "form": form})
        
        action = request.POST.get("action", "decode")
        if action == "decode":
            return self._decode_preview(request, form)
        return self._save(request, form)
    
    def _decode_preview(self, request, form):
        from ..synop_utils import decode_fm12
        
        raw = form.cleaned_data["raw_message"]
        year = form.cleaned_data["observation_year"]
        month = form.cleaned_data["observation_month"]
        
        try:
            decoded = decode_fm12(raw)
        except (ValueError, ImportError) as exc:
            form.add_error("raw_message", str(exc))
            return render(request, _SYNOP_TPL, {"page_title": "SYNOP FM12 Entry", "step": 1, "form": form})
        
        station_id = (decoded.get("station_id") or {}).get("value")
        station_link = None
        connection = None
        station_error = None
        mapped_records = []
        unmapped_elements = []
        observation_time = None
        
        if station_id is None:
            station_error = "No station ID found in this SYNOP message."
        else:
            try:
                station_link = ManualObservationStationLink.objects.select_related(
                    "station", "network_connection"
                ).get(station__wsi_local=station_id)
                connection = station_link.network_connection
                mappings = list(
                    SynopParameterMapping.objects.select_related("adl_parameter", "source_unit").all()
                )
                mapped_records = build_submission_records_from_synop(decoded, mappings)
                unmapped_elements = get_unmapped_elements(decoded, mappings)
                # Detect station-level gaps: globally mapped but no station-level
                # ManualObservationStationLinkVariableMapping for this station.
                # These would silently fail at save time — surface them now.
                station_param_ids = set(
                    station_link.variable_mappings.values_list("adl_parameter_id", flat=True)
                )
                importable = [r for r in mapped_records if r["adl_parameter_id"] in station_param_ids]
                gap = [r for r in mapped_records if r["adl_parameter_id"] not in station_param_ids]
                mapped_records = importable
                unmapped_elements = unmapped_elements + [
                    {"path": r["fm12_element_path"], "label": r["adl_parameter_name"], "value": r["value"]}
                    for r in gap
                ]
            except ManualObservationStationLink.DoesNotExist:
                station_error = f'No station link found for SYNOP station ID "{station_id}".'
        
        if not station_error:
            obs_time_info = decoded.get("obs_time") or {}
            day = (obs_time_info.get("day") or {}).get("value")
            hour = (obs_time_info.get("hour") or {}).get("value")
            if day is not None and hour is not None:
                try:
                    observation_time = datetime.datetime(
                        int(year), int(month), int(day), int(hour), 0, 0,
                        tzinfo=zoneinfo.ZoneInfo("UTC"),
                    )
                except ValueError:
                    pass
        
        context = {
            "page_title": "SYNOP FM12 Entry",
            "step": 2,
            "form": form,
            "station_id": station_id,
            "station_link": station_link,
            "connection": connection,
            "station_error": station_error,
            "mapped_records": mapped_records,
            "unmapped_elements": unmapped_elements,
            "observation_time": observation_time,
        }
        
        if unmapped_elements:
            wizard_url = reverse('synop_setup_wizard')
            paths = ''.join(f"&path={u.get('path')}" for u in unmapped_elements)
            context.update({
                "synop_wizard_url": f"{wizard_url}?connection={connection.pk}{paths}"
            })
        
        return render(request, _SYNOP_TPL, context)
    
    def _save(self, request, form):
        ser = SynopSubmitInSer(data=request.POST, context={"request": request})
        if not ser.is_valid():
            return render(request, _SYNOP_TPL, {
                "page_title": "SYNOP FM12 Entry",
                "step": 1,
                "form": form,
                "errors": ser.errors,
            })
        synop_msg = ser.save()
        now = dj_timezone.now()
        return render(request, _SYNOP_TPL, {
            "page_title": "SYNOP FM12 Entry",
            "step": 1,
            "success": True,
            "synop_message": synop_msg,
            "form": SynopForm(initial={
                "observation_year": synop_msg.observation_time.year if synop_msg.observation_time else now.year,
                "observation_month": synop_msg.observation_time.month if synop_msg.observation_time else now.month,
            }),
        })
