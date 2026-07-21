package io.nexus.api.node;

import org.springframework.data.neo4j.repository.Neo4jRepository;

/**
 * Read repository (PLAN.md T7.3).
 * TODO(T7.3): findByNameContainingIgnoreCase(term, Pageable), findById(id),
 *             and a @Query UNION search across Person/Organization/Vessel.
 */
public interface NodeRepository extends Neo4jRepository<Person, String> {
}
