import { ApolloClient, InMemoryCache, createHttpLink } from "@apollo/client";

// PLAN.md T9.1: /graphql is proxied to the Spring API (see vite.config.ts).
// TODO(T9.1): inject Basic auth header (hardcoded analyst creds for v1 — document this).
export const apolloClient = new ApolloClient({
  link: createHttpLink({ uri: "/graphql" }),
  cache: new InMemoryCache(),
});
