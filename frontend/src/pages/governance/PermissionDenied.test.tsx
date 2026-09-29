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

describe("Governance permission denied", () => {
  it("renders 403 for task:read guarded content", () => {
    render(
      <MemoryRouter>
        <RouteGuard permission="task:read">
          <div>Governance Console</div>
        </RouteGuard>
      </MemoryRouter>,
    );

    expect(screen.getByText("403")).toBeInTheDocument();
    expect(screen.queryByText("Governance Console")).not.toBeInTheDocument();
  });
});
