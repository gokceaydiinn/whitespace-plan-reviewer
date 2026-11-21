
import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

type Task = {
  id: string;
  name: string;
  owner: string | null;
  duration_days: number;
  depends_on: string[];
  quote: string;
  confidence?: number | null;
  flags?: string[];
};

type Finding = {
  title: string;
  detail: string;
  quote: string | null;
  action?: string | null;
};

type Schedule = {
  status: 'scheduled' | 'cycle';
  schedule: {
    id: string;
    start_day: number | null;
    end_day: number | null;
  }[];
  meets_deadline: boolean | null;
  days_late: number | null;
  cycle: string[];
};

type PlanSummary = {
  id: string;
  title: string;
};

type Plan = {
  id: string;
  text: string;
  review: {
    deadline_day: number | null;
    tasks: Task[];
    findings: Finding[];
  };
  schedule: Schedule;
};

export default function App() {
  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [plan, setPlan] = useState<Plan | null>(null);
  const [editedTasks, setEditedTasks] = useState<Task[]>([]);
  const [currentSchedule, setCurrentSchedule] = useState<Schedule | null>(null);
  const [scheduleError, setScheduleError] = useState('');
  const [calculating, setCalculating] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    fetch('/api/plans')
      .then((response) => {
        if (!response.ok) throw new Error('Could not load plans.');
        return response.json();
      })
      .then((items: PlanSummary[]) => {
        setPlans(items);
        if (items.length > 0) setSelectedId(items[0].id);
      })
      .catch((error) => setScheduleError(error.message));
  }, []);

  useEffect(() => {
    if (!selectedId) return;

    let cancelled = false;

    setPlan(null);
    setEditedTasks([]);
    setCurrentSchedule(null);
    setScheduleError('');
    setHasChanges(false);

    fetch(`/api/plans/${selectedId}`)
      .then((response) => {
        if (!response.ok) throw new Error('Could not load this plan.');
        return response.json();
      })
      .then((data: Plan) => {
        if (cancelled) return;

        setPlan(data);
        setEditedTasks(data.review.tasks);
        setCurrentSchedule(data.schedule);
      })
      .catch((error) => {
        if (!cancelled) setScheduleError(error.message);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  function updateTask(id: string, changes: Partial<Task>) {
    setEditedTasks((tasks) =>
      tasks.map((task) =>
        task.id === id ? { ...task, ...changes } : task
      )
    );
    setHasChanges(true);
    setScheduleError('');
  }

  async function recalculate() {
    if (!plan || calculating) return;

    if (plan.review.deadline_day === null) {
      setScheduleError('A deadline is needed to calculate the schedule.');
      return;
    }

    setCalculating(true);
    setScheduleError('');

    try {
      const response = await fetch('/api/schedule', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          deadline_day: plan.review.deadline_day,
          tasks: editedTasks.map((task) => ({
            id: task.id,
            name: task.name,
            owner: task.owner,
            duration_days: task.duration_days,
            depends_on: task.depends_on,
          })),
        }),
      });

      if (!response.ok) {
        throw new Error(
          'Could not calculate the schedule. Check durations and dependencies.'
        );
      }

      const result: Schedule = await response.json();
      setCurrentSchedule(result);
      setHasChanges(false);
    } catch (error) {
      setScheduleError(
        error instanceof Error ? error.message : 'Something went wrong.'
      );
    } finally {
      setCalculating(false);
    }
  }

  const finishDay =
    currentSchedule?.status === 'scheduled'
      ? Math.max(
          0,
          ...currentSchedule.schedule.map((task) => task.end_day ?? 0)
        )
      : null;

  return (
    <main className="app">
      <header className="app-header">
        <div className="brand">WhiteSpace / Plan reviewer</div>

        <label>
          Plan{' '}
          <select
            value={selectedId}
            onChange={(event) => setSelectedId(event.target.value)}
          >
            {plans.map((item) => (
              <option key={item.id} value={item.id}>
                {item.title}
              </option>
            ))}
          </select>
        </label>
      </header>

      {scheduleError && !plan && <p role="alert">{scheduleError}</p>}

      {plan && currentSchedule && (
        <div className="content">
          <h1>{plans.find((item) => item.id === selectedId)?.title}</h1>

          <section className="overview">
            <div className="overview-heading">
              <h2>Schedule overview</h2>
              <span>
                {currentSchedule.status === 'cycle'
                  ? 'Cannot schedule'
                  : plan.review.deadline_day === null
                    ? 'Deadline not specified'
                    : currentSchedule.meets_deadline === true
                      ? 'Meets deadline'
                      : currentSchedule.meets_deadline === false
                        ? 'Past deadline'
                        : 'Needs review'}
              </span>
            </div>

            {hasChanges && (
              <p className="schedule-notice">
                Tasks have changed. Recalculate to update these results.
              </p>
            )}

            <div className="overview-stats">
              <div>
                <small>Earliest finish</small>
                <strong>
                  {finishDay !== null ? `Day ${finishDay}` : 'Not available'}
                </strong>
              </div>

              <div>
                <small>Deadline</small>
                <strong>
                  {plan.review.deadline_day !== null
                    ? `Day ${plan.review.deadline_day}`
                    : 'Not specified'}
                </strong>
              </div>

              <div>
                <small>Days late</small>
                <strong>
                  {currentSchedule.days_late ?? 'Not available'}
                </strong>
              </div>
            </div>

            {currentSchedule.status === 'cycle' && (
              <p role="alert">
                Circular dependencies found in tasks:{' '}
                {currentSchedule.cycle.join(', ')}.
              </p>
            )}
          </section>

          <section className="findings-section">
            <div className="findings-heading">
              <h2>Things to check</h2>
              <span>{plan.review.findings.length} findings</span>
            </div>

            {plan.review.findings.length === 0 ? (
              <p>No findings reported.</p>
            ) : (
              plan.review.findings.map((finding, index) => (
                <div className="finding-item" key={index}>
                  <span className="finding-number">
                    {String(index + 1).padStart(2, '0')}
                  </span>

                  <div className="finding-content">
                    <strong>{finding.title}</strong>
                    <p>{finding.action || finding.detail}</p>

                    <details className="finding-details">
                      <summary>View details</summary>
                      <p>{finding.detail}</p>
                      {finding.quote && (
                        <blockquote>{finding.quote}</blockquote>
                      )}
                    </details>
                  </div>
                </div>
              ))
            )}
          </section>

          <section>
            <div className="tasks-heading">
              <div>
                <h2>Tasks</h2>
                <p>
                  Edit task details, then recalculate the schedule.
                </p>
              </div>

              <button
                type="button"
                className="recalculate-button"
                onClick={recalculate}
                disabled={calculating}
              >
                {calculating ? 'Calculating...' : 'Recalculate schedule'}
              </button>
            </div>

            {scheduleError && <p role="alert">{scheduleError}</p>}

            <div className="tasks-table">
              <table>
                <thead>
                  <tr>
                    <th>Task</th>
                    <th>Owner</th>
                    <th>Days</th>
                    <th>Depends on</th>
                    <th>Start</th>
                    <th>End</th>
                  </tr>
                </thead>

                <tbody>
                  {editedTasks.map((task) => {
                    const scheduled = currentSchedule.schedule.find(
                      (entry) => entry.id === task.id
                    );

                    return (
                      <tr key={task.id}>
                        <td>
                          <strong>{task.name}</strong>
                          {task.flags && task.flags.length > 0 && (
                            <details>
                              <summary>Check assumptions</summary>
                              {task.flags.map((flag, index) => (
                                <p key={index}>{flag}</p>
                              ))}
                            </details>
                          )}
                          <details>
                            <summary>Source</summary>
                            <blockquote>{task.quote}</blockquote>
                          </details>
                        </td>

                        <td>
                          <input
                            aria-label={`Owner for ${task.name}`}
                            value={task.owner ?? ''}
                            placeholder="Unassigned"
                            onChange={(event) =>
                              updateTask(task.id, {
                                owner: event.target.value || null,
                              })
                            }
                          />
                        </td>

                        <td>
                          <input
                            aria-label={`Duration for ${task.name}`}
                            type="number"
                            min="1"
                            step="1"
                            value={task.duration_days}
                            onChange={(event) =>
                              updateTask(task.id, {
                                duration_days: Number(event.target.value),
                              })
                            }
                          />
                        </td>

                        <td>
                          <input
                            aria-label={`Dependencies for ${task.name}`}
                            value={task.depends_on.join(', ')}
                            placeholder="None"
                            onChange={(event) =>
                              updateTask(task.id, {
                                depends_on: event.target.value
                                  .split(',')
                                  .map((value) => value.trim())
                                  .filter(Boolean),
                              })
                            }
                          />
                        </td>

                        <td>
                          {!hasChanges
                            ? scheduled?.start_day ?? '—'
                            : '—'}
                        </td>
                        <td>
                          {!hasChanges
                            ? scheduled?.end_day ?? '—'
                            : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <p className="task-help">
              Enter dependency IDs separated by commas, for example T1, T2.
              Leave the field empty for no dependencies.
            </p>
          </section>

          <section>
            <details>
              <summary>Original plan</summary>

              <div className="plan-document">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {plan.text}
                </ReactMarkdown>
              </div>
            </details>
          </section>
        </div>
      )}
    </main>
  );
}
