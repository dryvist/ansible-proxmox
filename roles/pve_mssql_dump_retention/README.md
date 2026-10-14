# pve_mssql_dump_retention

Archives old SQL Server dump directories as `.tar.zst` files, verifies each
archive against its live source, then removes only that source directory. The
role selects direct child directories matching the SQL Server dump name
pattern, always leaves the newest ones on the volume, and takes the oldest of
the rest that are older than the age limit, at most one bounded batch per
converge.

The archive directory's parent must already exist as a mounted ZFS dataset
whose device belongs to `bulk`. The role creates the archive directory as
`root:root` mode `0700` only after validating that mount. A dry run reports
candidate names and apparent regular-file bytes without creating or deleting
anything.

For a new archive, the role writes a `.partial` file, tests the Zstandard
stream, compares the tar members against the live directory, and checks the
member count before moving the archive into place. A pre-existing final
archive is verified in place. Any failed check stops before source deletion;
an invalid existing archive is left untouched. The reported byte total is the
sum of apparent regular-file sizes in source directories removed during the
run.

## Variables

| Variable | Default | Description |
| --- | --- | --- |
| `pve_mssql_dump_retention_enabled` | `false` | Enables the role on a host. |
| `pve_mssql_dump_retention_dry_run` | `true` | Reports candidates without archive or deletion. |
| `pve_mssql_dump_retention_source_dir` | `""` | Directory containing dump directories. |
| `pve_mssql_dump_retention_archive_dir` | `""` | Directory on the mounted bulk ZFS dataset. |
| `pve_mssql_dump_retention_age_days` | `30` | Minimum directory mtime age in days. |
| `pve_mssql_dump_retention_keep_newest` | `5` | Newest matching directories always left on the volume. |
| `pve_mssql_dump_retention_max_dirs_per_run` | `40` | Maximum directories processed per converge. |

## Usage

Enable the role only on a host with the source directory and mounted bulk
archive dataset. Set both directories explicitly. Run the normal converge or
scope it with `--tags pve_mssql_dump_retention`.
