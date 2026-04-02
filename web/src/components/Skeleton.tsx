import { clsx } from "clsx";

/* ── Skeleton line ──────────────────────────────────────────────── */
interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  className?: string;
  rounded?: boolean;
}

export function Skeleton({ width, height, className, rounded }: SkeletonProps) {
  return (
    <div
      className={clsx("ow-skeleton", rounded && "!rounded-full", className)}
      style={{ width, height: height ?? "14px" }}
      aria-hidden="true"
    />
  );
}

/* ── Skeleton Card (common pattern) ────────────────────────────── */
export function SkeletonCard({ rows = 3 }: { rows?: number }) {
  return (
    <div className="ow-card ow-card-section flex flex-col gap-3">
      <Skeleton width="40%" height={12} />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} width={i === rows - 1 ? "60%" : "100%"} height={12} />
      ))}
    </div>
  );
}

/* ── Skeleton Signal Row ────────────────────────────────────────── */
export function SkeletonSignalRow() {
  return (
    <div className="ow-signal-card cursor-default">
      <div className="flex items-start gap-3">
        <Skeleton width={52} height={20} rounded />
        <div className="flex-1 flex flex-col gap-2">
          <Skeleton width="55%" height={14} />
          <Skeleton width="80%" height={12} />
        </div>
        <Skeleton width={60} height={12} />
      </div>
    </div>
  );
}

/* ── Skeleton Table ─────────────────────────────────────────────── */
export function SkeletonTable({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="ow-table-wrapper">
      <table className="ow-table">
        <thead>
          <tr>
            {Array.from({ length: cols }).map((_, i) => (
              <th key={i}><Skeleton width={`${60 + i * 10}%`} height={10} /></th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, ri) => (
            <tr key={ri}>
              {Array.from({ length: cols }).map((_, ci) => (
                <td key={ci}><Skeleton width={`${50 + ci * 10}%`} height={12} /></td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ── Legacy aliases (backward compat) ──────────────────────────── */
export const TableSkeleton = SkeletonTable;

export function DetailSkeleton() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex flex-col gap-2">
        <Skeleton width="30%" height={10} />
        <Skeleton width="60%" height={24} />
        <Skeleton width="45%" height={14} />
      </div>
      <div className="flex gap-3">
        {[80, 100, 72].map((w, i) => <Skeleton key={i} width={w} height={28} rounded />)}
      </div>
      <SkeletonCard rows={4} />
      <SkeletonCard rows={3} />
      <SkeletonTable rows={4} cols={5} />
    </div>
  );
}
