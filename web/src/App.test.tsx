import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("renders the Phase 1 startup page", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "Nexus is starting" }),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Local OSINT link-analysis workspace"),
    ).toBeInTheDocument();
  });
});