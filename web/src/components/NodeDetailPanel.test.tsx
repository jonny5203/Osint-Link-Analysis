import "@testing-library/jest-dom/vitest";
import { MockedProvider } from "@apollo/client/testing";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { EntityResult } from "../graphql/queries";
import { NodeDetailPanel } from "./NodeDetailPanel";

const detailResult: EntityResult = {
  entity: {
    node: {
      id: "fixture:entity:avery",
      kind: "PERSON",
      displayName: "Avery Stone",
      aliases: ["A. Stone"],
      sanctioned: false,
      datasetIds: ["fixture:dataset:alpha"],
    },
    normalizedName: "avery stone",
    datesOfBirth: [],
    nationalities: [],
    jurisdiction: null,
    registrationNumber: null,
    imo: null,
    flag: null,
    programs: [],
    sourceRecords: [
      {
        id: "fixture:record:alpha:avery",
        datasetId: "fixture:dataset:alpha",
        datasetName: "Fictional Dataset Alpha",
        externalId: "avery-001",
        retrievedAt: "2026-07-20T10:00:00Z",
        recordHash: "hash",
        active: true,
      },
    ],
    matches: [
      {
        edgeId: "match-1",
        otherEntityId: "fixture:entity:avery-variant",
        type: "POSSIBLE_MATCH",
        score: 0.82,
        reasons: ["similar normalized name"],
        algorithmVersion: "fixture-v1",
        decidedAt: null,
        decisionSource: null,
        reviewStatus: "PENDING",
      },
    ],
  },
};

describe("NodeDetailPanel", () => {
  it("shows provenance and labels possible matches as leads rather than facts", async () => {
    render(
      <MockedProvider>
        <NodeDetailPanel
          selectedNodeId="fixture:entity:avery"
          detailLoader={() => Promise.resolve(detailResult)}
        />
      </MockedProvider>,
    );

    expect(await screen.findByText("Avery Stone")).toBeInTheDocument();
    expect(screen.getByText("fixture:record:alpha:avery")).toBeInTheDocument();
    expect(
      screen.getByText("This is a lead, not a verified identity fact."),
    ).toBeInTheDocument();
  });
});
