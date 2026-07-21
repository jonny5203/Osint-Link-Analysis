MATCH (run:ImportRun)
WHERE run.status = "SUCCEEDED"
  AND (
    run.sha256 IS NULL
    OR NOT run.sha256 =~ "^[0-9a-f]{64}$"
    OR any(value IN [
      run.record_count,
      run.inserted_count,
      run.updated_count,
      run.unchanged_count,
      run.failed_count
    ] WHERE value IS NULL OR value < 0)
    OR run.record_count <>
       run.inserted_count +
       run.updated_count +
       run.unchanged_count +
       run.failed_count
  )
RETURN count(run) AS violations;
