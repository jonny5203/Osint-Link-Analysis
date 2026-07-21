MATCH (record:SourceRecord)
OPTIONAL MATCH (record)-[relationship:FROM_DATASET]->(:Dataset)
WITH record, count(relationship) AS relationship_count
WHERE relationship_count <> 1
RETURN count(record) AS violations;
