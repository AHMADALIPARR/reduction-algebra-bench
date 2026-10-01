<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Copyright (C) 2026 SnapKitty Collective -->
# RUNLOG — exp04 (SaC track)

Date: 2026-10-01. All times PDT. sac2c = the Single Assignment C compiler.

## Toolchain attempts (all failed or incomplete; nothing executed)

1. `which sac2c` / `apt-get install -y sac2c` → **"Unable to locate package
   sac2c"**. No sac2c package in the configured apt sources; `apt-cache
   search sac2c` returns nothing.
2. sac-home.org download page → the site redirects (`/index`); no usable
   compiler download found there.
3. github.com/SacBase/sac2c (releases + API) → **404**. The GitHub
   organization/repo no longer exists at that path.
4. Source build from gitlab.sac-home.org/Lucas/sac2c (found via web search;
   the sac2c sources moved to GitLab):
   - `git clone --depth 1` → OK (1711 files).
   - `git submodule update --init --recursive` → OK.
   - Installed build deps via apt: `bison`, `flex`, `xsltproc`
     (cmake/gcc/make already present).
   - `cmake -DCMAKE_BUILD_TYPE=RELEASE -DCUDA=OFF ..` → failed twice, then
     succeeded after: (a) installing `xsltproc` ("Cannot find a suitable
     xslt processor"), (b) tagging the shallow clone `v1.3.3-local` so
     `git describe --tags` yields `SAC2C_VERSION`.
   - `make -j2` → reached ~24% (copying test files) and then the VM was
     restarted; `/tmp` (where the source tree lived) was wiped. Build did
     not complete. Not re-attempted: the per-language install time-box is
     long exceeded and the Remora track (which has a working toolchain)
     takes priority for executed results.

## Result

`sac2c` is **not installed** in this environment. `exp04_sac.sac` has not
been compiled or executed. Per the brief's runtime rule, the implementation
is complete, `results/exp04_sac.json` carries nulls with provenance
`unknown`, and no numbers are claimed.

## To reproduce (on a machine with sac2c)

```sh
sac2c -o exp04_sac exp04_sac.sac
./exp04_sac
# verify-before-record: crosslang_checksum must equal 1388262917130611548
# (substrate/splitmix64.py); a mismatch fails the gate -> no results.
```
