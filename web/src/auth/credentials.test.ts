import { describe, expect, it } from "vitest";

import {
  CredentialInputError,
  createBasicAuthorization,
} from "./credentials";

describe("Basic credential encoding", () => {
  it.each([
    {
      caseName: "an empty username",
      credentials: { username: "", password: "something" },
    },
    {
      caseName: "a whitespace-only username",
      credentials: { username: "    ", password: "something" },
    },
    {
      caseName: "an empty password",
      credentials: { username: "superman", password: "" },
    },
    {
      caseName: "a whitespace-only password",
      credentials: { username: "superman", password: "    " },
    },
    {
      caseName: "a colon in the username",
      credentials: { username: "super:man", password: "something" },
    },
  ])("rejects $caseName", ({ credentials }) => {
    expect(() => createBasicAuthorization(credentials)).toThrow(
      CredentialInputError,
    );
  });

  it("preserves surrounding whitespace in a valid username", () => {
    expect(
      createBasicAuthorization({
        username: "  superman  ",
        password: "something",
      }),
    ).toBe("Basic ICBzdXBlcm1hbiAgOnNvbWV0aGluZw==");
  });

  it("encodes non-ASCII credentials as UTF-8 before Base64", () => {
    expect(
      createBasicAuthorization({ username: "søker", password: "påssord" }),
    ).toBe("Basic c8O4a2VyOnDDpXNzb3Jk");
  });
});
