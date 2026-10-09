# MongoDB Document Model

The app stores repository profile, selected requirements, and the current
deployment specification together in one `projects` document. Versioned output
and workflow history use separate collections so each record can be queried and
indexed independently.

```mermaid
flowchart LR
    P[projects\nprofile + requirements + deployment_spec]
    A[artifact_generations\nversioned artifacts]
    V[validation_runs\nstatus + embedded errors]
    R[repair_attempts\nsource + repaired generation]
    P -->|project_id| A
    P -->|project_id| V
    A -->|generation_id| V
    P -->|project_id| R
    V -->|validation_run_id| R
```

Indexes are created by the FastAPI startup lifecycle. Artifact versions are
unique per project; project history is indexed by project and creation time.
