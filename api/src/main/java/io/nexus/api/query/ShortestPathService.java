package io.nexus.api.query;

import org.springframework.stereotype.Service;

/** Raw Cypher shortest-path via Neo4jClient (PLAN.md T7.4). */
@Service
public class ShortestPathService {
    // TODO(T7.4): MATCH p = shortestPath((a)--(b)) ... via Neo4jClient.unboundRunnable().cypher(...)
}
