# Mid-iteration report evidence, 20 October 2026

`verification_20261020.json` contains the 15 retained in-scope local HTTP assertions and the corrected-scope unit-test result. One assertion checks the absent PDF report route; this is not a passed feature test. The original broader execution records are retained outside the report in the ignored local execution directory.

The role, engagement, identity and tracker suites were rerun for the corrected scope: **24 passed in 2.66 seconds**. Run from the repository root with the virtual environment, `PYTHONPATH` set to the backend directory and `TEMP` / `TMP` set to a writable local test directory:

```powershell
.venv/Scripts/python.exe -m pytest backend/interaction/test_engagement.py backend/interaction/test_cust_emp_classifier.py backend/interaction/test_role_classifier.py backend/interaction/test_identity.py backend/interaction/test_tracker.py -q
```

`unit_tests_20261020.txt` records that rerun. `source_audit_20261020.json` records source-reference checks and confirmed LaTeX compilation.

Representative UI screenshots show demonstration data rather than measured vision accuracy. Role navigation remains partial. The earlier development server exhausted a 768 MB Node heap and was restarted at 2048 MB. Authentication checks used isolated local databases; credentials, cookies, databases and raw video are excluded from this folder.

Historical floor-distance results refer to commit `4a9023a`, before source removal in `8c3a6fe`. The inspected code snapshot was `feature/interaction`, HEAD `52f651e`. This report update changes documentation only.
