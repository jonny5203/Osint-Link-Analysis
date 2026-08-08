import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ApolloError } from "@apollo/client";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { createApolloClient } from "./apollo/client";

function enterCredentials(username = "analyst", password = "demo-password") {
  fireEvent.change(screen.getByLabelText("Username"), {
    target: { value: username },
  });
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: password },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("App authentication session", () => {
  it("gates the explorer behind runtime sign-in", async () => {
    const client = createApolloClient("Basic test-only");
    const authorizationFactory = vi.fn(() => "Basic test-session");
    const clientFactory = vi.fn(() => client);
    const credentialValidator = vi.fn().mockResolvedValue(undefined);

    render(
      <App
        authorizationFactory={authorizationFactory}
        clientFactory={clientFactory}
        credentialValidator={credentialValidator}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Sign in to the graph explorer" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Graph" })).not.toBeInTheDocument();

    enterCredentials();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Graph" })).toBeInTheDocument();
    });
    expect(authorizationFactory).toHaveBeenCalledWith({
      username: "analyst",
      password: "demo-password",
    });
    expect(clientFactory).toHaveBeenCalledWith("Basic test-session");
    expect(credentialValidator).toHaveBeenCalledWith(client);
    expect(window.localStorage).toHaveLength(0);
    expect(window.sessionStorage).toHaveLength(0);
  });

  it.each([
    {
      failureName: "rejected credentials",
      networkError: Object.assign(new Error("Raw unauthorized HTTP response"), {
        statusCode: 401,
      }),
      expectedMessage: "The username or password is incorrect.",
    },
    {
      failureName: "unavailable API",
      networkError: new Error("Raw connection refused"),
      expectedMessage:
        "The local API is unavailable. Try again when it is running.",
    },
  ])("shows only the safe message for $failureName", async ({
    networkError,
    expectedMessage,
  }) => {
    const client = createApolloClient("Basic test-only");
    const rawUsername = "raw-test-username";
    const rawPassword = "raw-test-password";
    const credentialValidator = vi.fn().mockRejectedValue(
      new ApolloError({ networkError }),
    );

    render(
      <App
        clientFactory={vi.fn(() => client)}
        credentialValidator={credentialValidator}
      />,
    );

    enterCredentials(rawUsername, rawPassword);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(expectedMessage);
    expect(alert.textContent).toBe(expectedMessage);
    expect(alert).not.toHaveTextContent(networkError.message);
    expect(alert).not.toHaveTextContent(rawUsername);
    expect(alert).not.toHaveTextContent(rawPassword);
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(
      screen.getByRole("heading", { name: "Sign in to the graph explorer" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Graph" })).not.toBeInTheDocument();
  });
});
