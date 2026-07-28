package io.nexus.api.query.input_validation;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.fail;

import org.junit.jupiter.api.Test;

class StableEdgeIdsTest {

    @Test
    void producesStableVersionedSha256Ids() {
        String first = StableEdgeIds.from(
                "fixture:entity:avery",
                "OWNS",
                "fixture:entity:northstar");

        String second = StableEdgeIds.from(
                "fixture:entity:avery",
                "OWNS",
                "fixture:entity:northstar");

        assertThat(first)
                .isEqualTo(second)
                .startsWith("edge:v1:")
                .hasSize(72);
    }

    @Test
    void changesWhenTheCanonicalTupleChanges() {
        String original = StableEdgeIds.from(
                "a",
                "OWNS",
                "b");

        assertThat(
                StableEdgeIds.from("b", "OWNS", "a")).isNotEqualTo(original);

        assertThat(
                StableEdgeIds.from("a", "CONTROLS", "b")).isNotEqualTo(original);

        assertThat(
                StableEdgeIds.from("a", "OWNS", "b", "director")).isNotEqualTo(original);
    }
}
