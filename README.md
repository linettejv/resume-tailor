# Resume Tailor

Paste a job description from LinkedIn, Wellfound or InstaHire. A Claude agent checks how well you fit, lists the gaps, and rewrites your resume for that job, **using only facts from your own fact bank**. Every bullet has to cite the facts it comes from, and code (not the model) checks this before anything is accepted.

```
 React UI ──► Flask /api/tailor ──► agent loop ──► Claude API
                                       │  ▲
                          tool calls   ▼  │  tool results (or errors)
                         get_profile · check_bullets · submit_tailored_resume
                                       │
                                       ▼
                        validated submission ──► .tex (+ PDF) download
```


