package io.nexus.api.node;

import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;

/**
 * Address node (PLAN.md §3, T7.2). Required: id, country. Optional: city, raw.
 * Note: Address has no `name`, so it does NOT implement the GraphQL `Node` interface.
 */
@Node("Address")
public class Address {
    @Id private String id;
    // TODO(T7.2): @Id String id; String country; String city; String raw;
}
