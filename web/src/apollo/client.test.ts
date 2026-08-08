import { describe, expect, it, vi } from "vitest";

import { createApolloClient, validateCredentials } from "./client";

describe("authenticated Apollo client", () => {
  it("probes the relative GraphQL endpoint with the session authorization header", async () => {
    const fetchImpl = vi.fn<typeof fetch>(async (_input, init) => {
      expect(_input).toBe("/graphql");
      expect(new Headers(init?.headers).get("authorization")).toBe(
        "Basic test-session",
      );

      return new Response(JSON.stringify({ data: { __typename: "Query" } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });
    const client = createApolloClient("Basic test-session", fetchImpl);

    await expect(validateCredentials(client)).resolves.toBeUndefined();
    expect(fetchImpl).toHaveBeenCalledOnce();
  });
});
