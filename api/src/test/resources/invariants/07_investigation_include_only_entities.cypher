MATCH (:Investigation)-[relationship:INCLUDES]->(target)
WHERE NOT target:Entity
RETURN count(relationship) AS violations;
