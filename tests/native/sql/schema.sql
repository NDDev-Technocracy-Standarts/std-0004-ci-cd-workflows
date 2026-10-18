CREATE TABLE run_evidence (
    workflow_path VARCHAR(255) NOT NULL,
    run_url VARCHAR(512) NOT NULL,
    proven_digest CHAR(64) NOT NULL
);

SELECT
    workflow_path,
    run_url
FROM run_evidence
WHERE proven_digest IS NOT NULL;
