from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.messages import success as msg_success
from django.db import transaction
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from ..models import (
    ManualObservationStationLink,
    ManualObservationStationLinkVariableMapping,
    ManualObservationConnection,
    SynopParameterMapping,
)

SYNOP_WIZARD_SESSION_KEY = "synop_setup_wizard"


@method_decorator(staff_member_required, name="dispatch")
class SynopSetupWizardView(View):
    """
    4-step wizard to configure SynopParameterMapping (global) and
    ManualObservationStationLinkVariableMapping (station-level) for FM12 SYNOP ingestion.

    Step 1 — Select connection (auto-skipped when launched with ?connection=<id>)
    Step 2 — Review FM12 parameters; accept/change/create new/skip each
    Step 3 — Create new DataParameters for paths marked "create_new" (optional)
    Step 4 — Review all proposed mappings and confirm / save
    """

    TPLS = "adl_collector_app_plugin/office/synop_wizard/{}.html"

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _state(self, request):
        return request.session.get(SYNOP_WIZARD_SESSION_KEY, {})

    def _save_state(self, request, state):
        request.session[SYNOP_WIZARD_SESSION_KEY] = state
        request.session.modified = True

    def _clear_state(self, request):
        request.session.pop(SYNOP_WIZARD_SESSION_KEY, None)

    @staticmethod
    def _field_key(path):
        """Convert 'air_temperature.value' → 'air_temperature_value' for use in form field names."""
        return path.replace(".", "_")

    # ------------------------------------------------------------------
    # dispatch
    # ------------------------------------------------------------------

    def get(self, request):
        step = int(request.GET.get("step", 1))
        state = self._state(request)

        if step == 1 and "connection" in request.GET:
            try:
                conn = ManualObservationConnection.objects.get(pk=request.GET["connection"])
                state["connection_id"] = conn.pk
                self._save_state(request, state)
                return redirect(reverse("synop_setup_wizard") + "?step=2")
            except ManualObservationConnection.DoesNotExist:
                pass

        if step == 1:
            return self._step1_get(request, state)
        if step == 2:
            if "connection_id" not in state:
                return redirect(reverse("synop_setup_wizard") + "?step=1")
            return self._step2_get(request, state)
        if step == 3:
            if "mappings" not in state:
                return redirect(reverse("synop_setup_wizard") + "?step=2")
            return self._step3_get(request, state)
        if step == 4:
            if "mappings" not in state:
                return redirect(reverse("synop_setup_wizard") + "?step=2")
            return self._step4_get(request, state)
        return redirect(reverse("synop_setup_wizard") + "?step=1")

    def post(self, request):
        step = int(request.POST.get("step", 1))
        state = self._state(request)
        if step == 1:
            return self._step1_post(request, state)
        if step == 2:
            return self._step2_post(request, state)
        if step == 3:
            return self._step3_post(request, state)
        if step == 4:
            return self._step4_post(request, state)
        return redirect(reverse("synop_setup_wizard") + "?step=1")

    # ------------------------------------------------------------------
    # Step 1 — select connection
    # ------------------------------------------------------------------

    def _step1_get(self, request, state):
        from ..synop_wizard_data import count_mapped_common, SYNOP_COMMON_PARAMETERS
        connections = list(ManualObservationConnection.objects.all())
        global_mapped = count_mapped_common()
        global_incomplete = len(SYNOP_COMMON_PARAMETERS) - global_mapped
        conn_info = [{"connection": c} for c in connections]
        if len(conn_info) == 1:
            state["connection_id"] = conn_info[0]["connection"].pk
            self._save_state(request, state)
            return redirect(reverse("synop_setup_wizard") + "?step=2")
        return render(request, self.TPLS.format("step_connection"), {
            "page_title": "SYNOP Setup Wizard",
            "step": 1,
            "conn_info": conn_info,
            "global_incomplete": global_incomplete,
            "saved": request.GET.get("saved") == "1",
        })

    def _step1_post(self, request, state):
        conn_id = request.POST.get("connection_id")
        try:
            ManualObservationConnection.objects.get(pk=conn_id)
        except (ManualObservationConnection.DoesNotExist, ValueError):
            return self._step1_get(request, state)
        state["connection_id"] = int(conn_id)
        self._save_state(request, state)
        return redirect(reverse("synop_setup_wizard") + "?step=2")

    # ------------------------------------------------------------------
    # Step 2 — review & map parameters
    # ------------------------------------------------------------------

    def _step2_get(self, request, state, errors=None):
        from adl.core.models import DataParameter, Unit
        from ..synop_wizard_data import (
            SYNOP_COMMON_PARAMETERS, SYNOP_EXTENDED_PARAMETERS,
            suggest_adl_parameter, get_or_suggest_unit,
        )

        conn = ManualObservationConnection.objects.get(pk=state["connection_id"])
        show_all = request.GET.get("show_all") == "1" or state.get("show_all", False)
        parameters = SYNOP_COMMON_PARAMETERS + (SYNOP_EXTENDED_PARAMETERS if show_all else [])

        existing = {
            m.fm12_element_path: m
            for m in SynopParameterMapping.objects.select_related("adl_parameter", "source_unit").all()
        }

        param_rows = []
        for meta in parameters:
            path = meta["path"]
            fk = self._field_key(path)
            existing_mapping = existing.get(path)
            if existing_mapping:
                param_rows.append({"meta": meta, "field_key": fk, "status": "mapped", "existing": existing_mapping})
            else:
                param_rows.append({
                    "meta": meta,
                    "field_key": fk,
                    "status": "unmapped",
                    "existing": None,
                    "suggested_parameter": suggest_adl_parameter(meta),
                    "suggested_unit": get_or_suggest_unit(meta["suggested_unit_symbol"]) if meta.get(
                        "suggested_unit_symbol") else None,
                })

        return render(request, self.TPLS.format("step_parameters"), {
            "page_title": "SYNOP Setup Wizard",
            "step": 2,
            "connection": conn,
            "param_rows": param_rows,
            "show_all": show_all,
            "all_parameters": DataParameter.objects.select_related("unit").order_by("name"),
            "all_units": Unit.objects.order_by("name"),
            "common_count": len(SYNOP_COMMON_PARAMETERS),
            "extended_count": len(SYNOP_EXTENDED_PARAMETERS),
            "errors": errors or [],
        })

    def _step2_post(self, request, state):
        from ..synop_wizard_data import SYNOP_COMMON_PARAMETERS, SYNOP_EXTENDED_PARAMETERS

        show_all = request.POST.get("show_all") == "1"
        parameters = SYNOP_COMMON_PARAMETERS + (SYNOP_EXTENDED_PARAMETERS if show_all else [])

        mappings = []
        errors = []
        for meta in parameters:
            path = meta["path"]
            fk = self._field_key(path)
            action = request.POST.get(f"action_{fk}", "skip")

            if action == "skip":
                continue
            if action == "use_existing":
                adl_pid = request.POST.get(f"adl_parameter_{fk}")
                unit_id = request.POST.get(f"unit_{fk}")
                if not adl_pid or not unit_id:
                    errors.append(f"""Please select a DataParameter and Unit for "{meta['label']}" or choose Skip.""")
                    continue
                mappings.append({
                    "path": path,
                    "label": meta["label"],
                    "action": "use_existing",
                    "adl_parameter_id": int(adl_pid),
                    "unit_id": int(unit_id),
                    "show_in_direct_entry": request.POST.get(f"show_direct_{fk}") == "on",
                    "is_coded": meta.get("is_coded", False),
                })
            elif action == "create_new":
                mappings.append({
                    "path": path,
                    "label": meta["label"],
                    "action": "create_new",
                    "adl_parameter_id": None,
                    "unit_id": None,
                    "show_in_direct_entry": request.POST.get(f"show_direct_{fk}") == "on",
                    "is_coded": meta.get("is_coded", False),
                    "suggested_unit_symbol": meta.get("suggested_unit_symbol", ""),
                    "wmo_code_table": meta.get("wmo_code_table", ""),
                    "adl_category": meta.get("adl_category", "meteorological"),
                })

        if errors:
            state["show_all"] = show_all
            self._save_state(request, state)
            return self._step2_get(request, state, errors=errors)

        state["mappings"] = mappings
        state["show_all"] = show_all
        self._save_state(request, state)

        has_new = any(m["action"] == "create_new" for m in mappings)
        return redirect(reverse("synop_setup_wizard") + f"?step={'3' if has_new else '4'}")

    # ------------------------------------------------------------------
    # Step 3 — create missing DataParameters
    # ------------------------------------------------------------------

    def _step3_get(self, request, state, errors=None):
        from adl.core.models import Unit, DataParameter
        new_mappings = [
            {**m, "field_key": self._field_key(m["path"])}
            for m in state.get("mappings", [])
            if m["action"] == "create_new"
        ]
        return render(request, self.TPLS.format("step_new_params"), {
            "page_title": "SYNOP Setup Wizard",
            "step": 3,
            "new_mappings": new_mappings,
            "all_units": Unit.objects.order_by("name"),
            "category_choices": DataParameter._meta.get_field("category").choices,
            "errors": errors or [],
        })

    def _step3_post(self, request, state):
        from adl.core.models import DataParameter, Unit

        mappings = state.get("mappings", [])
        errors = []

        for mapping in mappings:
            if mapping["action"] != "create_new":
                continue
            fk = self._field_key(mapping["path"])
            param_name = request.POST.get(f"new_name_{fk}", "").strip()
            unit_symbol = request.POST.get(f"new_unit_symbol_{fk}", "").strip()
            is_coded = request.POST.get(f"new_is_coded_{fk}") == "on"
            wmo_code_table = request.POST.get(f"new_wmo_code_table_{fk}", "").strip()
            category = request.POST.get(f"new_category_{fk}", "meteorological")
            show_direct = request.POST.get(f"show_direct_{fk}") == "on"

            if not param_name:
                errors.append(f'Name is required for "{mapping["label"]}".')
                continue

            if is_coded:
                unit, _ = Unit.objects.get_or_create(symbol="1", defaults={"name": "dimensionless"})
            else:
                if not unit_symbol:
                    errors.append(f'Unit symbol is required for "{mapping["label"]}".')
                    continue
                unit = Unit.objects.filter(symbol=unit_symbol).first()
                if not unit:
                    errors.append(
                        f'Unit symbol "{unit_symbol}" for "{mapping["label"]}" was not found. '
                        f'Create the Unit first, then return to the wizard.'
                    )
                    continue

            param, _ = DataParameter.objects.get_or_create(
                name=param_name,
                defaults={
                    "unit": unit,
                    "is_coded": is_coded,
                    "wmo_code_table": wmo_code_table if is_coded else "",
                    "category": category,
                },
            )
            mapping["adl_parameter_id"] = param.id
            mapping["unit_id"] = unit.id
            mapping["show_in_direct_entry"] = show_direct
            mapping["action"] = "use_existing"

        if errors:
            self._save_state(request, state)
            return self._step3_get(request, state, errors=errors)

        state["mappings"] = mappings
        self._save_state(request, state)
        return redirect(reverse("synop_setup_wizard") + "?step=4")

    # ------------------------------------------------------------------
    # Step 4 — review & confirm
    # ------------------------------------------------------------------

    def _step4_get(self, request, state):
        from adl.core.models import DataParameter, Unit

        conn = ManualObservationConnection.objects.get(pk=state["connection_id"])
        stations = ManualObservationStationLink.objects.filter(
            network_connection=conn, enabled=True
        ).select_related("station")

        enriched = []
        for m in state.get("mappings", []):
            if m["action"] != "use_existing" or not m.get("adl_parameter_id") or not m.get("unit_id"):
                continue
            try:
                param = DataParameter.objects.get(pk=m["adl_parameter_id"])
                unit = Unit.objects.get(pk=m["unit_id"])
            except (DataParameter.DoesNotExist, Unit.DoesNotExist):
                continue
            enriched.append({**m, "adl_parameter_name": param.name, "unit_name": unit.name})

        return render(request, self.TPLS.format("step_confirm"), {
            "page_title": "SYNOP Setup Wizard",
            "step": 4,
            "connection": conn,
            "enriched_mappings": enriched,
            "stations": stations,
            "station_count": stations.count(),
        })

    def _step4_post(self, request, state):
        from adl.core.models import DataParameter, Unit

        conn = ManualObservationConnection.objects.get(pk=state["connection_id"])
        stations = list(ManualObservationStationLink.objects.filter(
            network_connection=conn, enabled=True
        ))

        mappings = state.get("mappings", [])

        proposed = [
            m for m in mappings
            if m.get("action") == "use_existing"
               and m.get("adl_parameter_id")
               and m.get("unit_id")
        ]

        param_to_paths: dict = {}
        for m in proposed:
            param_to_paths.setdefault(m["adl_parameter_id"], []).append(m["path"])

        proposed_paths = {m["path"] for m in proposed}
        existing_param_to_path = {
            spm.adl_parameter_id: spm.fm12_element_path
            for spm in SynopParameterMapping.objects.exclude(fm12_element_path__in=proposed_paths)
        }

        duplicate_errors = []
        for param_id, paths in param_to_paths.items():
            if len(paths) > 1:
                duplicate_errors.append(
                    f"The same ADL parameter (id={param_id}) is assigned to multiple FM12 paths in this wizard: "
                    + ", ".join(paths)
                    + ". Each ADL parameter must map to exactly one FM12 path."
                )
            elif param_id in existing_param_to_path:
                duplicate_errors.append(
                    f"ADL parameter (id={param_id}) is already mapped to FM12 path "
                    f"'{existing_param_to_path[param_id]}'. "
                    "Remove or re-assign that mapping before adding another."
                )

        if duplicate_errors:
            return self._step2_get(request, state, errors=duplicate_errors)

        created_synop = 0
        created_station = 0

        with transaction.atomic():
            for m in mappings:
                if m["action"] != "use_existing" or not m.get("adl_parameter_id") or not m.get("unit_id"):
                    continue

                param = DataParameter.objects.get(pk=m["adl_parameter_id"])
                unit = Unit.objects.get(pk=m["unit_id"])

                _, synop_created = SynopParameterMapping.objects.get_or_create(
                    fm12_element_path=m["path"],
                    defaults={"adl_parameter": param, "source_unit": unit},
                )
                if synop_created:
                    created_synop += 1

                show_direct = m.get("show_in_direct_entry", not m.get("is_coded", False))
                for sl in stations:
                    if not sl.variable_mappings.filter(adl_parameter=param).exists():
                        ManualObservationStationLinkVariableMapping.objects.create(
                            station_link=sl,
                            adl_parameter=param,
                            obs_parameter_unit=unit,
                            show_in_direct_entry=show_direct,
                        )
                        created_station += 1

        self._clear_state(request)
        msg_success(
            request,
            f"Saved {created_synop} SYNOP mapping(s) and {created_station} station variable mapping(s) "
            f"for {conn.name}.",
        )
        return redirect(reverse("synop_setup_wizard") + "?step=1&saved=1")
