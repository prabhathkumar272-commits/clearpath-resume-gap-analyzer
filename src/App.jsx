import { useRef, useState } from "react";

const MAX_BYTES = 10 * 1024 * 1024;
const ACCEPTED = [".pdf", ".docx", ".txt"];
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const ANALYZE_ENDPOINT = `${API_BASE_URL}/api/analyze`;
const SAMPLE_JOB = `Backend Software Developer Intern\nWe are looking for an intern to help build and maintain backend services and product features. The role involves implementing REST APIs, working with databases, supporting deployment workflows, and collaborating with engineers to deliver reliable software.\nCore skills: Python, JavaScript, TypeScript, SQL, REST APIs, Git, Docker, MongoDB, CI/CD.\nPreferred skills: FastAPI, AWS, Pandas, and clear communication.`;

function formatSize(bytes) {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function ScoreMeter({ score, requiredCount, requiredTotal, preferredCount, preferredTotal }) {
  const shownScore = Number.isFinite(score) ? `${score}%` : "—";
  return (
    <section className="score-card" aria-label={Number.isFinite(score) ? `Match score ${score} percent` : "No score available"}>
      <div className="score-card__top"><span className="eyebrow">ROLE ALIGNMENT</span><span className="score-card__mark">CLEARPATH</span></div>
      <div className="score-card__value">{shownScore}</div>
      <p>Weighted skill coverage</p>
      {Number.isFinite(score) && <progress value={score} max="100" aria-label="Weighted skill coverage" />}
      <div className="score-card__counts"><span><strong>{requiredCount}/{requiredTotal}</strong> required met</span><span><strong>{preferredCount}/{preferredTotal}</strong> preferred met</span></div>
    </section>
  );
}

function Evidence({ item, matched }) {
  return (
    <details className="evidence">
      <summary>{matched ? "View match evidence" : "View requirement evidence"}</summary>
      <div className="evidence__body">
        <div><span className="evidence__label">Job description</span><p>“{item.job_evidence}”</p></div>
        {matched ? (
          <div><span className="evidence__label">Resume evidence</span><p>“{item.resume_evidence}”</p></div>
        ) : (
          <div><span className="evidence__label">Resume evidence</span><p>No matching phrase was found in the extracted resume text.</p></div>
        )}
      </div>
    </details>
  );
}

function SkillList({ title, items, tone }) {
  return (
    <section className={`skill-list skill-list--${tone}`}>
      <div className="skill-list__heading"><span className="status-dot" aria-hidden="true" />{title}<span className="skill-count">{items.length}</span></div>
      {items.length ? (
        <ul>
          {items.map((item) => (
            <li key={item.name}>
              <div className="skill-row">
                <div><strong>{item.name}</strong><small>{item.category}</small></div>
                <span className={`priority-tag priority-tag--${item.priority}`}>{item.priority}</span>
              </div>
              {item.match_type === "related" && <p className="related-note">Related wording found · review this possible match</p>}
              <Evidence item={item} matched={Boolean(item.match_type)} />
            </li>
          ))}
        </ul>
      ) : (
        <p className="empty-copy">{tone === "matched" ? "No direct or related skill evidence found yet." : "Every recognized requirement has evidence in the resume."}</p>
      )}
    </section>
  );
}

function downloadReport(result, filename) {
  const lines = [
    "# Clearpath match report",
    "",
    `Resume: ${filename}`,
    `Weighted skill coverage: ${Number.isFinite(result.match_score) ? `${result.match_score}%` : "Not available"}`,
    "",
    result.summary,
    "",
    "## Skills with evidence",
    ...(result.matched_skills.length ? result.matched_skills.map((skill) => `- ${skill.name} (${skill.priority}; ${skill.match_type})\n  - Job: ${skill.job_evidence}\n  - Resume: ${skill.resume_evidence}`) : ["- No recognized skills matched."]),
    "",
    "## Skills to strengthen",
    ...(result.missing_skills.length ? result.missing_skills.map((skill) => `- ${skill.name} (${skill.priority})\n  - Job: ${skill.job_evidence}`) : ["- No recognized skill gaps found."]),
    "",
    "## Score method",
    result.score_explanation,
    "This is a resume guidance tool, not an employer or ATS decision.",
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "clearpath-match-report.md";
  anchor.click();
  URL.revokeObjectURL(url);
}

function Results({ result, filename, onReset }) {
  const requiredMatched = result.matched_skills.filter((item) => item.priority === "required").length;
  const preferredMatched = result.matched_skills.filter((item) => item.priority === "preferred").length;
  return (
    <main className="results-wrap">
      <div className="results-actions"><button className="back-link" onClick={onReset}>Start a new analysis</button><button className="export-button" onClick={() => downloadReport(result, filename)}>Download report</button></div>
      <div className="results-heading">
        <div><p className="eyebrow">YOUR ROLE MATCH REPORT</p><h1>A clearer path <em>forward.</em></h1><p className="results-subtitle">Skill evidence for <strong>{filename}</strong></p></div>
        <ScoreMeter score={result.match_score} requiredCount={requiredMatched} requiredTotal={result.required_count} preferredCount={preferredMatched} preferredTotal={result.preferred_count} />
      </div>
      <div className="score-explainer"><strong>How this score works</strong><p>{result.score_explanation}</p><span>{result.detected_skill_count} recognized skills · {result.required_count} required · {result.preferred_count} preferred</span></div>
      <div className="results-grid">
        <div className="results-main">
          <div className="insight-bar"><p>{result.summary}</p></div>
          <div className="skills-grid">
            <SkillList title="Skills with resume evidence" items={result.matched_skills} tone="matched" />
            <SkillList title="Skills to strengthen" items={result.missing_skills} tone="missing" />
          </div>
          {result.resume_highlights?.length > 0 && (
            <section className="highlights"><p className="eyebrow">OTHER SKILLS ALREADY IN YOUR CORNER</p><ul>{result.resume_highlights.map((item) => <li key={item.name}><strong>{item.name}</strong><span>{item.evidence}</span></li>)}</ul></section>
          )}
          <p className="method-note">This comparison uses phrases found in the resume text. A missing phrase does not prove a missing ability; add relevant evidence to the resume if you have it.</p>
        </div>
        <aside className="learning-panel" aria-labelledby="learning-title">
          <div className="learning-panel__title"><div><p className="eyebrow">A PRACTICAL GROWTH PLAN</p><h2 id="learning-title">Build the next skill.</h2></div></div>
          <p className="learning-intro">Start with required gaps, then use a small project to make your learning visible.</p>
          {result.learning_resources.length ? (
            <ol className="resource-list">{result.learning_resources.map((resource, index) => (
              <li key={`${resource.skill}-${resource.url}`}><div className="resource-step">{String(index + 1).padStart(2, "0")}</div><div className="resource-detail"><span className="resource-priority">{resource.priority} skill</span><strong>{resource.skill}</strong><span className="resource-source">{resource.practice_task}</span><a href={resource.url} target="_blank" rel="noreferrer" aria-label={`Open ${resource.source} resource for ${resource.skill}`}>{resource.source}</a></div></li>
            ))}</ol>
          ) : <p className="empty-copy">No recognized gaps to build a learning plan from yet.</p>}
        </aside>
      </div>
      <div className="privacy-banner"><div><strong>Your resume is processed in memory for this analysis.</strong><p>Clearpath does not write uploaded files, personal details, or reports to a database. Your browser keeps this result until you clear it or close the page.</p></div><button onClick={onReset}>Clear analysis</button></div>
      <p className="method-note method-note--footer">This is career guidance based on extracted text, not a hiring decision or a guarantee of ATS results. {result.method === "semantic-enhanced" ? "Related phrase matches are suggestions; review them before relying on the score." : "Install and enable the optional semantic model for related-phrase suggestions."}</p>
    </main>
  );
}

export default function App() {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [jobDescription, setJobDescription] = useState("");
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  function acceptFile(nextFile) {
    if (!nextFile) return;
    const extension = nextFile.name.toLowerCase().match(/\.[^.]+$/)?.[0];
    if (!ACCEPTED.includes(extension)) { setError("Please choose a PDF, DOCX, or TXT resume."); return; }
    if (nextFile.size > MAX_BYTES) { setError("That file is over 10 MB. Choose a smaller file to continue."); return; }
    setFile(nextFile);
    setError("");
  }

  async function loadExample() {
    setError("");
    try {
      const response = await fetch("/sample-resume.txt");
      if (!response.ok) throw new Error("The sample resume is unavailable right now.");
      const text = await response.text();
      setFile(new File([text], "clearpath-sample-resume.txt", { type: "text/plain" }));
      setJobDescription(SAMPLE_JOB);
      document.getElementById("analyze")?.scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (err) { setError(err.message || "Couldn't load the sample. You can still add your own resume."); }
  }

  async function analyze(event) {
    event.preventDefault();
    if (!file) { setError("Add your resume or choose Try a sample to get started."); return; }
    if (jobDescription.trim().length < 60) { setError("Add a little more of the job description (at least 60 characters)."); return; }
    setError("");
    setLoading(true);
    try {
      const form = new FormData();
      form.append("resume", file);
      form.append("job_description", jobDescription);
      const response = await fetch(ANALYZE_ENDPOINT, { method: "POST", body: form, cache: "no-store" });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || "We couldn't analyze that resume. Please try again.");
      setResult(payload);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(err.message || "We couldn't connect to the analysis service. Please try again.");
    } finally { setLoading(false); }
  }

  function reset() {
    setResult(null);
    setError("");
    setFile(null);
    setJobDescription("");
    if (inputRef.current) inputRef.current.value = "";
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <div className="app-shell" id="top">
      <div className="ambient" aria-hidden="true" />
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Clearpath home"><span>clearpath<span className="brand-period">.</span></span></a>
        <nav className="topnav" aria-label="Main navigation"><a className="topnav__active" href="#analyze">Analyze</a><a href="#how-it-works">How it works</a></nav>
      </header>

      {result ? <Results result={result} filename={file?.name ?? "your resume"} onReset={reset} /> : (
        <main className="hero" id="top-content">
          <section className="hero-copy"><p className="eyebrow hero-kicker"><span /> RESUME × ROLE, IN FOCUS</p><h1>Clarity for<br />your <em>next move.</em></h1><p className="hero-description">See the strengths you already bring, the skills to build, and where to focus next for the role you want.</p><a className="scroll-cue" href="#analyze"><span className="scroll-cue__icon" aria-hidden="true">↘</span><span>Start with your resume</span></a><p className="privacy-note">Your resume is processed for this comparison and is not saved.</p></section>

          <section className="analyzer-panel" id="analyze" aria-labelledby="panel-title">
            <div className="panel-heading"><div><p className="eyebrow">YOUR MATCH, MADE CLEAR</p><h2 id="panel-title">Bring the role into focus.</h2></div><span className="panel-step">01 <span>/ 01</span></span></div>
            <form onSubmit={analyze} aria-busy={loading}>
              <div className="field-group"><div className="field-label"><span>01</span><div><label htmlFor="resume-upload">Your resume</label><small>PDF, DOCX, or TXT · up to 10 MB</small></div></div>
                {!file ? <button type="button" className={`dropzone${dragging ? " dropzone--dragging" : ""}`} onClick={() => inputRef.current?.click()} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); acceptFile(event.dataTransfer.files?.[0]); }}><span className="upload-icon" aria-hidden="true">↑</span><strong>Drop it here, or <u>browse files</u></strong><span className="dropzone-hint">Your file is used for this comparison only</span></button> : <div className="file-chip"><span className="file-chip__type">{file.name.toLowerCase().endsWith(".pdf") ? "PDF" : file.name.toLowerCase().endsWith(".docx") ? "DOCX" : "TXT"}</span><span className="file-chip__meta"><strong>{file.name}</strong><small>{formatSize(file.size)} · Ready to review</small></span><button type="button" className="remove-file" onClick={() => { setFile(null); if (inputRef.current) inputRef.current.value = ""; }}>Remove</button></div>}
                <input ref={inputRef} id="resume-upload" className="visually-hidden" type="file" accept=".pdf,.docx,.txt" onChange={(event) => acceptFile(event.target.files?.[0])} />
              </div>
              <div className="field-group field-group--description"><div className="field-label"><span>02</span><div><label htmlFor="job-description">The job description</label><small>Paste the full listing for a more useful comparison</small></div></div><textarea id="job-description" value={jobDescription} disabled={loading} onChange={(event) => setJobDescription(event.target.value)} placeholder="Paste the role, responsibilities, and the skills they’re looking for…" rows={5} /><div className="textarea-footer"><span>{jobDescription.trim().length < 60 ? "A little more detail helps" : "Ready to compare"}</span><span>{jobDescription.length} characters</span></div><button type="button" className="sample-description-button" onClick={() => setJobDescription(SAMPLE_JOB)}>Use sample job description</button></div>
              {error && <p className="form-error" role="alert">{error}</p>}
              <div className="form-actions"><button className="analyze-button" type="submit" disabled={loading}>{loading ? <><span className="loading-dot" aria-hidden="true" /> Reading the details…</> : "See my match"}</button><button type="button" className="try-sample-button" onClick={loadExample} disabled={loading}>Try a sample</button></div>
              <details className="score-method"><summary>How the match score works</summary><p>Clearpath compares recognized skills in the job description with evidence in the resume. Required skills count twice as much as preferred skills. The score is guidance, not an employer or ATS decision.</p></details>
              <p className="form-footnote">No account. In-memory processing. No resume storage or analysis history.</p>
            </form>
          </section>
          <div className="hero-index">01 <span>—</span> A clearer next step</div>
        </main>
      )}

      <section className="how-section" id="how-it-works" aria-labelledby="how-title">
        <div className="how-section__heading"><p className="eyebrow">A SIMPLE, TRANSPARENT PROCESS</p><h2 id="how-title">From experience<br />to <em>next steps.</em></h2></div>
        <ol><li><span>01</span><div><strong>Bring your experience</strong><p>Upload a resume. Clearpath reads selectable text from the file for this comparison.</p></div></li><li><span>02</span><div><strong>See the evidence</strong><p>Compare skill phrases from the listing with phrases found in your resume. Required skills carry more weight.</p></div></li><li><span>03</span><div><strong>Choose a next step</strong><p>Review missing requirements, practice tasks, and learning links. Add evidence you already have.</p></div></li></ol>
      </section>
      <footer className="site-footer"><span>© 2026 clearpath. Built to help you move forward.</span><span>Compare <b>→</b> Understand <b>→</b> Grow</span></footer>
    </div>
  );
}
