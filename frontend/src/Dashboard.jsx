import { useEffect, useState } from "react";
import axios from "axios";
import "./Dashboard.css";

const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function Dashboard() {
  const [jobId, setJobId] = useState(1);
  const [ranking, setRanking] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadRanking = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await axios.get(
        `${API_URL}/api/evaluation/ranking/${jobId}`
      );

      setRanking(response.data.ranking || []);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Could not load candidate ranking."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRanking();
  }, []);

  return (
    <main className="dashboard">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">AI Recruitment Platform</p>
          <h1>Candidate Ranking Dashboard</h1>
          <p>
            Resume, project, academic, test and GitHub-based
            candidate evaluation.
          </p>
        </div>

        <div className="job-control">
          <label htmlFor="jobId">Job ID</label>

          <input
            id="jobId"
            type="number"
            min="1"
            value={jobId}
            onChange={(event) =>
              setJobId(event.target.value)
            }
          />

          <button onClick={loadRanking}>
            Load Ranking
          </button>
        </div>
      </header>

      {loading && <p>Loading candidates...</p>}

      {error && <p className="error">{String(error)}</p>}

      {!loading && !error && (
        <section className="table-card">
          <div className="table-heading">
            <h2>Ranked Candidates</h2>
            <span>{ranking.length} candidates</span>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Candidate</th>
                  <th>Resume</th>
                  <th>GitHub</th>
                  <th>Coding</th>
                  <th>Overall</th>
                  <th>Recommendation</th>
                </tr>
              </thead>

              <tbody>
                {ranking.map((item) => {
                  const candidate = item.candidates || {};

                  return (
                    <tr key={item.candidate_id}>
                      <td>#{item.rank}</td>

                      <td>
                        <strong>{candidate.name}</strong>
                        <small>
                          {candidate.college || "College not provided"}
                        </small>
                      </td>

                      <td>{item.resume_match_score ?? 0}</td>
                      <td>{item.github_score ?? 0}</td>
                      <td>{item.coding_test_score ?? 0}</td>

                      <td>
                        <strong>
                          {item.overall_score ?? 0}
                        </strong>
                      </td>

                      <td>
                        <span className="badge">
                          {item.recommendation}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </main>
  );
}