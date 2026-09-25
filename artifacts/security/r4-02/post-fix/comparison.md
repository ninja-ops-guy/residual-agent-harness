# R4-02 pre/post comparison

The demonstrated archive defect is fixed in the tested scope. Full deterministic qualification is BLOCKED on this host by existing M4 namespace mount failures; the retained gate envelope is FAIL. R4-03 must not begin.

Pre-fix: 2 outside-authority creations. Post-fix: 0 outside writes and 0 newly created outside authorities in 42 real cases.

The unsafe controls continue to escape. Both pre-fix TAR.ZST regressions fail on frozen source and pass on remediated source. Both semantic mutants are killed.

Gemma: **SUBAGENT_RESULT: INCOMPLETE**. Finding: **Astra direct audit**.

Historical protection labels in the byte-identical audit harness are superseded by the attribution below: TAR and TAR.ZST now use RESIDUAL explicit member/link checks plus the Python data filter, and all formats use disposable staging and post-validation.

| Format | Case | Pre-fix | Post-fix |
|---|---|---|---|
| tar | benign | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED |
| tar | parent | BLOCKED | BLOCKED |
| tar | absolute | ALLOWED_BUT_CONFINED | BLOCKED |
| tar | nested | BLOCKED | BLOCKED |
| tar | dot | BLOCKED | BLOCKED |
| tar | backslash | ALLOWED_BUT_CONFINED | BLOCKED |
| tar | mixed | ALLOWED_BUT_CONFINED | BLOCKED |
| tar | drive | ALLOWED_BUT_CONFINED | BLOCKED |
| tar | symlink_alone | BLOCKED | BLOCKED |
| tar | symlink_then_file | BLOCKED | BLOCKED |
| tar | hardlink_absolute | BLOCKED | BLOCKED |
| tar | hardlink_relative | BLOCKED | BLOCKED |
| tar | hardlink_then_overwrite | BLOCKED | BLOCKED |
| tar | existing_symlink | BLOCKED | BLOCKED |
| tar | duplicate | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED |
| zip | benign | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED |
| zip | parent | BLOCKED | BLOCKED |
| zip | absolute | BLOCKED | BLOCKED |
| zip | nested | BLOCKED | BLOCKED |
| zip | dot | BLOCKED | BLOCKED |
| zip | backslash | ALLOWED_BUT_CONFINED | BLOCKED |
| zip | mixed | ALLOWED_BUT_CONFINED | BLOCKED |
| zip | drive | ALLOWED_BUT_CONFINED | BLOCKED |
| zip | symlink_alone | ALLOWED_BUT_CONFINED | BLOCKED |
| zip | symlink_then_file | BLOCKED | BLOCKED |
| zip | hardlink_absolute | UNSUPPORTED_FIXTURE | UNSUPPORTED_FIXTURE |
| zip | hardlink_relative | UNSUPPORTED_FIXTURE | UNSUPPORTED_FIXTURE |
| zip | hardlink_then_overwrite | UNSUPPORTED_FIXTURE | UNSUPPORTED_FIXTURE |
| zip | existing_symlink | BLOCKED | BLOCKED |
| zip | duplicate | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED |
| tar.zst | benign | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED |
| tar.zst | parent | BLOCKED | BLOCKED |
| tar.zst | absolute | ALLOWED_BUT_CONFINED | BLOCKED |
| tar.zst | nested | BLOCKED | BLOCKED |
| tar.zst | dot | BLOCKED | BLOCKED |
| tar.zst | backslash | ALLOWED_BUT_CONFINED | BLOCKED |
| tar.zst | mixed | ALLOWED_BUT_CONFINED | BLOCKED |
| tar.zst | drive | ALLOWED_BUT_CONFINED | BLOCKED |
| tar.zst | symlink_alone | OUTSIDE_AUTHORITY_CREATED | BLOCKED |
| tar.zst | symlink_then_file | OUTSIDE_AUTHORITY_CREATED | BLOCKED |
| tar.zst | hardlink_absolute | BLOCKED | BLOCKED |
| tar.zst | hardlink_relative | BLOCKED | BLOCKED |
| tar.zst | hardlink_then_overwrite | BLOCKED | BLOCKED |
| tar.zst | existing_symlink | BLOCKED | BLOCKED |
| tar.zst | duplicate | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED |
