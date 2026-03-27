import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { VisualSurface } from "../VisualSurface";

vi.mock("../../../hooks/usePageVisible", () => ({
  usePageVisible: vi.fn(() => true),
}));

describe("VisualSurface", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(new Blob(["fake-jpeg"], { type: "image/jpeg" }), {
        status: 200,
      }),
    );
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock-url");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  it("renders an img element with visual-surface class", () => {
    const { container } = render(<VisualSurface />);
    const img = container.querySelector("img.visual-surface");
    expect(img).not.toBeNull();
  });

  it("has fixed positioning styles", () => {
    const { container } = render(<VisualSurface />);
    const img = container.querySelector("img.visual-surface") as HTMLImageElement;
    expect(img.style.position).toBe("fixed");
    expect(img.style.pointerEvents).toBe("none");
    expect(img.style.zIndex).toBe("-1");
  });

  it("has cover object-fit for aspect ratio handling", () => {
    const { container } = render(<VisualSurface />);
    const img = container.querySelector("img.visual-surface") as HTMLImageElement;
    expect(img.style.objectFit).toBe("cover");
  });
});
