import { describe, it, expect } from "vitest";
import { RouteGuard } from "@/auth/RouteGuard";
import { MemoryRouter } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

vi.mock("@/auth/AuthProvider", () => ({
  useAuth: () => ({
    loading: false,
    can: () => false,
    rbacEnforced: true,
  }),
}));

describe("Intelligence console permission denied", () => {
  it("renders 403 for intelligence:read guarded console", () => {
    render(
      <MemoryRouter>
        <RouteGuard permission="intelligence:read">
          <div>Intelligence Console</div>
        </RouteGuard>
      </MemoryRouter>,
    );
    expect(screen.getByText("403")).toBeInTheDocument();
    expect(screen.queryByText("Intelligence Console")).not.toBeInTheDocument();
  });
});
