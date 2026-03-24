import { forwardRef } from "react";
import { cn } from "@/lib/utils";

/* ── Root ─────────────────────────────────────────── */
export const Table = forwardRef<HTMLTableElement, React.TableHTMLAttributes<HTMLTableElement>>(
  ({ className, ...props }, ref) => (
    <div className="overflow-x-auto">
      <table ref={ref} className={cn("w-full text-left text-sm", className)} {...props} />
    </div>
  ),
);
Table.displayName = "Table";

/* ── Header ───────────────────────────────────────── */
export const TableHeader = forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
  ({ className, ...props }, ref) => (
    <thead
      ref={ref}
      className={cn("", className)}
      {...props}
    />
  ),
);
TableHeader.displayName = "TableHeader";

/* ── Body ─────────────────────────────────────────── */
export const TableBody = forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
  ({ className, ...props }, ref) => (
    <tbody ref={ref} className={cn("", className)} {...props} />
  ),
);
TableBody.displayName = "TableBody";

/* ── Row ──────────────────────────────────────────── */
interface TableRowProps extends React.HTMLAttributes<HTMLTableRowElement> {
  clickable?: boolean;
}

export const TableRow = forwardRef<HTMLTableRowElement, TableRowProps>(
  ({ className, clickable, style, ...props }, ref) => (
    <tr
      ref={ref}
      className={cn(
        "transition-colors duration-120",
        clickable && "cursor-pointer hover:bg-surface-subtle/50",
        className,
      )}
      style={{ borderBottom: "1px solid var(--color-border)", ...style }}
      {...props}
    />
  ),
);
TableRow.displayName = "TableRow";

/* ── Header cell ──────────────────────────────────── */
export const TableHead = forwardRef<HTMLTableCellElement, React.ThHTMLAttributes<HTMLTableCellElement>>(
  ({ className, style, ...props }, ref) => (
    <th
      ref={ref}
      className={cn(
        "px-3 py-2.5 text-left uppercase tracking-[0.05em] text-muted",
        className,
      )}
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: "0.6875rem",
        borderBottom: "1px solid var(--color-border)",
        ...style,
      }}
      {...props}
    />
  ),
);
TableHead.displayName = "TableHead";

/* ── Body cell ────────────────────────────────────── */
export const TableCell = forwardRef<HTMLTableCellElement, React.TdHTMLAttributes<HTMLTableCellElement>>(
  ({ className, ...props }, ref) => (
    <td ref={ref} className={cn("px-3 py-2", className)} {...props} />
  ),
);
TableCell.displayName = "TableCell";
