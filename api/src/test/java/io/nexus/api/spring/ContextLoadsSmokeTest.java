package io.nexus.api.spring;

import static org.assertj.core.api.Assertions.assertThat;

import org.springframework.context.ApplicationContext;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;


@SpringBootTest
@ActiveProfiles("test")
class ContextLoadsSmokeTest {
    @Test
    void applicationContextStartsWithoutLiveNeo4j(ApplicationContext context){
        assertThat(context).isNotNull();
        assertThat(context.containsBean("nexusApiApplication")).isTrue();
    }
}
