import "@testing-library/jest-dom/vitest";
import { MockedProvider } from "@apollo/client/testing";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { GraphNode, SearchResult } from "../graphql/queries";
import { SearchBar } from "./SearchBar";

function node(id: string, displayName: string): GraphNode {
  return {
    id,
    displayName,
    kind: "PERSON",
    aliases: [],
    sanctioned: false,
    datasetIds: [],
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

afterEach(() => {
  vi.useRealTimers();
});

describe("SearchBar", () => {
  it("does not search a one-character term", () => {
    vi.useFakeTimers();
    const searchExecutor = vi.fn<() => Promise<SearchResult>>();

    render(
      <MockedProvider>
        <SearchBar onSelect={vi.fn()} searchExecutor={searchExecutor} />
      </MockedProvider>,
    );

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "a" } });
    act(() => vi.advanceTimersByTime(500));

    expect(searchExecutor).not.toHaveBeenCalled();
  });

  it("ignores a late stale response and supports keyboard selection", async () => {
    vi.useFakeTimers();
    const older = deferred<SearchResult>();
    const newer = deferred<SearchResult>();
    const searchExecutor = vi
      .fn<(term: string) => Promise<SearchResult>>()
      .mockReturnValueOnce(older.promise)
      .mockReturnValueOnce(newer.promise);
    const onSelect = vi.fn();

    render(
      <MockedProvider>
        <SearchBar onSelect={onSelect} searchExecutor={searchExecutor} />
      </MockedProvider>,
    );

    const input = screen.getByRole("combobox");
    fireEvent.change(input, { target: { value: "Ave" } });
    act(() => vi.advanceTimersByTime(300));
    fireEvent.change(input, { target: { value: "Avery" } });
    act(() => vi.advanceTimersByTime(300));

    await act(async () => {
      newer.resolve({
        searchEntities: [{ score: 1, node: node("avery", "Avery Stone") }],
      });
      await newer.promise;
    });
    await act(async () => {
      older.resolve({
        searchEntities: [{ score: 1, node: node("old", "Outdated Person") }],
      });
      await older.promise;
    });

    expect(screen.getByText("Avery Stone")).toBeInTheDocument();
    expect(screen.queryByText("Outdated Person")).not.toBeInTheDocument();

    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith(node("avery", "Avery Stone"));
  });
});
