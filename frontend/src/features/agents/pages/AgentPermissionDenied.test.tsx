import { describe, it, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import { RouteGuard } from "@/auth/RouteGuard";

vi.mock("@/auth/AuthProvider", () => ({
  useAuth: () => ({
    loading: false,
    can: () => false,
    rbacEnforced: true,
  }),
}));

describe("Agent console permission denied", () => {
  it("renders 403 for task:read guarded agent console", () => {
    render(
      <MemoryRouter>
        <RouteGuard permission="task:read">
          <div>Agent Operations Console</div>
        </RouteGuard>
      </MemoryRouter>,
    );

    expect(screen.getByText("403")).toBeInTheDocument();
    expect(screen.queryByText("Agent Operations Console")).not.toBeInTheDocument();
  });
});
