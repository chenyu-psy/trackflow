# Behavior Recovery

Recovery helpers manage the meta-JSON state used to resume planned rows by
accepted `plan_id` values.

::: trackflow.beh.recovery
    options:
      members:
        - make_meta_state
        - save_meta_state
        - load_meta_state
        - mark_plan_completed
        - remaining_plan_rows
        - prepare_meta_state
