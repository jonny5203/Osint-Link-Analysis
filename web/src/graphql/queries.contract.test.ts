import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { buildSchema, validate } from "graphql";
import { describe, expect, it } from "vitest";

import {
    ENTITY,
    NEIGHBORHOOD,
    SEARCH,
    SHORTEST_PATH
} from "./queries";

const schemaPath = resolve(
  process.cwd(),
  "../api/src/main/resources/graphql/schema.graphqls",
);

const schema = buildSchema(
    readFileSync(schemaPath, "utf8")
)

const documents = {
    SEARCH,
    ENTITY,
    NEIGHBORHOOD,
    SHORTEST_PATH
};

describe("GraphQL query contract", () => {
  for (const [name, document] of Object.entries(documents)) {
    it(`${name} matches the server schema`, () => {
      const errors = validate(schema, document);

      expect(
        errors.map((error) => error.message),
      ).toEqual([]);
    });
  }
});