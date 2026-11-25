# Sample run verification

**Date:** 2026-11-25  
**Input:** Fictional demo resume and sample role included with the app. No personal resume data is included in this record.

The local browser flow accepted the demo resume and job description and rendered a complete analysis. The sample role is a junior data analyst position. The report showed **36% weighted skill coverage**, with **3 of 9 required** and **2 of 4 preferred** skills matched. It listed eight gaps, resume/job evidence snippets, suggested practice tasks, and learning links.

The score is a transparent vocabulary-based coverage estimate, not an ATS simulation or hiring prediction. Skill phrasing and context can affect results. Uploaded files are processed in memory and are not saved by the application.

## Verification

- Python analyzer unit tests: 6 passed.
- Production build: passed.
- Sites worker tests: 4 passed.
- Browser flow: sample upload, report details, clear/reset, and mobile layout checked.
