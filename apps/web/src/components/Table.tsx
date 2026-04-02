import { clsx } from "clsx";
import type { HTMLAttributes, ThHTMLAttributes, TdHTMLAttributes, ReactNode } from "react";

export function Table({ className, children, ...props }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="ow-table-wrapper">
      <table className={clsx("ow-table", className)} {...props}>
        {children}
      </table>
    </div>
  );
}

export function TableHead({ className, children, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={className} {...props}>{children}</thead>;
}

export function TableBody({ className, children, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={className} {...props}>{children}</tbody>;
}

export function TableRow({ className, children, onClick, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={clsx(onClick && "ow-table-row-link", className)}
      onClick={onClick}
      {...props}
    >
      {children}
    </tr>
  );
}

export function Th({ className, children, ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return <th className={className} {...props}>{children}</th>;
}

export function Td({ className, children, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={className} {...props}>{children}</td>;
}
