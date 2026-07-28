package io.nexus.api.query;

import java.util.List;

import org.springframework.stereotype.Controller;

import io.nexus.api.query.dto.EntityDetailDto;
import io.nexus.api.query.dto.GraphSliceDto;
import io.nexus.api.query.dto.SearchHitDto;
import io.nexus.api.query.input_validation.GraphQueryService;

import org.springframework.graphql.data.method.annotation.Argument;
import org.springframework.graphql.data.method.annotation.QueryMapping;

@Controller
public class QueryController{
    private final GraphQueryService service;

    public QueryController(GraphQueryService service) {
        this.service = service;
    }

    @QueryMapping
    public EntityDetailDto entity(@Argument String id){
        return service.entity(id).orElse(null);
    }

    @QueryMapping
    public List<SearchHitDto> searchEntities(
        @Argument String term,
        @Argument Integer limit
    ) {
        return service.search(term, limit);
    }

    @QueryMapping
    public GraphSliceDto neighborhood(
        @Argument String id,
        @Argument Integer depth,
        @Argument Integer nodeLimit,
        @Argument Integer edgeLimit
    ) {
        return service.neighborhood(id, depth, nodeLimit, edgeLimit);
    }

    @QueryMapping
    public GraphSliceDto shortestPath(
        @Argument String fromId,
        @Argument String toId,
        @Argument Integer maxHops
    ) {
        return service.shortestPath(fromId, toId, maxHops).orElse(null);
    }
}
