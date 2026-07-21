MATCH (node)
WHERE (node:Person OR node:Organization OR node:Vessel OR node:Address)
    AND NOT node:Entity
RETURN count(node) AS violations;
