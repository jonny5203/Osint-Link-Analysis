MATCH ()-[relationship:LOCATED_AT|OFFICER_OF|OWNS|CONTROLS]->()
WHERE coalesce(size(relationship.evidence_record_ids), 0) = 0
    AND (
        trim(coalesce(relationship.citation_url, "")) = ""
        OR relationship.citation_retrieved_at IS NULL
    )
RETURN count(relationship) AS violations;
