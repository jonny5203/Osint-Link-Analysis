package io.nexus.api.node;

import java.util.List;

import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;

@Node("Organization")
public class Organization {
    @Id
    private String id;

    protected Organization() {

    }

    public Organization(String id) {
        this.id = id;
    }

    public String getId() {
        return id;
    }
}
