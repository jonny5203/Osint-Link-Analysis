MATCH (left:Entity)-[link:SAME_AS|POSSIBLE_MATCH]->(right:Entity)
WITH left, right, count(link) AS link_count
WHERE left.id >= right.id OR link_count <> 1
RETURN count(*) AS violations;
