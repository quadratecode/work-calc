# About

A [PyWebIO](https://github.com/pywebio/PyWebIO) project to check the temporal validity of your termination and to calculate any possible embargo and notice periods under Swiss law. The hosted version is [available here](https://www.llq.ch/tools/termination-calc). Currently undergoing beta testing.

# Features

## Implemented

- [x] Permanent full-time employment (100 %)
- [x] Incapacities due to illness or accident
- [x] The probation period duration incl. a possible extension considering legally mandated holidays
- [x] The validity of a termination with regards to the embargo period
- [x] The embargo period duration
- [x] The notice period duration incl. a possible extension
- [x] Leap years are respected
- [x] Changes in seniority during an incapacity are respected

## Planned

- [ ] Certain inputs optional, e.g. only check probation period without incapacity
- [ ] Temporary Employment
- [ ] Different incapacities to work (military service or similar, pregnancy or participation in overseas aid projects) and combinations thereof
- [ ] A single incapacity with gaps
- [ ] Multiple incapacities, with or without gaps

# Contribute

- If your input returns an error or incorrect results, please open an [issue](https://github.com/quadratecode/ch-termination-calc/issues) containing your input data
- For questions and feature requests, please use [GitHub discussions](https://github.com/quadratecode/ch-termination-calc/discussions)
- PRs are welcomed. Since this project is licensed under the EUPL (v1.2 only, with specific provisions), your contributions must be under a compatible license. By contributing code or other assets to the project, you confirm that you hold the necessary rights for these contributions.
