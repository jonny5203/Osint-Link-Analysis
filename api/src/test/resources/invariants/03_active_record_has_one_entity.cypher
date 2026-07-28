MATCH (record:SourceRecord)
WHERE record.active = true
OPTIONAL MATCH (record)-[relationship:DESCRIBES]->(:Entity)
WITH record, count(relationship) AS relationship_count
WHERE relationship_count <> 1
RETURN count(record) AS violations;
