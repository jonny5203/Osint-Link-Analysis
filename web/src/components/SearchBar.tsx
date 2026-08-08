import { useApolloClient } from "@apollo/client";
import { useEffect, useRef, useState } from "react";

import {
  SEARCH,
  type GraphNode,
  type SearchResult,
} from "../graphql/queries";

type SearchExecutor = (term: string) => Promise<SearchResult>;

type SearchBarProps = {
  onSelect: (node: GraphNode) => void;
  searchExecutor?: SearchExecutor;
};

const SEARCH_DELAY_MS = 300;

export function SearchBar({ onSelect, searchExecutor }: SearchBarProps) {
  const client = useApolloClient();
  const [term, setTerm] = useState("");
  const [results, setResults] = useState<SearchResult["searchEntities"]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [searched, setSearched] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const requestGeneration = useRef(0);

  useEffect(() => {
    const trimmed = term.trim();
    const generation = requestGeneration.current;

    if (trimmed.length < 2) {
      return;
    }

    const timer = window.setTimeout(() => {
      setLoading(true);
      const execute = searchExecutor
        ? searchExecutor(trimmed)
        : client
            .query({
              query: SEARCH,
              variables: { term: trimmed, limit: 20 },
              fetchPolicy: "no-cache",
            })
            .then(({ data }) => data);

      void execute
        .then((data) => {
          if (requestGeneration.current !== generation) {
            return;
          }

          setResults(data.searchEntities);
          setSearched(true);
        })
        .catch(() => {
          if (requestGeneration.current !== generation) {
            return;
          }

          setResults([]);
          setError(true);
          setSearched(true);
        })
        .finally(() => {
          if (requestGeneration.current === generation) {
            setLoading(false);
          }
        });
    }, SEARCH_DELAY_MS);

    return () => window.clearTimeout(timer);
  }, [client, searchExecutor, term]);

  function selectResult(index: number) {
    const result = results[index];
    if (!result) {
      return;
    }

    onSelect(result.node);
    updateTerm("");
  }

  function updateTerm(value: string) {
    requestGeneration.current += 1;
    setTerm(value);
    setActiveIndex(-1);
    setError(false);
    setSearched(false);
    setResults([]);
    setLoading(false);
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (results.length === 0) {
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % results.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) =>
        index <= 0 ? results.length - 1 : index - 1,
      );
    } else if (event.key === "Enter" && activeIndex >= 0) {
      event.preventDefault();
      selectResult(activeIndex);
    } else if (event.key === "Escape") {
      setResults([]);
      setActiveIndex(-1);
    }
  }

  return (
    <div className="search-bar">
      <label htmlFor="entity-search">Search entities</label>
      <input
        id="entity-search"
        type="search"
        role="combobox"
        aria-autocomplete="list"
        aria-controls="search-results"
        aria-expanded={results.length > 0}
        aria-activedescendant={
          activeIndex >= 0 ? `search-result-${activeIndex}` : undefined
        }
        placeholder="Type at least two characters"
        value={term}
        onChange={(event) => updateTerm(event.target.value)}
        onKeyDown={handleKeyDown}
      />
      <div className="search-status" role="status" aria-live="polite">
        {loading && "Searching…"}
        {!loading && error && "Search is unavailable. Try again."}
        {!loading && searched && !error && results.length === 0 && "No results."}
      </div>
      {results.length > 0 && (
        <ul id="search-results" className="search-results" role="listbox">
          {results.map(({ node }, index) => (
            <li
              id={`search-result-${index}`}
              key={node.id}
              role="option"
              aria-selected={index === activeIndex}
            >
              <button type="button" onClick={() => selectResult(index)}>
                <span>{node.displayName}</span>
                <small>{node.kind.toLowerCase()}</small>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
