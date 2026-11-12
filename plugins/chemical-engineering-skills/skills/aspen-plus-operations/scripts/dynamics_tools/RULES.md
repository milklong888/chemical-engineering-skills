# Offline facade rules and scope

1. `verify_package_manifest` delegates listed-file byte checks to toolpack. It
   does not prove a complete dependency inventory or package portability.
2. `check_csv_grid` delegates the caller's explicit grid checks. Time units and
   tolerance belong to the supplied CSV comparison, never a solver setting.
3. `inspect_history` imports the identity-checked existing public owner. A clean
   text result does not prove its run identity, live Control Panel, products,
   tolerance lock, current version, or exact-file reopen.
4. `list_external_tools` and `plan_external_invocation` inspect paths and print
   plans only. No external service, process or COM object is started.
5. The MCP facade is transport around these same functions, not a native
   Dynamics interface, simulator, engineering solver, or second evidence parser.
6. `status=ok` means a structured diagnostic was produced, including
   `matches=false`. Read each result's `scope` and `matches`; engineering and
   native-calculation acceptance remain `not_assessed`.
7. User-provided paths are local read capabilities. Run the server only for a
   trusted local client and select intended files. It performs no telemetry,
   automatic client registration, configuration mutation, or network transport.
8. Synthetic examples and tests are not case defaults, native success evidence,
   source authenticity proof or experience-inbox admission.
