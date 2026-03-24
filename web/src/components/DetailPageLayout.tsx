import { cn } from "@/lib/utils";

interface DetailPageLayoutProps {
  header: React.ReactNode;
  aside: React.ReactNode;
  main: React.ReactNode;
  asideWidth?: string;
  maxWidth?: "4xl" | "5xl" | "6xl" | "full";
}

const MAX_WIDTH_CLASSES = {
  "4xl": "max-w-4xl",
  "5xl": "max-w-5xl",
  "6xl": "max-w-6xl",
  full: "max-w-full",
};

export function DetailPageLayout({
  header,
  aside,
  main,
  maxWidth = "5xl",
}: DetailPageLayoutProps) {
  return (
    <div className={cn("mx-auto px-4 sm:px-6 pb-10", MAX_WIDTH_CLASSES[maxWidth])}>
      {/* Sticky header */}
      <div className="sticky top-0 z-10 -mx-4 px-4 sm:-mx-6 sm:px-6 bg-newsprint/95 backdrop-blur-sm border-b border-border py-4 mb-6">
        {header}
      </div>

      {/* Two-zone layout */}
      <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
        {/* Aside — stacks above on mobile, sticky on desktop */}
        <aside className="w-full lg:w-72 lg:shrink-0 lg:sticky lg:top-[73px] space-y-3">
          <div className="border border-border bg-newsprint-subtle p-4">
            {aside}
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 min-w-0 space-y-6">
          {main}
        </main>
      </div>
    </div>
  );
}
