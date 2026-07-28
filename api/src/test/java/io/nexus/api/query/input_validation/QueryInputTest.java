package io.nexus.api.query.input_validation;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

import io.nexus.api.query.input_validation.exceptions.ApiInputException;

class QueryInputTest {
    
    @Test
    void trimsValidaSearchTerms(){
        assertThat(QueryInputs.searchTerm("  Avery  "))
            .isEqualTo("Avery");
    }

    @Test
    void rejectsShortSearchTerms(){
        assertThatThrownBy(() -> QueryInputs.searchTerm("a"))
            .isInstanceOf(ApiInputException.class)
            .hasMessageContaining("between 2 and 100");
    }

    @Test
    void escapesLuceneSyntax() {
        assertThat(QueryInputs.luceneLiteral("A+B/C"))
            .isEqualTo("A\\+B\\/C");
    }

    @Test
    void clampsSearchLimits() {
        assertThat(QueryInputs.searchLimit(null)).isEqualTo(20);
        assertThat(QueryInputs.searchLimit(0)).isEqualTo(1);
        assertThat(QueryInputs.searchLimit(51)).isEqualTo(50);
    }

    @Test
    void acceptsOnlyDepthOne() {
        QueryInputs.depth(1);

        assertThatThrownBy(() -> QueryInputs.depth(2))
            .isInstanceOf(ApiInputException.class)
            .hasMessage("depth must be 1 in Nexus v1");
    }

    @Test
    void validatesBoundedLimits() {
        assertThat(
            QueryInputs.boundedLimit(
                "edgeLimit", 
                null,
                200,
                500)
        ).isEqualTo(200);

        assertThatThrownBy(() -> 
            QueryInputs.boundedLimit(
                "edgeLimit",
                501,
                200,
                500
            )
        )
        .isInstanceOf(ApiInputException.class)
        .hasMessage(
            "edgeLimit must be between 1 and 500"
        );
    }

    @Test
    void validatesMaximumHops() {
        assertThat(QueryInputs.maxHops(null)).isEqualTo(6);
        assertThat(QueryInputs.maxHops(1)).isEqualTo(1);

        assertThatThrownBy(() -> QueryInputs.maxHops(100))
            .isInstanceOf(ApiInputException.class)
            .hasMessage("maxHops must be between 1 and 6");
    }

    @Test
    void rejectsBlankIds() {
        assertThatThrownBy(() -> QueryInputs.id("id", ""))
            .isInstanceOf(ApiInputException.class)
            .hasMessageContaining("non-blank ID");
    }

    @Test
    void exposesOnlyAnalystRelationshipTypes() {
        assertThat(GraphQueryService.ANALYST_RELATIONSHIP_TYPES)
            .containsExactly(
                "OWNS",
                "CONTROLS",
                "OFFICER_OF",
                "LOCATED_AT",
                "SAME_AS",
                "POSSIBLE_MATCH"
            );
    }
}
