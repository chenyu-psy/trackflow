# Behavior Preflight

Preflight checks are explicit and opt-in. They only check the runtime pieces
enabled for the current experiment session.

::: trackflow.beh.preflight
    options:
      members:
        - PreflightResult
        - check_preflight
        - preflight_or_raise
