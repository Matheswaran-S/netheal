# 5-minute demo script
1. `streamlit run app.py`. Point out the status pill (READY) and sidebar.
2. **Network Topology** tab: healthy network, green primary route, dashed blue backup (both computed by the engine).
3. Press **RUN SIMULATION** with no failures: baseline KPIs (~97% delivery at 1% loss per link).
4. **Failure & Recovery** tab: Link B-D, fail at 10 s, **INJECT FAILURE**, then **RUN SIMULATION**.
5. Show the recovery sequence table: FAILURE -> ROUTE_INVALIDATED -> RECOVERY_SEARCH -> ROUTE_CHANGED (25 ms later).
6. **Network Topology** tab: before/after figures; open the Packet inspector on a rerouted packet.
7. **Performance Analysis**: without vs with recovery table and charts; the timeline shows delivery collapsing without recovery.
8. Load scenario "6. No alternate path" and run: the PARTITIONED status and NO_ROUTE drops (graceful failure).
9. Export CSVs. Close: failures are scheduled events; both runs share seed and failures, so the difference is the self-healing.
