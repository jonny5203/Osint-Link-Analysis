package io.nexus.api.node;

import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Relationship;

@Node("Address")
public class Address {
    @Id private String id;
    private String country;
    private String city;
    private String raw;
}
