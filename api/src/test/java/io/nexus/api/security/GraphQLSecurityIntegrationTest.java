package io.nexus.api.security;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.not;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.security.test.web.servlet.setup.SecurityMockMvcConfigurers.springSecurity;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

import org.testcontainers.shaded.com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;

@SpringBootTest
@ActiveProfiles("test")
class GraphQlSecurityIntegrationTest {

    @Value("${ANALYST_USERNAME}")
    private String username;

    @Value("${ANALYST_PASSWORD}")
    private String password;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Autowired
    private WebApplicationContext context;

    private MockMvc mockMvc;

    @BeforeEach
    void configureMockMvc() {
        mockMvc = MockMvcBuilders
            .webAppContextSetup(context)
            .apply(springSecurity())
            .build();
    }

    @Test
    void unauthenticatedGraphQlRequestReturns401()
        throws Exception {

        mockMvc.perform(
            post("/graphql")
                .contentType(MediaType.APPLICATION_JSON)
                .content(body("{ __typename }"))
        )
            .andExpect(status().isUnauthorized());
    }

    @Test
    void wrongCredentialsReturn401WithoutEchoingPassword()
        throws Exception {

        mockMvc.perform(
            post("/graphql")
                .with(httpBasic(username, "wrong-" + password))
                .contentType(MediaType.APPLICATION_JSON)
                .content(body("{ __typename }"))
        )
            .andExpect(status().isUnauthorized())
            .andExpect(
                content().string(not(containsString(password)))
            );
    }

    @Test
    void validAnalystCredentialsSucceed() throws Exception {
        mockMvc.perform(
            post("/graphql")
                .with(httpBasic(username, password))
                .contentType(MediaType.APPLICATION_JSON)
                .content(body("{ __typename }"))
        )
            .andExpect(status().isOk())
            .andExpect(
                jsonPath("$.data.__typename").value("Query")
            );
    }

    @Test
    void invalidInputBecomesSafeGraphQlError()
        throws Exception {

        String query = """
            query {
              shortestPath(
                fromId: "a"
                toId: "b"
                maxHops: 100
              ) {
                truncated
              }
            }
            """;

        mockMvc.perform(
            post("/graphql")
                .with(httpBasic(username, password))
                .contentType(MediaType.APPLICATION_JSON)
                .content(body(query))
        )
            .andExpect(status().isOk())
            .andExpect(
                jsonPath("$.errors[0].message")
                    .value("maxHops must be between 1 and 6")
            )
            .andExpect(
                jsonPath(
                    "$.errors[0].extensions.classification"
                ).value("BAD_REQUEST")
            )
            .andExpect(
                content().string(not(containsString(password)))
            );
    }

    private String body(String query) throws Exception {
        return objectMapper.writeValueAsString(
            Map.of("query", query)
        );
    }
}
