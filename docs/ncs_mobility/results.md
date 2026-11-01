# Mobility verification results

Fifteen native worlds complete 181,440 updates, using populations 128 and 1,000, a 300×300 grid and 40 periods. Source positions, memory and visit data match the declared reference checks. Build and runtime information identify the Windows MSVC/PPL implementation. The tables below retain individual conditions and verification counts.

## Configuration and execution

| Population | memory | rho0 | Seeds | Mean final occupied locations | Mean final toroidal radius | Mean concentration |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 128 | False | 1e-12 | 3 | 3.33 | 1.230 | 0.31632 |
| 128 | False | 10 | 3 | 128.00 | 93.672 | 0.00781 |
| 128 | True | 1e-12 | 3 | 32.00 | 3.700 | 0.05216 |
| 128 | True | 10 | 3 | 114.00 | 26.579 | 0.01038 |
| 1000 | True | 1e-12 | 3 | 66.67 | 2.592 | 0.02404 |

## Sources and records

- [Detailed results (JSON)](results.json)
- [Result table (CSV)](results.csv)
- [Mobility source-kernel adapter](README.md)
