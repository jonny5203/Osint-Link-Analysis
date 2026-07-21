package io.nexus.api.node;

import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;

/** Source node (PLAN.md §3, T7.2). Required: id, list, url, retrieved_at. */
@Node("Source")
public class Source {
    @Id private String id;
    // TODO(T7.2): @Id String id; String list; String url; String retrievedAt;
}
