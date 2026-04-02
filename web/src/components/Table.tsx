import { forwardRef } from "react";
import { cn } from "@/lib/utils";

/**
 * Table Component — Modern Data Display
 * 
 * Usage:
 * <Table>
 *   <TableHeader>
 *     <TableRow>
 *       <TableHead>Column</TableHead>
 *     </TableRow>
 *   </TableHeader>
 *   <TableBody>
 *     <TableRow>
 *       <TableCell>Data</TableCell>
 *     </TableRow>
 *   </TableBody>
 * </Table>
 */

/* ── Root ───────────────────────────────────────────────── */
export const Table = forwardRef<HTMLTableElement, React.TableHTMLAttributes<HTMLTableElement>>(
  ({ className, ...props }, ref) => (
    <div className="w-full overflow-x-auto rounded-[var(--radius-md)] border border-[var(--color-border-light)] shadow-[var(--shadow-sm)]">
      <table 
        ref={ref} 
        className={cn(
          "w-full text-left text-sm font-family-sans border-collapse",
          className
        )} 
        {...props} 
      />
    </div>
  ),
);
Table.displayName = "Table";

/* ── Header ────────────────────────────────────────────── */
export const TableHeader = forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <thead
    ref={ref}
    className={cn(
      "bg-[var(--color-surface-hover)] border-b border-[var(--color-border-light)]",
      className,
    )}
    {...props}
  />
));
TableHeader.displayName = "TableHeader";

/* ── Body ──────────────────────────────────────────────── */
export const TableBody = forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tbody ref={ref} className={cn("bg-white", className)} {...props} />
));
TableBody.displayName = "TableBody";

/* ── Row ───────────────────────────────────────────────── */
interface TableRowProps extends React.HTMLAttributes<HTMLTableRowElement> {
  clickable?: boolean;
  highlighted?: boolean;
}

export const TableRow = forwardRef<HTMLTableRowElement, TableRowProps>(
  ({ className, clickable, highlighted, ...props }, ref) => (
    <tr
      ref={ref}
      className={cn(
        "border-b border-[var(--color-border-light)] transition-colors duration-150",
        clickable && "cursor-pointer hover:bg-[var(--color-surface-hover)]",
        highlighted && "bg-blue-50",
        className,
      )}
      {...props}
    />
  ),
);
TableRow.displayName = "TableRow";

/* ── Header cell ───────────────────────────────────────── */
export const TableHead = forwardRef<
  HTMLTableCellElement,
  React.ThHTMLAttributes<HTMLTableCellElement> & { sortable?: boolean }
>(({ className, sortable, ...props }, ref) => (
  <th
    ref={ref}
    className={cn(
      "px-4 py-3 text-left text-xs font-semibold text-[var(--color-text-primary)] uppercase",
      "letter-spacing-[0.05em] tracking-wider",
      sortable && "cursor-pointer select-none hover:text-[var(--color-accent-alert)]",
      className,
    )}
    {...props}
  />
));
TableHead.displayName = "TableHead";

/* ── Body cell ────────────────────────────────────────── */
export const TableCell = forwardRef<
  HTMLTableCellElement,
  React.TdHTMLAttributes<HTMLTableCellElement> & { 
    variant?: "default" | "label" | "data" | "code";
    severity?: "critical" | "high" | "medium" | "low";
  }
>(({ className, variant = "default", severity, ...props }, ref) => {
  let variantClass = "";
  
  switch (variant) {
    case "label":
      variantClass = "font-semibold text-[var(--color-text-primary)]";
      break;
    case "data":
      variantClass = "font-[var(--font-mono)] text-[var(--color-text-secondary)]";
      break;
    case "code":
      variantClass = "font-[var(--font-mono)] text-xs bg-[var(--color-surface-base)] px-2 py-1 rounded";
      break;
    default:
      variantClass = "text-[var(--color-text-secondary)]";
  }

  let severityClass = "";
  if (severity) {
    switch (severity) {
      case "critical":
        severityClass = "text-[var(--color-critical)]";
        break;
      case "high":
        severityClass = "text-[var(--color-high)]";
        break;
      case "medium":
        severityClass = "text-[var(--color-medium)]";
        break;
      case "low":
        severityClass = "text-[var(--color-low)]";
        break;
    }
  }

  return (
    <td 
      ref={ref} 
      className={cn(
        "px-4 py-3",
        variantClass,
        severityClass,
        className
      )} 
      {...props} 
    />
  );
});
TableCell.displayName = "TableCell";

/* ── Selection checkbox ────────────────────────────────── */
export const TableCheckbox = forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => (
  <input
    ref={ref}
    type="checkbox"
    className={cn(
      "w-4 h-4 rounded-[var(--radius-xs)] cursor-pointer accent-[var(--color-accent-alert)]",
      className,
    )}
    {...props}
  />
));
TableCheckbox.displayName = "TableCheckbox";

