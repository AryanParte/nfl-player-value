import { useEffect, useState } from "react";
import {
  evidenceUrl,
  GATES,
  GROUPS,
  loadAdmission,
  registryPath,
  STATUSES,
} from "./admission";
import type { Admission } from "./admission";

export function ModuleAvailability() {
  const [data, setData] = useState<Admission>();
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [selected, setSelected] = useState("QB");
  useEffect(() => {
    const controller = new AbortController();
    setError("");
    loadAdmission(new URL("./", window.location.href), controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setData(value);
      })
      .catch((e: unknown) => {
        if (!controller.signal.aborted)
          setError(
            e instanceof Error && e.name !== "ZodError"
              ? e.message
              : "The availability record failed validation. No admission decision has been displayed.",
          );
      });
    return () => controller.abort();
  }, [attempt]);
  const module =
    data && Object.values(data.modules).find((m) => m.role === selected);
  return (
    <section
      id="availability"
      className="availability"
      aria-labelledby="availability-title"
    >
      <div className="section-heading">
        <div>
          <p className="eyebrow">ALL POSITIONS · MEASUREMENT STATUS</p>
          <h2 id="availability-title">CAVAA availability</h2>
        </div>
        {data && <span className="tag">{data.season} RESEARCH</span>}
      </div>
      {!data ? (
        <div className="availability-empty">
          <p role={error ? "alert" : "status"}>
            {error || "Checking the reviewed module decisions."}
          </p>
          {error && (
            <button
              className="primary"
              onClick={() => setAttempt((n) => n + 1)}
            >
              Retry availability
            </button>
          )}
        </div>
      ) : (
        <>
          <p className="availability-intro">
            <strong>No CAVAA rankings published.</strong> None of the{" "}
            {Object.keys(data.modules).length} contribution modules has passed
            all required checks. Missing scores do not mean zero value.
          </p>
          <p className="muted availability-date">
            Model review:{" "}
            <time dateTime={data.decided_at}>November 2, 2026</time>. This
            review does not refresh game coverage or change the Explorer’s
            archived cutoff.
          </p>
          <div className="availability-grid">
            <div className="module-picker">
              {Object.entries(GROUPS).map(([group, roles]) => (
                <fieldset key={group}>
                  <legend>{group}</legend>
                  <div className="module-buttons">
                    {roles.map((role) => (
                      <button
                        key={role}
                        aria-pressed={selected === role}
                        aria-controls="module-detail"
                        onClick={() => setSelected(role)}
                      >
                        {role}
                      </button>
                    ))}
                  </div>
                </fieldset>
              ))}
              <p className="muted">
                Participation thresholds and model admission are separate.
                Playing enough games cannot resolve an unvalidated estimate.
              </p>
            </div>
            {module && (
              <div
                id="module-detail"
                className="module-detail"
                role="region"
                aria-label={`${module.role} measurement status`}
              >
                <div className="module-title">
                  <h3>{module.role} contribution</h3>
                  <span className="tag">NOT ADMITTED</span>
                </div>
                <p className="module-scope">{module.scope_label}</p>
                <p className="module-value">
                  Cumulative CAVAA: <strong>Not available</strong>
                </p>
                <div className="gate-list">
                  {Object.entries(GATES).map(([gate, label]) => {
                    const finding =
                      data.findings[module.gates[gate as keyof typeof GATES]];
                    return (
                      <details
                        key={`${selected}/${gate}`}
                        className={`gate gate-${finding.status}`}
                      >
                        <summary>
                          <span>{label}</span>
                          <span className="gate-status">
                            {STATUSES[finding.status]}
                          </span>
                        </summary>
                        <p>{finding.reason}</p>
                        <ul className="evidence-links">
                          {finding.evidence_refs.map((ref) => (
                            <li key={ref}>
                              <a href={evidenceUrl(data.sources[ref])}>
                                {ref.replaceAll("_", " ")} ↗
                              </a>
                            </li>
                          ))}
                        </ul>
                      </details>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
          <p className="availability-policy">
            The intended metric is cumulative expected points above the
            first-unit positional benchmark. Equal-player and
            opportunity-weighted comparisons remain sensitivity checks. Earlier
            games are retained.
          </p>
          <a className="download" href={`./${registryPath}`} download>
            Download reviewed decisions ↓
          </a>
        </>
      )}
    </section>
  );
}
